"""
Option implied volatility context via yfinance.
"""

from typing import Dict, Optional

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
    except Exception:
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

