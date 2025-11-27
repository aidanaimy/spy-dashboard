"""
Intraday analysis: VWAP, EMAs, returns, volatility, and micro trend.
"""

import pandas as pd
import numpy as np
from typing import Dict
import config


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP).
    VWAP resets each trading day (calculated from market open to close).
    
    Args:
        df: Intraday OHLCV dataframe with Volume column (should only contain regular trading hours: 9:30 AM - 4:00 PM ET)
        
    Returns:
        Series with VWAP values
    """
    if df.empty or 'Volume' not in df.columns:
        return pd.Series(dtype=float, index=df.index)
    
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    # VWAP = cumulative (price * volume) / cumulative volume
    # This resets each day since we filter to single-day data
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap


def calculate_ema(df: pd.DataFrame, period: int, column: str = 'Close') -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        df: DataFrame with price data
        period: EMA period
        column: Column to calculate EMA on (default: 'Close')
        
    Returns:
        Series with EMA values
    """
    return df[column].ewm(span=period, adjust=False).mean()


def calculate_returns(df: pd.DataFrame, periods: int = 1) -> pd.Series:
    """
    Calculate percentage returns over N periods.
    
    Args:
        df: DataFrame with Close prices
        periods: Number of periods to look back
        
    Returns:
        Series with percentage returns
    """
    return df['Close'].pct_change(periods=periods) * 100


def calculate_realized_volatility(df: pd.DataFrame, lookback: int = config.VOLATILITY_LOOKBACK) -> float:
    """
    Calculate short-term realized volatility as std dev of returns.
    
    Args:
        df: DataFrame with Close prices
        lookback: Number of bars to look back
        
    Returns:
        Realized volatility (annualized, as percentage)
    """
    returns = calculate_returns(df, periods=1)
    recent_returns = returns.tail(lookback)
    
    if len(recent_returns) < 2:
        return 0.0
    
    # Calculate std dev and annualize (assuming ~252 trading days, ~78 5-min bars per day)
    bars_per_day = 78  # Approximate for 5-min bars
    std_daily = recent_returns.std()
    vol_annualized = std_daily * np.sqrt(bars_per_day * 252)
    
    return vol_annualized


def get_micro_trend(price: float, ema_fast: float, ema_slow: float, vwap: float) -> str:
    """
    Determine micro trend based on EMAs and VWAP.
    
    Args:
        price: Current price
        ema_fast: Fast EMA value
        ema_slow: Slow EMA value
        vwap: VWAP value
        
    Returns:
        'Up', 'Down', or 'Neutral'
    """
    if ema_fast > ema_slow and price > vwap:
        return "Up"
    elif ema_fast < ema_slow and price < vwap:
        return "Down"
    else:
        return "Neutral"


def analyze_intraday(df: pd.DataFrame) -> Dict:
    """
    Complete intraday analysis.
    
    Args:
        df: Intraday OHLCV dataframe
        
    Returns:
        Dictionary with all intraday metrics
    """
    if df.empty:
        raise ValueError("Empty dataframe for intraday analysis")
    
    df_sorted = df.sort_index()
    
    # Calculate indicators
    vwap = calculate_vwap(df_sorted)
    ema_fast = calculate_ema(df_sorted, config.EMA_FAST)
    ema_slow = calculate_ema(df_sorted, config.EMA_SLOW)
    
    # Get latest values
    latest_idx = df_sorted.index[-1]
    latest_price = df_sorted.loc[latest_idx, 'Close']
    latest_vwap = vwap.loc[latest_idx]
    latest_ema_fast = ema_fast.loc[latest_idx]
    latest_ema_slow = ema_slow.loc[latest_idx]
    
    # Calculate returns
    returns_1 = calculate_returns(df_sorted, periods=1)
    returns_5 = calculate_returns(df_sorted, periods=5)
    
    latest_return_1 = returns_1.loc[latest_idx] if not pd.isna(returns_1.loc[latest_idx]) else 0.0
    latest_return_5 = returns_5.loc[latest_idx] if not pd.isna(returns_5.loc[latest_idx]) else 0.0
    
    # Distance from VWAP
    vwap_distance = ((latest_price - latest_vwap) / latest_vwap) * 100 if latest_vwap > 0 else 0.0
    
    # Realized volatility
    realized_vol = calculate_realized_volatility(df_sorted)
    
    # Micro trend
    micro_trend = get_micro_trend(latest_price, latest_ema_fast, latest_ema_slow, latest_vwap)
    
    return {
        'price': latest_price,
        'vwap': latest_vwap,
        'ema_fast': latest_ema_fast,
        'ema_slow': latest_ema_slow,
        'return_1': latest_return_1,
        'return_5': latest_return_5,
        'vwap_distance': vwap_distance,
        'realized_vol': realized_vol,
        'micro_trend': micro_trend,
        'vwap_series': vwap,
        'ema_fast_series': ema_fast,
        'ema_slow_series': ema_slow
    }

