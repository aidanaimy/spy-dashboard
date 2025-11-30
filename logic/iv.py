"""
Option implied volatility context via yfinance.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf


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

    import time
    
    max_retries = 3
    
    # Attempt to fetch ATM IV
    for attempt in range(max_retries):
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
                    break # Success
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            atm_iv = None
            expiry = None

    vix_level = None
    vix_rank = None
    vix_percentile = None
    vix_change = None
    vix_change_pct = None
    
    # Attempt to fetch VIX data
    for attempt in range(max_retries):
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period=f"{lookback_days}d")
            if not hist.empty:
                vix_level = float(hist['Close'].iloc[-1])
                vix_min = float(hist['Close'].min())
                vix_max = float(hist['Close'].max())
                if vix_max > vix_min:
                    vix_rank = (vix_level - vix_min) / (vix_max - vix_min)
                vix_percentile = float((hist['Close'] <= vix_level).mean())
                
                # Calculate VIX change from previous day
                if len(hist) >= 2:
                    vix_prev = float(hist['Close'].iloc[-2])
                    vix_change = vix_level - vix_prev
                    vix_change_pct = (vix_change / vix_prev) * 100 if vix_prev > 0 else 0
                break # Success
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            vix_level = None
            vix_rank = None
            vix_percentile = None
            vix_change = None
            vix_change_pct = None

    # If VIX level is still None after retries, try fallback to yesterday's data
    # This is common on weekends when yfinance is slow/flaky
    if vix_level is None:
        from datetime import datetime, timedelta
        for days_back in range(1, 6):  # Try up to 5 days back
            try:
                fallback_date = datetime.now() - timedelta(days=days_back)
                vix = yf.Ticker("^VIX")
                hist = vix.history(start=fallback_date.strftime('%Y-%m-%d'), 
                                  end=(fallback_date + timedelta(days=1)).strftime('%Y-%m-%d'))
                if not hist.empty:
                    vix_level = float(hist['Close'].iloc[-1])
                    # Note: We don't calculate rank/percentile for fallback data
                    # since we don't have the full lookback window
                    vix_rank = None
                    vix_percentile = None
                    vix_change = None
                    vix_change_pct = None
                    break
            except Exception:
                continue
    
    # If still None after fallback, raise exception
    if vix_level is None:
        raise RuntimeError("Failed to fetch VIX data after retries and fallback")

    return {
        'atm_iv': atm_iv,
        'expiry': expiry,
        'vix_level': vix_level,
        'vix_rank': vix_rank,
        'vix_percentile': vix_percentile,
        'vix_change': vix_change,
        'vix_change_pct': vix_change_pct
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
            # BUGFIX: Always use list comprehension to get a Python list, not numpy array
            # hist.index.date returns numpy.ndarray which doesn't have .index() method
            hist_dates = [d.date() for d in hist.index]
            
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
                # BUGFIX: Make target_date timezone-aware to match hist.index
                # hist.index is timezone-aware from yfinance, but target_date might not be
                if hist.index.tz is not None:
                    # Make target_date timezone-aware using the same timezone as hist.index
                    if target_date.tzinfo is None:
                        import pytz
                        target_date_aware = hist.index.tz.localize(target_date.replace(hour=23, minute=59, second=59))
                    else:
                        target_date_aware = target_date
                else:
                    target_date_aware = target_date
                
                lookback_hist = hist[hist.index <= target_date_aware]
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

