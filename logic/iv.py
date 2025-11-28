"""
Option implied volatility context via yfinance and Alpaca.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf

# Try to import Alpaca for VIX data
try:
    from data.alpaca_client import get_alpaca_api
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    get_alpaca_api = None


def fetch_iv_context(symbol: str, reference_price: float, lookback_days: int = 252) -> Dict[str, Optional[float]]:
    """
    Fetch ATM implied volatility using yfinance option chain and compute
    VIX-based percentile/rank as a proxy for broader volatility regime.

    Args:
        symbol: Underlying symbol (e.g., SPY)
        reference_price: Current price used to locate ATM strike
        lookback_days: Days for VIX percentile/rank calculation

    Returns:
        Dict with iv metrics.
    """
    atm_iv = None
    expiry = None

    try:
        ticker = yf.Ticker(symbol)
        options = ticker.options
        if options:
            expiry = options[0]
            chain = ticker.option_chain(expiry)
            calls = chain.calls
            puts = chain.puts

            if not calls.empty and not puts.empty:
                call_idx = (calls['strike'] - reference_price).abs().idxmin()
                put_idx = (puts['strike'] - reference_price).abs().idxmin()
                atm_call_iv = float(calls.loc[call_idx, 'impliedVolatility'])
                atm_put_iv = float(puts.loc[put_idx, 'impliedVolatility'])
                atm_iv = np.mean([atm_call_iv, atm_put_iv]) * 100  # convert to %
    except Exception:
        atm_iv = None
        expiry = None

    vix_level = None
    vix_rank = None
    vix_percentile = None

    print(f"[IV FETCH] Starting VIX fetch, ALPACA_AVAILABLE={ALPACA_AVAILABLE}")
    
    # Try Alpaca first for VIX data (more reliable on Streamlit Cloud)
    if ALPACA_AVAILABLE:
        try:
            api = get_alpaca_api()
            print(f"[IV FETCH] Alpaca API initialized: {api is not None}")
            if api is not None:
                # Fetch VIX daily data from Alpaca
                end_date = datetime.now()
                start_date = end_date - timedelta(days=lookback_days + 30)
                
                print(f"[IV FETCH] Fetching Alpaca VIX from {start_date.date()} to {end_date.date()}")
                bar_set = api.get_bars(
                    'VIX',
                    '1Day',
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    adjustment='raw'
                )
                
                bars = bar_set.df
                print(f"[IV FETCH] Alpaca returned {len(bars)} bars")
                if not bars.empty:
                    # Get last valid VIX close (skip if zero/invalid)
                    valid_closes = bars['close'][bars['close'] > 0]
                    if not valid_closes.empty:
                        vix_level = float(valid_closes.iloc[-1])
                        vix_min = float(valid_closes.min())
                        vix_max = float(valid_closes.max())
                        if vix_max > vix_min:
                            vix_rank = (vix_level - vix_min) / (vix_max - vix_min)
                        vix_percentile = float((valid_closes <= vix_level).mean())
                        print(f"[IV FETCH] ✓ Alpaca VIX success: {vix_level:.2f}")
        except Exception as e:
            # Log error for debugging on Streamlit Cloud
            print(f"[IV FETCH] ✗ Alpaca VIX fetch failed: {str(e)}")
            pass  # Fall through to yfinance fallback
    
    # Fallback to yfinance if Alpaca didn't work
    if vix_level is None:
        print(f"[IV FETCH] Trying yfinance fallback...")
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period=f"{lookback_days}d")
            print(f"[IV FETCH] yfinance returned {len(hist)} days")
            if not hist.empty:
                # Get last valid VIX close (skip if zero/invalid)
                valid_closes = hist['Close'][hist['Close'] > 0]
                if not valid_closes.empty:
                    vix_level = float(valid_closes.iloc[-1])
                    vix_min = float(valid_closes.min())
                    vix_max = float(valid_closes.max())
                    if vix_max > vix_min:
                        vix_rank = (vix_level - vix_min) / (vix_max - vix_min)
                    vix_percentile = float((valid_closes <= vix_level).mean())
                    print(f"[IV FETCH] ✓ yfinance VIX success: {vix_level:.2f}")
        except Exception as e:
            # Log error for debugging on Streamlit Cloud
            print(f"[IV FETCH] ✗ yfinance VIX fetch failed: {str(e)}")
            pass  # Continue to final fallback
    
    # Final fallback: Use ATM IV as proxy if both sources failed
    if vix_level is None:
        if atm_iv is not None and atm_iv > 0:
            vix_level = atm_iv  # Use ATM IV as VIX proxy
            vix_rank = 0.5  # Assume middle of range
            vix_percentile = 0.5  # Assume middle percentile
        else:
            vix_level = None
            vix_rank = None
            vix_percentile = None

    return {
        'atm_iv': atm_iv,
        'expiry': expiry,
        'vix_level': vix_level,
        'vix_rank': vix_rank,
        'vix_percentile': vix_percentile
    }


def fetch_historical_vix_context(target_date: datetime, lookback_days: int = 252) -> Dict[str, Optional[float]]:
    """
    Fetch historical VIX data for a specific date (for backtesting).
    
    Args:
        target_date: The date to fetch VIX data for
        lookback_days: Days for VIX percentile/rank calculation (from target_date backwards)
        
    Returns:
        Dict with vix metrics (atm_iv will be None for historical data)
    """
    vix_level = None
    vix_rank = None
    vix_percentile = None
    
    try:
        vix = yf.Ticker("^VIX")
        # Fetch historical data up to target_date
        end_date = target_date.date()
        start_date = end_date - timedelta(days=lookback_days + 30)  # Extra buffer for weekends/holidays
        
        hist = vix.history(start=start_date, end=end_date + timedelta(days=1))
        
        if not hist.empty:
            # Get VIX level on or before target_date
            target_date_only = target_date.date()
            hist_dates = hist.index.date if hasattr(hist.index, 'date') else [d.date() for d in hist.index]
            
            # Find the closest date <= target_date
            valid_dates = [d for d in hist_dates if d <= target_date_only]
            if valid_dates:
                closest_date = max(valid_dates)
                date_idx = hist_dates.index(closest_date) if closest_date in hist_dates else -1
                if date_idx >= 0:
                    # Use OPEN price to avoid look-ahead bias
                    vix_level = float(hist['Open'].iloc[date_idx])
            
            # Calculate rank and percentile from lookback period ending at target_date
            if vix_level is not None:
                lookback_hist = hist[hist.index <= target_date]
                if len(lookback_hist) >= 20:  # Need some data for meaningful stats
                    # Use last lookback_days worth of data
                    lookback_hist = lookback_hist.tail(min(lookback_days, len(lookback_hist)))
                    vix_min = float(lookback_hist['Close'].min())
                    vix_max = float(lookback_hist['Close'].max())
                    if vix_max > vix_min:
                        vix_rank = (vix_level - vix_min) / (vix_max - vix_min)
                    vix_percentile = float((lookback_hist['Close'] <= vix_level).mean())
    except Exception:
        vix_level = None
        vix_rank = None
        vix_percentile = None
    
    return {
        'atm_iv': vix_level,  # Use VIX as proxy for ATM IV in backtest
        'expiry': None,
        'vix_level': vix_level,
        'vix_rank': vix_rank,
        'vix_percentile': vix_percentile
    }

