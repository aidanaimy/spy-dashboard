"""
Simple backtest engine for SPY price-only trading.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try Alpaca first, fallback to yfinance
try:
    from data.alpaca_client import get_daily_data, get_intraday_data, get_alpaca_api
    if get_alpaca_api() is None:
        raise ImportError("Alpaca API not initialized")
except (ImportError, AttributeError):
    from data.yfinance_client import get_daily_data, get_intraday_data
from logic.regime import analyze_regime
from logic.intraday import analyze_intraday
from logic.signals import generate_signal
from logic.iv import fetch_historical_vix_context, fetch_iv_context
from logic.options import (
    black_scholes_price, calculate_delta, calculate_all_greeks,
    get_atm_strike, time_to_expiration_0dte, calculate_option_pnl
)
import config


class BacktestEngine:
    """Simple backtest engine for rule-based signals."""
    
    def __init__(self, tp_pct: float = config.BACKTEST_TP_PCT,
                 sl_pct: float = config.BACKTEST_SL_PCT,
                 position_size: float = config.BACKTEST_POSITION_SIZE,
                 use_options: bool = False):
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.position_size = position_size
        self.use_options = use_options
        
        # Options-specific parameters
        if use_options:
            self.options_tp_pct = config.BACKTEST_OPTIONS_TP_PCT
            self.options_sl_pct = config.BACKTEST_OPTIONS_SL_PCT
            self.options_contracts = config.BACKTEST_OPTIONS_CONTRACTS
            self.risk_free_rate = config.BACKTEST_RISK_FREE_RATE
    
    def _get_option_price(self, S: float, K: float, T: float, sigma: float, option_type: str) -> float:
        """Calculate option price using Black-Scholes."""
        return black_scholes_price(S, K, T, self.risk_free_rate, sigma, option_type)
    
    def _get_option_greeks(self, S: float, K: float, T: float, sigma: float, option_type: str) -> Dict:
        """Calculate option Greeks."""
        return calculate_all_greeks(S, K, T, self.risk_free_rate, sigma, option_type)
    
    def _calculate_options_pnl(self, entry_option_price: float, exit_option_price: float) -> float:
        """Calculate P/L for options trade."""
        return calculate_option_pnl(entry_option_price, exit_option_price, self.options_contracts)
        
    def run_backtest(self, start_date: datetime, end_date: datetime, use_options: bool = False) -> Dict:
        """
        Run backtest over date range.
        
        Args:
            start_date: Start date
            end_date: End date
            use_options: If True, use options pricing (Black-Scholes) instead of shares
            
        Returns:
            Dictionary with backtest results
        """
        self.use_options = use_options
        if use_options:
            self.options_tp_pct = config.BACKTEST_OPTIONS_TP_PCT
            self.options_sl_pct = config.BACKTEST_OPTIONS_SL_PCT
            self.options_contracts = config.BACKTEST_OPTIONS_CONTRACTS
            self.risk_free_rate = config.BACKTEST_RISK_FREE_RATE
        # Get daily data for regime analysis - fetch enough to cover the backtest period
        # Calculate days needed: backtest period + buffer for weekends/holidays + MA periods
        backtest_days = (end_date - start_date).days
        required_days = max(backtest_days * 2, 100)  # At least 2x the period or 100 days
        daily_df = get_daily_data(config.SYMBOL, days=required_days)
        
        # Get list of trading days
        trading_days = pd.bdate_range(start=start_date, end=end_date)
        
        trades = []
        equity_curve = []
        current_position = None  # {'direction': 'LONG'/'SHORT', 'entry_price': float, 'entry_time': datetime}
        equity = 10000.0  # Starting equity
        
        # Debug counters
        days_processed = 0
        days_skipped = 0
        signals_generated = 0
        
        for day in trading_days:
            try:
                # Get intraday data for this specific day
                # Calculate start and end of trading day
                day_start = datetime.combine(day.date(), datetime.min.time().replace(hour=9, minute=30))
                day_end = datetime.combine(day.date(), datetime.min.time().replace(hour=16, minute=0))
                
                # Fetch intraday data for this specific day
                try:
                    intraday_df = get_intraday_data(
                        config.SYMBOL,
                        interval=config.INTRADAY_INTERVAL,
                        start_date=day_start,
                        end_date=day_end
                    )
                    
                    # Filter to this day (in case we got extra data)
                    if not intraday_df.empty:
                        intraday_df.index = pd.to_datetime(intraday_df.index)
                        intraday_df = intraday_df[intraday_df.index.date == day.date()]
                except Exception as e:
                    # If intraday not available for this day, skip it
                    days_skipped += 1
                    continue
                
                if intraday_df.empty:
                    continue
                
                # Get daily data up to this day for regime analysis
                daily_df_up_to_day = daily_df[daily_df.index.date <= day.date()].sort_index()
                
                # Get yesterday's close (day before current trading day)
                if len(daily_df_up_to_day) >= 2:
                    yesterday_close = daily_df_up_to_day.iloc[-2]['Close']
                elif len(daily_df_up_to_day) == 1:
                    yesterday_close = daily_df_up_to_day.iloc[-1]['Close']
                else:
                    yesterday_close = intraday_df.iloc[0]['Open']
                
                # Get today's data
                today_data = {
                    'yesterday_close': yesterday_close,
                    'today_open': intraday_df.iloc[0]['Open'],
                    'today_high': intraday_df['High'].max(),
                    'today_low': intraday_df['Low'].min(),
                    'today_close': intraday_df.iloc[-1]['Close']
                }
                
                # Analyze regime using daily data up to this day
                regime = analyze_regime(daily_df_up_to_day, today_data)
                
                # Process each bar in the day
                intraday_df_sorted = intraday_df.sort_index()
                
                # Fetch VIX context for this day (once per day, reused for all bars)
                try:
                    # Use the first bar's timestamp as the day reference
                    first_bar_time = intraday_df_sorted.index[0]
                    if hasattr(first_bar_time, 'to_pydatetime'):
                        day_datetime = first_bar_time.to_pydatetime()
                    elif isinstance(first_bar_time, datetime):
                        day_datetime = first_bar_time
                    else:
                        day_datetime = pd.to_datetime(first_bar_time).to_pydatetime()
                    
                    iv_context = fetch_historical_vix_context(day_datetime)
                except Exception:
                    # If VIX fetch fails, use empty context
                    iv_context = {}
                
                for idx, row in intraday_df_sorted.iterrows():
                    # Check session time (9:45 - 15:30)
                    if hasattr(idx, 'strftime'):
                        time_str = idx.strftime('%H:%M')
                    elif hasattr(idx, 'time'):
                        time_str = idx.time().strftime('%H:%M')
                    else:
                        # Try to parse as datetime
                        try:
                            idx_dt = pd.to_datetime(idx)
                            time_str = idx_dt.strftime('%H:%M')
                        except:
                            time_str = "00:00"  # Default if can't parse
                    
                    if time_str < config.SESSION_START or time_str > config.SESSION_END:
                        continue
                    
                    current_price = row['Close']
                    
                    # Block entries at and after BLOCK_TRADE_AFTER time (15:30)
                    if time_str >= config.BLOCK_TRADE_AFTER:
                        # Still process exits, but no new entries
                        if current_position is not None:
                            entry_price = current_position['entry_price']
                            entry_underlying_price = current_position.get('entry_underlying_price', entry_price)
                            
                            if self.use_options:
                                # Options mode
                                strike = current_position.get('strike', get_atm_strike(current_price))
                                option_type = 'call' if current_position['direction'] == 'LONG' else 'put'
                                
                                # Get time to expiration
                                if hasattr(idx, 'hour') and hasattr(idx, 'minute'):
                                    hours = idx.hour
                                    minutes = idx.minute
                                else:
                                    idx_dt = pd.to_datetime(idx)
                                    hours = idx_dt.hour
                                    minutes = idx_dt.minute
                                
                                T = time_to_expiration_0dte(hours, minutes)
                                # Use stored entry IV or fallback to VIX (default 20.0 if None)
                                vix_level = iv_context.get('vix_level') or 20.0
                                sigma = current_position.get('entry_iv', vix_level / 100.0)
                                
                                current_option_price = self._get_option_price(
                                    current_price, strike, T, sigma, option_type
                                )
                                
                                entry_option_price = current_position.get('entry_option_price', entry_price)
                                pnl_pct = (current_option_price - entry_option_price) / entry_option_price if entry_option_price > 0 else 0
                                
                                exit_reason = None
                                if pnl_pct >= self.options_tp_pct:
                                    exit_reason = 'TP'
                                elif pnl_pct <= -self.options_sl_pct:
                                    exit_reason = 'SL'
                                elif time_str >= config.SESSION_END:
                                    exit_reason = 'EOD'
                                
                                if exit_reason:
                                    pnl = self._calculate_options_pnl(entry_option_price, current_option_price)
                                    equity += pnl
                                    trades.append({
                                        'entry_time': current_position['entry_time'],
                                        'exit_time': idx,
                                        'direction': current_position['direction'],
                                        'entry_price': entry_option_price,
                                        'exit_price': current_option_price,
                                        'entry_underlying': entry_underlying_price,
                                        'exit_underlying': current_price,
                                        'pnl': pnl,
                                        'exit_reason': exit_reason,
                                        'strike': strike
                                    })
                                    current_position = None
                            else:
                                # Shares mode
                                if current_position['direction'] == 'LONG':
                                    pnl_pct = (current_price - entry_price) / entry_price
                                else:
                                    pnl_pct = (entry_price - current_price) / entry_price
                                
                                exit_reason = None
                                if pnl_pct >= self.tp_pct:
                                    exit_reason = 'TP'
                                elif pnl_pct <= -self.sl_pct:
                                    exit_reason = 'SL'
                                elif time_str >= config.SESSION_END:
                                    exit_reason = 'EOD'
                                
                                if exit_reason:
                                    if current_position['direction'] == 'LONG':
                                        pnl = (current_price - entry_price) * self.position_size
                                    else:
                                        pnl = (entry_price - current_price) * self.position_size
                                    
                                    equity += pnl
                                    trades.append({
                                        'entry_time': current_position['entry_time'],
                                        'exit_time': idx,
                                        'direction': current_position['direction'],
                                        'entry_price': entry_price,
                                        'exit_price': current_price,
                                        'pnl': pnl,
                                        'exit_reason': exit_reason
                                    })
                                    current_position = None
                        
                        # Skip signal generation and entry after block time
                        equity_curve.append({
                            'timestamp': idx,
                            'equity': equity
                        })
                        continue
                    
                    # Analyze intraday at this point
                    intraday_data = analyze_intraday(intraday_df_sorted.loc[:idx])
                    
                    # Get market phase for time filtering
                    if hasattr(idx, 'hour') and hasattr(idx, 'minute'):
                        et_time = idx
                    else:
                        et_time = pd.to_datetime(idx)
                    
                    minutes = et_time.hour * 60 + et_time.minute
                    if minutes < 9 * 60 + 30:
                        market_phase = {"label": "Pre-Market", "is_open": False}
                    elif minutes < 11 * 60:
                        market_phase = {"label": "Open Drive", "is_open": True}
                    elif minutes < 13 * 60 + 30:
                        market_phase = {"label": "Midday", "is_open": True}
                    elif minutes < 14 * 60 + 30:
                        market_phase = {"label": "Afternoon Drift", "is_open": True}
                    elif minutes < 15 * 60 + 30:
                        market_phase = {"label": "Power Hour", "is_open": True}
                    else:
                        market_phase = {"label": "After Hours", "is_open": False}
                    
                    # Generate signal (with time filtering, chop detection, and IV/VIX context)
                    signal = generate_signal(
                        regime, 
                        intraday_data,
                        current_time=idx,
                        intraday_df=intraday_df_sorted.loc[:idx],
                        iv_context=iv_context,
                        market_phase=market_phase
                    )
                    
                    # Check for exit conditions if in position
                    if current_position is not None:
                        entry_price = current_position['entry_price']
                        entry_underlying_price = current_position.get('entry_underlying_price', entry_price)
                        
                        if self.use_options:
                            # Options mode: Calculate option price and check TP/SL based on option P/L %
                            strike = current_position.get('strike', get_atm_strike(current_price))
                            option_type = 'call' if current_position['direction'] == 'LONG' else 'put'
                            
                            # Get time to expiration
                            if hasattr(idx, 'hour') and hasattr(idx, 'minute'):
                                hours = idx.hour
                                minutes = idx.minute
                            else:
                                idx_dt = pd.to_datetime(idx)
                                hours = idx_dt.hour
                                minutes = idx_dt.minute
                            
                            T = time_to_expiration_0dte(hours, minutes)
                            # Use stored entry IV or fallback to VIX (default 20.0 if None)
                            vix_level = iv_context.get('vix_level') or 20.0
                            sigma = current_position.get('entry_iv', vix_level / 100.0)
                            
                            current_option_price = self._get_option_price(
                                current_price, strike, T, sigma, option_type
                            )
                            
                            entry_option_price = current_position.get('entry_option_price', entry_price)
                            pnl_pct = (current_option_price - entry_option_price) / entry_option_price if entry_option_price > 0 else 0
                            
                            exit_reason = None
                            if pnl_pct >= self.options_tp_pct:
                                exit_reason = 'TP'
                            elif pnl_pct <= -self.options_sl_pct:
                                exit_reason = 'SL'
                            elif time_str >= config.SESSION_END:
                                exit_reason = 'EOD'
                            
                            if exit_reason:
                                pnl = self._calculate_options_pnl(entry_option_price, current_option_price)
                                equity += pnl
                                
                                trades.append({
                                    'entry_time': current_position['entry_time'],
                                    'exit_time': idx,
                                    'direction': current_position['direction'],
                                    'entry_price': entry_option_price,
                                    'exit_price': current_option_price,
                                    'entry_underlying': entry_underlying_price,
                                    'exit_underlying': current_price,
                                    'pnl': pnl,
                                    'exit_reason': exit_reason,
                                    'strike': strike
                                })
                                
                                current_position = None
                        else:
                            # Shares mode: Calculate P/L percentage based on underlying
                            if current_position['direction'] == 'LONG':
                                pnl_pct = (current_price - entry_price) / entry_price
                            else:  # SHORT
                                pnl_pct = (entry_price - current_price) / entry_price
                            
                            # Check TP/SL
                            exit_reason = None
                            if pnl_pct >= self.tp_pct:
                                exit_reason = 'TP'
                            elif pnl_pct <= -self.sl_pct:
                                exit_reason = 'SL'
                            
                            # Exit at end of session (15:30)
                            if time_str >= config.SESSION_END:
                                exit_reason = 'EOD'
                            
                            if exit_reason:
                                # Close position
                                if current_position['direction'] == 'LONG':
                                    pnl = (current_price - entry_price) * self.position_size
                                else:
                                    pnl = (entry_price - current_price) * self.position_size
                                
                                equity += pnl
                                
                                trades.append({
                                    'entry_time': current_position['entry_time'],
                                    'exit_time': idx,
                                    'direction': current_position['direction'],
                                    'entry_price': entry_price,
                                    'exit_price': current_price,
                                    'pnl': pnl,
                                    'exit_reason': exit_reason
                                })
                                
                                current_position = None
                    
                    # Check for entry if no position
                    if current_position is None:
                        if self.use_options:
                            # Options mode: Calculate option price at entry
                            if signal['direction'] == 'CALL' and signal['confidence'] in ['MEDIUM', 'HIGH']:
                                strike = get_atm_strike(current_price)
                                option_type = 'call'
                                
                                # Get time to expiration
                                if hasattr(idx, 'hour') and hasattr(idx, 'minute'):
                                    hours = idx.hour
                                    minutes = idx.minute
                                else:
                                    idx_dt = pd.to_datetime(idx)
                                    hours = idx_dt.hour
                                    minutes = idx_dt.minute
                                
                                T = time_to_expiration_0dte(hours, minutes)
                                
                                # Use VIX as proxy for IV (default to 20.0 if None or missing)
                                vix_level = iv_context.get('vix_level') or 20.0
                                sigma = vix_level / 100.0
                                
                                # Calculate entry option price
                                entry_option_price = self._get_option_price(
                                    current_price, strike, T, sigma, option_type
                                )
                                
                                current_position = {
                                    'direction': 'LONG',
                                    'entry_price': entry_option_price,
                                    'entry_underlying_price': current_price,
                                    'entry_option_price': entry_option_price,
                                    'entry_time': idx,
                                    'strike': strike,
                                    'entry_iv': sigma
                                }
                            elif signal['direction'] == 'PUT' and signal['confidence'] in ['MEDIUM', 'HIGH']:
                                strike = get_atm_strike(current_price)
                                option_type = 'put'
                                
                                # Get time to expiration
                                if hasattr(idx, 'hour') and hasattr(idx, 'minute'):
                                    hours = idx.hour
                                    minutes = idx.minute
                                else:
                                    idx_dt = pd.to_datetime(idx)
                                    hours = idx_dt.hour
                                    minutes = idx_dt.minute
                                
                                T = time_to_expiration_0dte(hours, minutes)
                                
                                # Use VIX as proxy for IV (default to 20.0 if None or missing)
                                vix_level = iv_context.get('vix_level') or 20.0
                                sigma = vix_level / 100.0
                                
                                # Calculate entry option price
                                entry_option_price = self._get_option_price(
                                    current_price, strike, T, sigma, option_type
                                )
                                
                                current_position = {
                                    'direction': 'SHORT',
                                    'entry_price': entry_option_price,
                                    'entry_underlying_price': current_price,
                                    'entry_option_price': entry_option_price,
                                    'entry_time': idx,
                                    'strike': strike,
                                    'entry_iv': sigma
                                }
                        else:
                            # Shares mode: Original logic
                            if signal['direction'] == 'CALL' and signal['confidence'] in ['MEDIUM', 'HIGH']:
                                current_position = {
                                    'direction': 'LONG',
                                    'entry_price': current_price,
                                    'entry_time': idx
                                }
                            elif signal['direction'] == 'PUT' and signal['confidence'] in ['MEDIUM', 'HIGH']:
                                current_position = {
                                    'direction': 'SHORT',
                                    'entry_price': current_price,
                                    'entry_time': idx
                                }
                    
                    # Record equity
                    equity_curve.append({
                        'timestamp': idx,
                        'equity': equity
                    })
                
                # Close any remaining position at end of day
                if current_position is not None:
                    exit_underlying_price = intraday_df_sorted.iloc[-1]['Close']
                    entry_price = current_position['entry_price']
                    
                    if self.use_options:
                        # Options mode: Calculate final option price at EOD
                        strike = current_position.get('strike', get_atm_strike(exit_underlying_price))
                        option_type = 'call' if current_position['direction'] == 'LONG' else 'put'
                        
                        # At EOD (4:00 PM), T = 0 (expiration)
                        T = 0.0
                        
                        # Use entry IV (or VIX if available)
                        sigma = current_position.get('entry_iv', iv_context.get('vix_level', 20.0) / 100.0)
                        
                        # At expiration, option price = intrinsic value
                        exit_option_price = self._get_option_price(
                            exit_underlying_price, strike, T, sigma, option_type
                        )
                        
                        entry_option_price = current_position.get('entry_option_price', entry_price)
                        pnl = self._calculate_options_pnl(entry_option_price, exit_option_price)
                        
                        equity += pnl
                        
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': intraday_df_sorted.index[-1],
                            'direction': current_position['direction'],
                            'entry_price': entry_option_price,
                            'exit_price': exit_option_price,
                            'entry_underlying': current_position.get('entry_underlying_price', entry_price),
                            'exit_underlying': exit_underlying_price,
                            'pnl': pnl,
                            'exit_reason': 'EOD',
                            'strike': strike
                        })
                    else:
                        # Shares mode
                        if current_position['direction'] == 'LONG':
                            pnl = (exit_underlying_price - entry_price) * self.position_size
                        else:
                            pnl = (entry_price - exit_underlying_price) * self.position_size
                        
                        equity += pnl
                        
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': intraday_df_sorted.index[-1],
                            'direction': current_position['direction'],
                            'entry_price': entry_price,
                            'exit_price': exit_underlying_price,
                            'pnl': pnl,
                            'exit_reason': 'EOD'
                        })
                    
                    current_position = None
                    
            except Exception as e:
                import traceback
                print(f"Error processing {day}: {str(e)}")
                traceback.print_exc()
                days_skipped += 1
                continue
            
            days_processed += 1
        
        # Calculate metrics
        if not trades:
            return {
                'trades': [],
                'equity_curve': pd.DataFrame(),
                'num_trades': 0,
                'win_rate': 0.0,
                'avg_r_multiple': 0.0,
                'max_drawdown': 0.0,
                'total_pnl': 0.0
            }
        
        trades_df = pd.DataFrame(trades)
        
        # Win rate
        winning_trades = trades_df[trades_df['pnl'] > 0]
        win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0.0
        
        # Average R multiple (profit / risk)
        if self.use_options:
            # For options: risk = total premium paid (entry_price * 100 * contracts)
            # Each contract = 100 shares, so premium per contract = entry_price * 100
            trades_df['risk'] = trades_df['entry_price'] * 100 * self.options_contracts
        else:
            # For shares: risk = entry_price * sl_pct * position_size
            trades_df['risk'] = trades_df['entry_price'] * self.sl_pct * self.position_size
        
        trades_df['r_multiple'] = trades_df['pnl'] / trades_df['risk']
        trades_df['r_multiple'] = trades_df['r_multiple'].replace([np.inf, -np.inf], 0)
        trades_df['r_multiple'] = trades_df['r_multiple'].fillna(0)
        avg_r_multiple = trades_df['r_multiple'].mean()
        
        # Max drawdown
        equity_df = pd.DataFrame(equity_curve)
        if not equity_df.empty:
            equity_df['peak'] = equity_df['equity'].cummax()
            equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak']
            max_drawdown = abs(equity_df['drawdown'].min())
        else:
            max_drawdown = 0.0
        
        total_pnl = trades_df['pnl'].sum()
        
        # Time-of-day performance analysis
        time_analysis = {}
        if 'entry_time' in trades_df.columns:
            trades_df['entry_hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour
            trades_df['entry_minute'] = pd.to_datetime(trades_df['entry_time']).dt.minute
            trades_df['entry_time_of_day'] = trades_df['entry_hour'] * 60 + trades_df['entry_minute']
            
            # Define time periods
            time_periods = {
                'Early (9:45-11:00)': (9*60+45, 11*60),
                'Mid-Morning (11:00-12:00)': (11*60, 12*60),
                'Lunch (12:00-13:00)': (12*60, 13*60),
                'Afternoon (13:00-14:30)': (13*60, 14*60+30),
                'Power Hour (14:30-15:30)': (14*60+30, 15*60+30)
            }
            
            for period_name, (start_min, end_min) in time_periods.items():
                period_trades = trades_df[
                    (trades_df['entry_time_of_day'] >= start_min) & 
                    (trades_df['entry_time_of_day'] < end_min)
                ]
                
                if len(period_trades) > 0:
                    period_win_rate = len(period_trades[period_trades['pnl'] > 0]) / len(period_trades)
                    period_avg_r = period_trades['r_multiple'].mean()
                    period_pnl = period_trades['pnl'].sum()
                    period_count = len(period_trades)
                    
                    time_analysis[period_name] = {
                        'trades': period_count,
                        'win_rate': period_win_rate,
                        'avg_r_multiple': period_avg_r,
                        'total_pnl': period_pnl
                    }
        
        return {
            'trades': trades_df,
            'equity_curve': equity_df,
            'num_trades': len(trades_df),
            'win_rate': win_rate,
            'avg_r_multiple': avg_r_multiple,
            'max_drawdown': max_drawdown,
            'total_pnl': total_pnl,
            'time_analysis': time_analysis
        }

