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
# Try Alpaca first, fallback to yfinance
DATA_SOURCE = "yfinance"
try:
    from data.alpaca_client import get_daily_data, get_intraday_data, get_daily_data_for_period, get_alpaca_api
    if get_alpaca_api() is not None:
        DATA_SOURCE = "alpaca"
        print("✅ Backtest Engine: Using Alpaca data source")
    else:
        print("⚠️ Backtest Engine: Alpaca API not initialized, falling back to yfinance")
        raise ImportError("Alpaca API not initialized")
except (ImportError, AttributeError) as e:
    print(f"⚠️ Backtest Engine: Could not load Alpaca ({e}), falling back to yfinance")
    from data.yfinance_client import get_daily_data, get_intraday_data, get_daily_data_for_period

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

    def _apply_realistic_costs(self, base_price: float, is_entry: bool = True, direction: str = 'LONG') -> float:
        """Apply slippage and commissions to get realistic trade price."""
        # Add slippage
        slippage_adjustment = base_price * config.BACKTEST_SLIPPAGE_PCT
        if is_entry:
            # On entry: pay worse price (slip against us)
            if direction == 'LONG':
                adjusted_price = base_price + slippage_adjustment  # Buy higher
            else:
                adjusted_price = base_price - slippage_adjustment  # Sell lower
        else:
            # On exit: get worse price (slip against us)
            if direction == 'LONG':
                adjusted_price = base_price - slippage_adjustment  # Sell lower
            else:
                adjusted_price = base_price + slippage_adjustment  # Buy higher (covering short)

        return adjusted_price

    def _calculate_commission_cost(self, num_contracts: int) -> float:
        """Calculate total commission cost for a trade."""
        return num_contracts * config.BACKTEST_COMMISSION_PER_CONTRACT

    def _check_spread_filter(self, bid: float, ask: float) -> bool:
        """Check if bid/ask spread is within acceptable limits."""
        if bid <= 0 or ask <= 0:
            return False
        spread_pct = (ask - bid) / bid
        return spread_pct <= config.BACKTEST_MAX_SPREAD_FILTER
        
    def run_backtest(self, start_date: datetime, end_date: datetime, use_options: bool = False, progress_callback=None) -> Dict:
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
        # Need extra days for MA calculation (50-day MA needs 50 days before start)
        ma_buffer_days = config.MA_LONG + 50  # Buffer for MA calculations
        total_days_needed = backtest_days + ma_buffer_days

        # Fetch daily data from start_date - buffer to end_date
        # This ensures we have historical data for the entire backtest period
        daily_start_date = start_date - timedelta(days=ma_buffer_days)
        daily_df = get_daily_data_for_period(config.SYMBOL, daily_start_date, end_date)
        
        # Get list of trading days
        trading_days = pd.bdate_range(start=start_date, end=end_date)
        
        trades = []
        equity_curve = []
        current_position = None  # {'direction': 'LONG'/'SHORT', 'entry_price': float, 'entry_time': datetime}
        last_stop_loss = None  # {'direction': 'LONG'/'SHORT', 'time': datetime} - track last SL for cooldown
        equity = 10000.0  # Starting equity
        
        # Debug counters
        days_processed = 0
        days_skipped = 0
        signals_generated = 0
        
        # Batch fetch all intraday data if using Alpaca
        full_intraday_df = pd.DataFrame()
        if DATA_SOURCE == "alpaca":
            print(f"🚀 Batch fetching intraday data from {start_date.date()} to {end_date.date()}...")
            try:
                # Add buffer to end date to ensure we get the last day
                batch_end = end_date + timedelta(days=1)
                full_intraday_df = get_intraday_data(
                    config.SYMBOL,
                    interval=config.INTRADAY_INTERVAL,
                    start_date=start_date,
                    end_date=batch_end
                )
                if not full_intraday_df.empty:
                    # Ensure index is datetime
                    full_intraday_df.index = pd.to_datetime(full_intraday_df.index)
                    print(f"✅ Batch fetch successful: {len(full_intraday_df)} bars")
            except Exception as e:
                print(f"⚠️ Batch fetch failed: {e}. Falling back to daily fetch.")

        total_days = len(trading_days)
        for day_idx, day in enumerate(trading_days):
            try:
                # Get intraday data for this specific day
                target_date = day.date()
                
                # Strategy 1: Slice from batch data (Alpaca optimization)
                if not full_intraday_df.empty:
                    if full_intraday_df.index.tz is not None:
                        # For timezone-aware, extract date component properly
                        mask = full_intraday_df.index.date == target_date
                        intraday_df = full_intraday_df[mask].copy()
                    else:
                        # For timezone-naive
                        mask = full_intraday_df.index.date == target_date
                        intraday_df = full_intraday_df[mask].copy()
                
                # Strategy 2: Fetch daily (Fallback / yfinance)
                else:
                    # Calculate start and end of trading day
                    # IMPORTANT: yfinance end_date is EXCLUSIVE, so we need to add 1 day to get all bars
                    day_start = datetime.combine(day.date(), datetime.min.time().replace(hour=9, minute=30))
                    day_end = datetime.combine(day.date(), datetime.min.time().replace(hour=16, minute=0)) + timedelta(days=1)
                    
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
                            # Handle timezone-aware indices: get date properly for comparison
                            if intraday_df.index.tz is not None:
                                # For timezone-aware, extract date component properly
                                intraday_df['_date'] = intraday_df.index.date
                                intraday_df = intraday_df[intraday_df['_date'] == target_date].drop(columns=['_date'])
                            else:
                                # For timezone-naive, use date directly
                                intraday_df = intraday_df[intraday_df.index.date == target_date]
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
                
                # Process each bar in the day
                intraday_df_sorted = intraday_df.sort_index()

                # Fetch VIX context for this day FIRST (needed for regime analysis)
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
                    vix_level = iv_context.get('vix_level')
                except Exception:
                    # If VIX fetch fails, use empty context
                    iv_context = {}
                    vix_level = None

                # Analyze regime using daily data up to this day (now with VIX level)
                regime = analyze_regime(daily_df_up_to_day, today_data, vix_level=vix_level)
                
                last_processed_time = None
                bars_processed = 0
                bars_skipped_before_start = 0
                bars_skipped_after_close = 0
                
                if self.use_options:
                    print(f"DEBUG Loop Start for {day.date()}: Total bars in dataframe = {len(intraday_df_sorted)}")
                    if len(intraday_df_sorted) > 0:
                        print(f"  First bar: {intraday_df_sorted.index[0]}")
                        print(f"  Last bar: {intraday_df_sorted.index[-1]}")
                
                try:
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
                        
                        # Filter bars: start at SESSION_START, but allow until market close (16:00) for exits
                        if time_str < config.SESSION_START:
                            bars_skipped_before_start += 1
                            continue
                        if time_str > "16:00":  # Market close - no processing after this
                            bars_skipped_after_close += 1
                            continue
                        
                        last_processed_time = idx
                        bars_processed += 1
                        
                        current_price = row['Close']
                        
                        # Debug: Show bar data at 14:55 to verify we're using correct bar
                        if self.use_options and time_str == "14:55":
                            print(f"DEBUG 14:55 Bar: idx={idx}, time_str={time_str}, Close={current_price:.2f}, "
                                  f"High={row.get('High', 'N/A')}, Low={row.get('Low', 'N/A')}, Open={row.get('Open', 'N/A')}")
                        
                        # Block entries at and after BLOCK_TRADE_AFTER time (14:30)
                        # But continue processing exits until market close (16:00)
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
                                        # Apply realistic exit costs: slippage
                                        theoretical_exit_price = current_option_price
                                        if current_position['direction'] == 'LONG':
                                            exit_option_price = self._apply_realistic_costs(theoretical_exit_price, is_entry=False, direction='LONG')
                                        else:
                                            exit_option_price = self._apply_realistic_costs(theoretical_exit_price, is_entry=False, direction='SHORT')

                                        # Calculate P/L with realistic prices
                                        pnl = self._calculate_options_pnl(entry_option_price, exit_option_price)

                                        # Subtract commissions
                                        commission_cost = self._calculate_commission_cost(self.options_contracts)
                                        pnl -= commission_cost

                                        equity += pnl
                                        trades.append({
                                            'entry_time': current_position['entry_time'],
                                            'exit_time': idx,
                                            'direction': current_position['direction'],
                                            'entry_price': entry_option_price,  # Realistic entry price with slippage
                                            'exit_price': exit_option_price,    # Realistic exit price with slippage
                                            'theoretical_entry_price': current_position.get('theoretical_entry_price', entry_option_price),
                                            'theoretical_exit_price': theoretical_exit_price,
                                            'entry_underlying': entry_underlying_price,
                                            'exit_underlying': current_price,
                                            'pnl': pnl,  # Net P/L after commissions
                                            'commissions': commission_cost,
                                            'exit_reason': exit_reason,
                                            'strike': strike,
                                            'confidence': current_position.get('signal_confidence', 'N/A'),
                                            'reason': current_position.get('signal_reason', 'N/A'),
                                            '0dte_permission': current_position.get('0dte_permission', 'N/A')
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
                                            'exit_reason': exit_reason,
                                            'confidence': current_position.get('signal_confidence', 'N/A'),
                                            'reason': current_position.get('signal_reason', 'N/A'),
                                            '0dte_permission': current_position.get('0dte_permission', 'N/A')
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
                            market_phase=market_phase,
                            options_mode=self.use_options  # Apply stricter filters for options mode
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
                                
                                # Debug: Print every bar when in position to see price progression
                                if self.use_options and current_position is not None:
                                    print(f"DEBUG Options Check: Time={idx} ({time_str}), Underlying={current_price:.2f}, "
                                          f"Option_Price={current_option_price:.4f}, PnL%={pnl_pct*100:.2f}%, "
                                          f"T={T:.6f}, Strike={strike}")
                                
                                exit_reason = None
                                if pnl_pct >= self.options_tp_pct:
                                    exit_reason = 'TP'
                                elif pnl_pct <= -self.options_sl_pct:
                                    exit_reason = 'SL'
                                elif time_str >= "16:00":  # Market close - exit all positions
                                    exit_reason = 'EOD'
                                
                                if exit_reason:
                                    pnl = self._calculate_options_pnl(entry_option_price, current_option_price)
                                    equity += pnl
                                    
                                    # Debug: Print exit details for verification
                                    print(f"DEBUG {exit_reason} Exit: Time={idx} ({time_str}), Underlying={current_price:.2f}, "
                                          f"Entry_Underlying={entry_underlying_price:.2f}, "
                                          f"Option_Entry={entry_option_price:.4f}, Option_Exit={current_option_price:.4f}, "
                                          f"Strike={strike}, T={T:.6f}, IV={sigma:.4f}, PnL%={pnl_pct*100:.2f}%")
                                    
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
                                        'strike': strike,
                                        'confidence': current_position.get('signal_confidence', 'N/A'),
                                        'reason': current_position.get('signal_reason', 'N/A'),
                                        '0dte_permission': current_position.get('0dte_permission', 'N/A')
                                    })
                                    
                                    # Track stop loss for cooldown
                                    if exit_reason == 'SL':
                                        last_stop_loss = {
                                            'direction': current_position['direction'],
                                            'time': idx
                                        }
                                    
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
                                        'exit_reason': exit_reason,
                                        'confidence': current_position.get('signal_confidence', 'N/A'),
                                        'reason': current_position.get('signal_reason', 'N/A'),
                                        '0dte_permission': current_position.get('0dte_permission', 'N/A')
                                    })
                                    
                                    # Track stop loss for cooldown
                                    if exit_reason == 'SL':
                                        last_stop_loss = {
                                            'direction': current_position['direction'],
                                            'time': idx
                                        }
                                    
                                    current_position = None
                        
                        # Check for entry if no position
                        if current_position is None:
                            # Check cooldown: don't re-enter same direction within cooldown period after stop loss
                            skip_due_to_cooldown = False
                            if last_stop_loss is not None:
                                time_since_stop = (idx - last_stop_loss['time']).total_seconds() / 60  # minutes
                                same_direction = (
                                    (signal['direction'] == 'CALL' and last_stop_loss['direction'] == 'LONG') or
                                    (signal['direction'] == 'PUT' and last_stop_loss['direction'] == 'SHORT')
                                )
                                if same_direction and time_since_stop < config.BACKTEST_REENTRY_COOLDOWN_MINUTES:
                                    skip_due_to_cooldown = True
                            
                            if not skip_due_to_cooldown:
                                if self.use_options:
                                    # Options mode: Calculate option price at entry
                                    # Note: options_mode filter already ensures only HIGH confidence signals pass
                                    if signal['direction'] == 'CALL' and signal['confidence'] == 'HIGH':
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
                                        theoretical_price = self._get_option_price(
                                            current_price, strike, T, sigma, option_type
                                        )

                                        # Apply realistic costs: slippage and simulate bid/ask spread
                                        # For options, we assume a reasonable spread (wider for cheaper options)
                                        spread_pct = max(0.02, min(0.10, theoretical_price * 0.5))  # 2-10% spread
                                        bid_price = theoretical_price * (1 - spread_pct/2)
                                        ask_price = theoretical_price * (1 + spread_pct/2)

                                        # Check spread filter
                                        if not self._check_spread_filter(bid_price, ask_price):
                                            continue  # Skip trade if spread too wide

                                        # Apply slippage to ask price (we pay the offer)
                                        entry_option_price = self._apply_realistic_costs(ask_price, is_entry=True, direction='LONG')

                                        current_position = {
                                            'direction': 'LONG',
                                            'entry_price': entry_option_price,
                                            'entry_underlying_price': current_price,
                                            'entry_option_price': entry_option_price,
                                            'theoretical_entry_price': theoretical_price,
                                            'entry_time': idx,
                                            'strike': strike,
                                            'entry_iv': sigma,
                                            'signal_confidence': signal.get('confidence', 'N/A'),
                                            'signal_reason': signal.get('reason', 'N/A'),
                                            '0dte_permission': regime.get('0dte_status', 'N/A')
                                        }
                                    if signal['direction'] == 'PUT' and signal['confidence'] == 'HIGH':
                                        # Options mode: Only enter on HIGH confidence (filtered by options_mode)
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
                                        theoretical_price = self._get_option_price(
                                            current_price, strike, T, sigma, option_type
                                        )

                                        # Apply realistic costs: slippage and simulate bid/ask spread
                                        spread_pct = max(0.02, min(0.10, theoretical_price * 0.5))  # 2-10% spread
                                        bid_price = theoretical_price * (1 - spread_pct/2)
                                        ask_price = theoretical_price * (1 + spread_pct/2)

                                        # Check spread filter
                                        if not self._check_spread_filter(bid_price, ask_price):
                                            continue  # Skip trade if spread too wide

                                        # Apply slippage to bid price (we sell to the bid when shorting)
                                        entry_option_price = self._apply_realistic_costs(bid_price, is_entry=True, direction='SHORT')

                                        current_position = {
                                            'direction': 'SHORT',
                                            'entry_price': entry_option_price,
                                            'entry_underlying_price': current_price,
                                            'entry_option_price': entry_option_price,
                                            'theoretical_entry_price': theoretical_price,
                                            'entry_time': idx,
                                            'strike': strike,
                                            'entry_iv': sigma,
                                            'signal_confidence': signal.get('confidence', 'N/A'),
                                            'signal_reason': signal.get('reason', 'N/A'),
                                            '0dte_permission': regime.get('0dte_status', 'N/A')
                                        }
                                else:
                                    # Shares mode: Original logic
                                    if signal['direction'] == 'CALL' and signal['confidence'] in ['MEDIUM', 'HIGH']:
                                        current_position = {
                                            'direction': 'LONG',
                                            'entry_price': current_price,
                                            'entry_time': idx,
                                            'signal_confidence': signal.get('confidence', 'N/A'),
                                            'signal_reason': signal.get('reason', 'N/A'),
                                            '0dte_permission': regime.get('0dte_status', 'N/A')
                                        }
                                    elif signal['direction'] == 'PUT' and signal['confidence'] in ['MEDIUM', 'HIGH']:
                                        current_position = {
                                            'direction': 'SHORT',
                                            'entry_price': current_price,
                                            'entry_time': idx,
                                            'signal_confidence': signal.get('confidence', 'N/A'),
                                            'signal_reason': signal.get('reason', 'N/A'),
                                            '0dte_permission': regime.get('0dte_status', 'N/A')
                                        }
                        
                        # Record equity
                        equity_curve.append({
                            'timestamp': idx,
                            'equity': equity
                        })
                except Exception as e:
                    import traceback
                    print(f"ERROR processing bars for {day.date()}: {str(e)}")
                    traceback.print_exc()
                    days_skipped += 1
                    continue
                
                # Debug: Show loop summary
                if self.use_options:
                    print(f"DEBUG Loop End for {day.date()}: Bars processed={bars_processed}, "
                          f"Skipped before start={bars_skipped_before_start}, "
                          f"Skipped after close={bars_skipped_after_close}, "
                          f"Last processed={last_processed_time}")
                
                # DATA INTEGRITY CHECK: Warn if data is truncated (ends significantly before 16:00)
                if last_processed_time is not None:
                    # Get time component
                    if hasattr(last_processed_time, 'time'):
                        last_time = last_processed_time.time()
                    else:
                        last_time = pd.to_datetime(last_processed_time).time()
                    
                    # Check if before 15:30 (30 mins before close)
                    # 15:30 is SESSION_END, but data should exist until 16:00
                    if last_time < datetime.strptime("15:30", "%H:%M").time():
                        print(f"\n[WARNING] Data Truncation Detected for {day.date()}!")
                        print(f"  Last bar time: {last_time}")
                        print(f"  Expected data until: 16:00")
                        print(f"  Result: Positions forced closed at {last_time} (Reason: EOD)")
                        print(f"  Action: Check your data source (yfinance/Alpaca) for missing data.\n")
                
                # Close any remaining position at end of day
                if current_position is not None:
                    # Use last processed bar time, or fallback to last bar in dataframe
                    if last_processed_time is not None:
                        exit_time = last_processed_time
                        exit_underlying_price = intraday_df_sorted.loc[exit_time, 'Close']
                    else:
                        exit_time = intraday_df_sorted.index[-1]
                        exit_underlying_price = intraday_df_sorted.iloc[-1]['Close']
                    
                    entry_price = current_position['entry_price']
                    
                    # Debug: Show why we're closing at EOD
                    if self.use_options:
                        print(f"DEBUG EOD Close: Entry={current_position['entry_time']}, Exit={exit_time}, "
                              f"Total bars={len(intraday_df_sorted)}, Bars processed={bars_processed}, "
                              f"Last processed={last_processed_time}")
                    
                    if self.use_options:
                        # Options mode: Calculate final option price at EOD
                        strike = current_position.get('strike', get_atm_strike(exit_underlying_price))
                        option_type = 'call' if current_position['direction'] == 'LONG' else 'put'
                        
                        # Calculate T based on actual exit time (not always 0.0)
                        # If exit is at or after 4:00 PM, T = 0 (expiration)
                        # Otherwise, calculate time to expiration from exit time
                        if hasattr(exit_time, 'hour') and hasattr(exit_time, 'minute'):
                            exit_hour = exit_time.hour
                            exit_minute = exit_time.minute
                        else:
                            exit_dt = pd.to_datetime(exit_time)
                            exit_hour = exit_dt.hour
                            exit_minute = exit_dt.minute
                        
                        # If exit is at 16:00 (4:00 PM) or later, T = 0 (expiration)
                        if exit_hour >= 16:
                            T = 0.0
                        else:
                            # Calculate time to expiration from exit time
                            T = time_to_expiration_0dte(exit_hour, exit_minute)
                        
                        # Use entry IV (or VIX if available, default to 20.0 if None)
                        vix_level = iv_context.get('vix_level') or 20.0
                        sigma = current_position.get('entry_iv', vix_level / 100.0)
                        
                        # At expiration, option price = intrinsic value
                        exit_option_price = self._get_option_price(
                            exit_underlying_price, strike, T, sigma, option_type
                        )
                        
                        entry_option_price = current_position.get('entry_option_price', entry_price)
                        pnl = self._calculate_options_pnl(entry_option_price, exit_option_price)
                        
                        equity += pnl
                        
                        trades.append({
                            'entry_time': current_position['entry_time'],
                            'exit_time': exit_time,
                            'direction': current_position['direction'],
                            'entry_price': entry_option_price,
                            'exit_price': exit_option_price,
                            'entry_underlying': current_position.get('entry_underlying_price', entry_price),
                            'exit_underlying': exit_underlying_price,
                            'pnl': pnl,
                            'exit_reason': 'EOD',
                            'strike': strike,
                            'confidence': current_position.get('signal_confidence', 'N/A'),
                            'reason': current_position.get('signal_reason', 'N/A'),
                            '0dte_permission': current_position.get('0dte_permission', 'N/A')
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
                            'exit_time': exit_time,
                            'direction': current_position['direction'],
                            'entry_price': entry_price,
                            'exit_price': exit_underlying_price,
                            'pnl': pnl,
                            'exit_reason': 'EOD',
                            'confidence': current_position.get('signal_confidence', 'N/A'),
                            'reason': current_position.get('signal_reason', 'N/A'),
                            '0dte_permission': current_position.get('0dte_permission', 'N/A')
                        })
                    
                    current_position = None
                    
            except Exception as e:
                import traceback
                print(f"Error processing {day}: {str(e)}")
                traceback.print_exc()
                days_skipped += 1
                continue
            
            
            days_processed += 1
            
            # Update progress if callback provided
            if progress_callback and total_days > 0:
                progress = (day_idx + 1) / total_days
                progress_callback(progress, f"Processing day {day_idx + 1}/{total_days}: {day.date()}")
            
            # Memory cleanup: explicitly delete large DataFrames after processing
            del intraday_df
        
        # Calculate metrics
        if not trades:
            return {
                'trades': [],
                'equity_curve': pd.DataFrame(),
                'num_trades': 0,
                'win_rate': 0.0,
                'avg_r_multiple': 0.0,
                'max_drawdown': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'total_commissions': 0.0,
                'time_analysis': {}
            }
        
        trades_df = pd.DataFrame(trades)
        
        # Win rate
        # Win/Loss metrics
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0.0
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0.0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0.0
        
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
        total_commissions = trades_df.get('commissions', pd.Series()).sum()

        # Time-of-day performance analysis
        time_analysis = {}
        if 'entry_time' in trades_df.columns:
            trades_df['entry_hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour
            trades_df['entry_minute'] = pd.to_datetime(trades_df['entry_time']).dt.minute
            trades_df['entry_time_of_day'] = trades_df['entry_hour'] * 60 + trades_df['entry_minute']
            
            # Define time periods matching new config
            time_periods = {
                'Early Open (9:45-9:55)': (9*60+45, 9*60+55),
                'Morning Drive (9:55-10:30)': (9*60+55, 10*60+30),
                'Mid-Morning Trend (10:30-11:45)': (10*60+30, 11*60+45),
                'Lunch Chop (11:45-13:30)': (11*60+45, 13*60+30),
                'Afternoon Wake-up (13:30-14:15)': (13*60+30, 14*60+15),
                'Breakout Window (14:15-14:30)': (14*60+15, 14*60+30),
                'Late Day (14:30+)': (14*60+30, 16*60)
            }
            
            for period_name, (start_min, end_min) in time_periods.items():
                period_trades = trades_df[
                    (trades_df['entry_time_of_day'] >= start_min) & 
                    (trades_df['entry_time_of_day'] < end_min)
                ]
                
                # Always include period in report even if 0 trades, to confirm blocking works
                if len(period_trades) >= 0:
                    period_count = len(period_trades)
                    if period_count > 0:
                        period_win_rate = len(period_trades[period_trades['pnl'] > 0]) / period_count
                        period_avg_r = period_trades['r_multiple'].mean()
                        period_pnl = period_trades['pnl'].sum()
                    else:
                        period_win_rate = 0.0
                        period_avg_r = 0.0
                        period_pnl = 0.0
                    
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
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl,
            'total_commissions': total_commissions,
            'time_analysis': time_analysis
        }


