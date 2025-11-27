"""
Chop detection logic to filter out ranging/choppy market conditions.
"""

import pandas as pd
import numpy as np
from typing import Dict
import config


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate Average True Range (ATR).
    
    Args:
        df: DataFrame with High, Low, Close
        period: ATR period (default: 14)
        
    Returns:
        ATR value
    """
    if len(df) < 2:
        return 0.0
    
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR is the moving average of TR
    atr = tr.rolling(window=period).mean()
    
    return atr.iloc[-1] if not atr.empty else 0.0


def count_vwap_crosses(df: pd.DataFrame, vwap: pd.Series, lookback_bars: int = 12) -> int:
    """
    Count how many times price crossed VWAP in the last N bars.
    
    Args:
        df: DataFrame with Close prices
        vwap: VWAP series
        lookback_bars: Number of bars to look back (12 = 1 hour for 5-min bars)
        
    Returns:
        Number of VWAP crosses
    """
    if len(df) < 2 or len(vwap) < 2:
        return 0
    
    # Get recent data
    recent_df = df.tail(lookback_bars)
    recent_vwap = vwap.tail(lookback_bars)
    
    if len(recent_df) < 2:
        return 0
    
    # Check for crosses: price was above VWAP, now below (or vice versa)
    price_above = recent_df['Close'] > recent_vwap
    crosses = (price_above != price_above.shift()).sum() - 1  # -1 because first bar doesn't count
    
    return max(0, crosses)


def check_ema_flat(ema_fast: pd.Series, ema_slow: pd.Series, lookback: int = 12) -> bool:
    """
    Check if EMAs are flat (not trending).
    
    Args:
        ema_fast: Fast EMA series
        ema_slow: Slow EMA series
        lookback: Number of bars to check
        
    Returns:
        True if EMAs are flat
    """
    if len(ema_fast) < lookback or len(ema_slow) < lookback:
        return False
    
    recent_fast = ema_fast.tail(lookback)
    recent_slow = ema_slow.tail(lookback)
    
    # Calculate slope (change over lookback period)
    fast_slope = abs((recent_fast.iloc[-1] - recent_fast.iloc[0]) / recent_fast.iloc[0])
    slow_slope = abs((recent_slow.iloc[-1] - recent_slow.iloc[0]) / recent_slow.iloc[0])
    
    # If both slopes are below threshold, EMAs are flat
    return fast_slope < config.CHOP_EMA_FLAT_THRESHOLD and slow_slope < config.CHOP_EMA_FLAT_THRESHOLD


def check_vwap_range(df: pd.DataFrame, vwap: pd.Series) -> bool:
    """
    Check if price range is tight around VWAP (choppy).
    
    Args:
        df: DataFrame with High, Low, Close
        vwap: VWAP series
        
    Returns:
        True if range is tight around VWAP
    """
    if len(df) == 0 or len(vwap) == 0:
        return False
    
    current_price = df['Close'].iloc[-1]
    current_vwap = vwap.iloc[-1]
    
    if current_vwap == 0:
        return False
    
    # Check if price is within VWAP ± threshold
    distance_from_vwap = abs(current_price - current_vwap) / current_vwap
    
    return distance_from_vwap < config.CHOP_VWAP_RANGE_THRESHOLD


def detect_chop(df: pd.DataFrame, vwap: pd.Series, ema_fast: pd.Series, 
                 ema_slow: pd.Series) -> Dict[str, any]:
    """
    Detect if market is in a choppy/ranging condition.
    
    Args:
        df: Intraday DataFrame with OHLCV
        vwap: VWAP series
        ema_fast: Fast EMA series
        ema_slow: Slow EMA series
        
    Returns:
        Dictionary with 'is_chop', 'reasons', 'chop_score'
    """
    if len(df) < 12:  # Need at least 12 bars (1 hour) for chop detection
        return {
            'is_chop': False,
            'reasons': [],
            'chop_score': 0
        }
    
    reasons = []
    chop_score = 0
    
    # 1. Check VWAP crosses (more than threshold = chop)
    vwap_crosses = count_vwap_crosses(df, vwap, lookback_bars=12)
    if vwap_crosses >= config.CHOP_VWAP_CROSSES_THRESHOLD:
        reasons.append(f"VWAP crossed {vwap_crosses} times in last hour")
        chop_score += 1
    
    # 2. Check if EMAs are flat
    if check_ema_flat(ema_fast, ema_slow):
        reasons.append("EMAs are flat (no trend)")
        chop_score += 1
    
    # 3. Check ATR (low ATR = low volatility = chop)
    atr = calculate_atr(df, period=14)
    current_price = df['Close'].iloc[-1]
    atr_pct = (atr / current_price) if current_price > 0 else 0
    
    if atr_pct < config.CHOP_ATR_THRESHOLD:
        reasons.append(f"Low ATR ({atr_pct*100:.2f}% < {config.CHOP_ATR_THRESHOLD*100:.2f}%)")
        chop_score += 1
    
    # 4. Check if range is tight around VWAP
    if check_vwap_range(df, vwap):
        reasons.append("Price range tight around VWAP")
        chop_score += 1
    
    # If 2+ chop signals, consider it chop
    is_chop = chop_score >= 2
    
    return {
        'is_chop': is_chop,
        'reasons': reasons,
        'chop_score': chop_score
    }


def apply_chop_filter(signal: Dict, chop_result: Dict) -> Dict:
    """
    Apply chop detection filter to a signal.
    
    Args:
        signal: Original signal dictionary
        chop_result: Result from detect_chop()
        
    Returns:
        Modified signal dictionary
    """
    if not chop_result['is_chop']:
        return signal
    
    # If chop detected, reduce to NONE or LOW confidence
    original_direction = signal.get('direction', 'NONE')
    
    if original_direction == 'NONE':
        return signal  # Already NONE, no change
    
    # Set to NONE if strong chop (3+ signals)
    if chop_result['chop_score'] >= 3:
        return {
            'direction': 'NONE',
            'confidence': 'LOW',
            'reason': f"Chop detected ({', '.join(chop_result['reasons'])})"
        }
    
    # Otherwise, reduce confidence to LOW
    return {
        'direction': original_direction,
        'confidence': 'LOW',
        'reason': f"{signal.get('reason', '')}; Chop detected ({', '.join(chop_result['reasons'])})"
    }

