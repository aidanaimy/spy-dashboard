"""
Daily regime analysis: trend, gap, range, and 0DTE permission logic.
"""

import pandas as pd
import numpy as np
from typing import Dict
import config


def calculate_moving_averages(df: pd.DataFrame, short: int = config.MA_SHORT, 
                              long: int = config.MA_LONG) -> Dict[str, float]:
    """
    Calculate short and long moving averages.
    Handles cases where insufficient data is available.
    
    Args:
        df: Daily OHLCV dataframe
        short: Short MA period (default: 20)
        long: Long MA period (default: 50)
        
    Returns:
        Dictionary with 'ma_short' and 'ma_long' values
    """
    df_sorted = df.sort_index()
    available_days = len(df_sorted)
    
    # Calculate short MA (use available data if less than requested)
    if available_days < short:
        # Use all available data if we have less than short period
        ma_short = df_sorted['Close'].mean() if available_days > 0 else 0.0
    else:
        ma_short = df_sorted['Close'].tail(short).mean()
    
    # Calculate long MA (use available data if less than requested)
    if available_days < long:
        # Use all available data if we have less than long period
        ma_long = df_sorted['Close'].mean() if available_days > 0 else 0.0
    else:
        ma_long = df_sorted['Close'].tail(long).mean()
    
    return {
        'ma_short': ma_short,
        'ma_long': ma_long
    }


def get_trend(latest_close: float, ma_short: float, ma_long: float) -> Dict[str, str]:
    """
    Determine daily trend based on price relative to MAs.
    Handles cases where long MA might not be available.
    
    Args:
        latest_close: Latest closing price
        ma_short: Short MA value
        ma_long: Long MA value (may be 0 if insufficient data)
        
    Returns:
        Dictionary with 'trend' ('Bullish', 'Bearish', 'Mixed') and 'description'
    """
    # If we don't have long MA data, use only short MA
    if ma_long == 0.0 or ma_long is None:
        if latest_close > ma_short:
            trend = "Bullish"
            desc = f"SPY above {config.MA_SHORT}D (limited data)"
        elif latest_close < ma_short:
            trend = "Bearish"
            desc = f"SPY below {config.MA_SHORT}D (limited data)"
        else:
            trend = "Neutral"
            desc = f"SPY at {config.MA_SHORT}D (limited data)"
    else:
        # Full analysis with both MAs
        if latest_close > ma_short and latest_close > ma_long:
            trend = "Bullish"
            desc = f"SPY above {config.MA_SHORT}D & {config.MA_LONG}D"
        elif latest_close < ma_short:
            trend = "Bearish"
            desc = f"SPY below {config.MA_SHORT}D"
        else:
            trend = "Mixed"
            desc = f"SPY between {config.MA_SHORT}D & {config.MA_LONG}D"
    
    return {
        'trend': trend,
        'description': desc
    }


def calculate_gap(yesterday_close: float, today_open: float) -> Dict[str, float]:
    """
    Calculate gap percentage.
    
    Args:
        yesterday_close: Yesterday's closing price
        today_open: Today's opening price
        
    Returns:
        Dictionary with 'gap' (absolute value) and 'gap_pct' (percentage)
    """
    gap = today_open - yesterday_close
    gap_pct = (gap / yesterday_close) * 100 if yesterday_close > 0 else 0.0
    
    return {
        'gap': gap,
        'gap_pct': gap_pct
    }


def calculate_range(today_open: float, today_high: float, today_low: float) -> Dict[str, float]:
    """
    Calculate intraday range percentage.
    
    Args:
        today_open: Today's opening price
        today_high: Today's high (so far)
        today_low: Today's low (so far)
        
    Returns:
        Dictionary with 'range' (absolute value) and 'range_pct' (percentage of open)
    """
    range_val = today_high - today_low
    range_pct = (range_val / today_open) * 100 if today_open > 0 else 0.0
    
    return {
        'range': range_val,
        'range_pct': range_pct
    }


