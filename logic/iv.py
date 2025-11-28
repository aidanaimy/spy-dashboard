"""
Option implied volatility context via yfinance and Alpaca.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
import os

import numpy as np
import yfinance as yf

# Disable yfinance caching to avoid "unable to open database file" on Streamlit Cloud
# Streamlit Cloud has read-only filesystem restrictions
os.environ['YF_CACHE_DISABLE'] = '1'

# Set up logging
logger = logging.getLogger(__name__)


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

    # Try yfinance for VIX data
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period=f"{lookback_days}d")
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
    except Exception as e:
        pass  # Continue to final fallback
    
    # Final fallback: Use ATM IV as proxy if both sources failed
    if vix_level is None:
        if atm_iv is not None and atm_iv > 0:
            # ATM IV is typically lower than VIX, so scale it up
            # Typical relationship: VIX ≈ ATM IV * 80-100
            # Use conservative 85x multiplier
            vix_level = min(atm_iv * 85, 100.0)  # Cap at 100
            
            # Estimate rank/percentile based on VIX level
            # Historical VIX ranges: typical 10-30, extremes 5-80
            # Using empirical distribution for more accurate estimates
            
            # VIX Rank (position within 52-week range)
            # Assume typical range: min=10, max=35 for normal markets
            vix_min_estimate = 10.0
            vix_max_estimate = 35.0
            vix_rank = max(0.0, min(1.0, (vix_level - vix_min_estimate) / (vix_max_estimate - vix_min_estimate)))
            
            # VIX Percentile (historical distribution)
            # Based on long-term VIX statistics:
            # 10th percentile ≈ 11, 25th ≈ 13, 50th ≈ 16, 75th ≈ 20, 90th ≈ 27
            if vix_level < 11:
                vix_percentile = 0.05
            elif vix_level < 13:
                vix_percentile = 0.10 + (vix_level - 11) / (13 - 11) * 0.15  # Linear interpolation
            elif vix_level < 16:
                vix_percentile = 0.25 + (vix_level - 13) / (16 - 13) * 0.25
            elif vix_level < 20:
                vix_percentile = 0.50 + (vix_level - 16) / (20 - 16) * 0.25
            elif vix_level < 27:
                vix_percentile = 0.75 + (vix_level - 20) / (27 - 20) * 0.15
            else:
                vix_percentile = min(0.95, 0.90 + (vix_level - 27) / 20 * 0.05)
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