def classify_range(range_pct: float) -> str:
    """
    Classify range as Low, Normal, or High.
    
    Args:
        range_pct: Range as percentage of open
        
    Returns:
        'Low', 'Normal', or 'High'
    """
    if range_pct < config.RANGE_LOW_THRESHOLD * 100:
        return "Low"
    elif range_pct > config.RANGE_HIGH_THRESHOLD * 100:
        return "High"
    else:
        return "Normal"


def get_0dte_permission(trend: str, gap_pct: float, range_pct: float, vix_level: float = None) -> Dict[str, str]:
    """
    Determine 0DTE permission based on trend, gap, range, and VIX level.

    Args:
        trend: Trend classification ('Bullish', 'Bearish', 'Mixed')
        gap_pct: Gap percentage (absolute value)
        range_pct: Range percentage
        vix_level: Current VIX level (optional)

    Returns:
        Dictionary with 'status' ('AVOID', 'CAUTION', 'FAVORABLE') and 'reason'
    """
    gap_abs = abs(gap_pct)

    # HARD DECK: AVOID if VIX <= 15 (too calm for options)
    if vix_level is not None and vix_level <= 15:
        return {
            'status': 'AVOID',
            'reason': 'VIX too low - avoid 0DTE options (insufficient volatility)',
            'score': 0.0
        }

    # AVOID: small gap + low range = likely chop
    if gap_abs < config.GAP_SMALL_THRESHOLD * 100 and range_pct < config.RANGE_LOW_THRESHOLD * 100:
        return {
            'status': 'AVOID',
            'reason': 'Likely chop - avoid aggressive 0DTE directions',
            'score': 0.0
        }
    
    # FAVORABLE: high range = volatile day, directional OK
    if range_pct > config.RANGE_HIGH_THRESHOLD * 100:
        return {
            'status': 'FAVORABLE',
            'reason': 'Volatile day - directional 0DTE OK',
            'score': 1.0
        }
    
    # CAUTION: mixed conditions
    return {
        'status': 'CAUTION',
        'reason': 'Mixed conditions - use caution',
        'score': range_pct / (config.RANGE_HIGH_THRESHOLD * 100)
    }


def analyze_regime(daily_df: pd.DataFrame, today_data: Dict, vix_level: float = None) -> Dict:
    """
    Complete regime analysis combining all components.
    
    Args:
        daily_df: Daily OHLCV dataframe
        today_data: Dictionary with today's and yesterday's prices
        
    Returns:
        Complete regime dictionary with trend, gap, range, and 0DTE permission
    """
    # Calculate MAs
    mas = calculate_moving_averages(daily_df)
    latest_close = daily_df.sort_index().iloc[-1]['Close']
    
    # Get trend
    trend_info = get_trend(latest_close, mas['ma_short'], mas['ma_long'])
    
    # Calculate gap
    gap_info = calculate_gap(today_data['yesterday_close'], today_data['today_open'])
    
    # Calculate range
    range_info = calculate_range(
        today_data['today_open'],
        today_data['today_high'],
        today_data['today_low']
    )
    range_class = classify_range(range_info['range_pct'])
    
    # Get 0DTE permission
    permission = get_0dte_permission(
        trend_info['trend'],
        gap_info['gap_pct'],
        range_info['range_pct'],
        vix_level
    )
    
    return {
        'trend': trend_info['trend'],
        'trend_description': trend_info['description'],
        'ma_short': mas['ma_short'],
        'ma_long': mas['ma_long'],
        'latest_close': latest_close,
        'gap': gap_info['gap'],
        'gap_pct': gap_info['gap_pct'],
        'range': range_info['range'],
        'range_pct': range_info['range_pct'],
        'range_class': range_class,
        '0dte_status': permission['status'],
        '0dte_reason': permission['reason']
    }

