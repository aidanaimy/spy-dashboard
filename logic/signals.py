"""
Rule-based signal generation combining regime and intraday analysis.
"""

from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime
import config
from logic.time_filters import apply_time_filter
from logic.chop_detector import detect_chop, apply_chop_filter

if TYPE_CHECKING:
    import pandas as pd


def generate_signal(regime: Dict, intraday: Dict, current_time: datetime = None,
                    intraday_df: 'pd.DataFrame' = None,
                    iv_context: Optional[Dict] = None,
                    market_phase: Optional[Dict] = None,
                    options_mode: bool = False) -> Dict[str, str]:
    """
    Generate trading bias signal based on regime and intraday conditions.
    Now includes time-of-day filtering and chop detection.
    
    This function is designed to be robust - it will never crash even if
    optional parameters (iv_context, market_phase, etc.) are None or malformed.
    
    Args:
        regime: Regime analysis dictionary from regime.py
        intraday: Intraday analysis dictionary from intraday.py
        current_time: Current datetime for time filtering (optional)
        intraday_df: Full intraday DataFrame for chop detection (optional)
        iv_context: IV context dictionary (optional)
        market_phase: Market phase dictionary (optional)
        options_mode: If True, applies stricter filters for options trading (default: False)
        
    Returns:
        Dictionary with 'direction' ('CALL', 'PUT', 'NONE'), 
        'confidence' ('LOW', 'MEDIUM', 'HIGH'), and 'reason'
    """
    # Safely extract values with defaults to prevent crashes
    try:
        trend = regime.get('trend', 'Mixed')
        micro_trend = intraday.get('micro_trend', 'Neutral')
        price = intraday.get('price', 0)
        vwap = intraday.get('vwap', 0)
        return_5 = intraday.get('return_5', 0)
    except (AttributeError, TypeError):
        # If regime or intraday are malformed, return safe default
        return {
            'direction': 'NONE',
            'confidence': 'LOW',
            'reason': 'Error: Invalid input data'
        }
    
    # Initialize
    direction = "NONE"
    confidence = "LOW"
    reasons = []
    
    # CALL bias conditions
    call_conditions = []
    if trend == "Bullish":
        call_conditions.append("Bullish trend")
    if micro_trend == "Up":
        call_conditions.append("Micro trend up")
    if price > vwap:
        call_conditions.append("Price above VWAP")
    if return_5 > 0:
        call_conditions.append("Positive 5-bar return")
    
    # PUT bias conditions
    put_conditions = []
    if trend == "Bearish":
        put_conditions.append("Bearish trend")
    if micro_trend == "Down":
        put_conditions.append("Micro trend down")
    if price < vwap:
        put_conditions.append("Price below VWAP")
    if return_5 < 0:
        put_conditions.append("Negative 5-bar return")
    
    # Determine direction and confidence
    call_score = len(call_conditions)
    put_score = len(put_conditions)
    
    if call_score >= 3:
        direction = "CALL"
        confidence = "HIGH" if call_score == 4 else "MEDIUM"
        reasons = call_conditions
    elif put_score >= 3:
        direction = "PUT"
        confidence = "HIGH" if put_score == 4 else "MEDIUM"
        reasons = put_conditions
    elif call_score >= 2:
        direction = "CALL"
        confidence = "LOW"
        reasons = call_conditions
    elif put_score >= 2:
        direction = "PUT"
        confidence = "LOW"
        reasons = put_conditions
    else:
        direction = "NONE"
        confidence = "LOW"
        reasons = ["Mixed signals - no clear bias"]
    
    reason_text = "; ".join(reasons) if reasons else "No clear signal"
    
    base_signal = {
        'direction': direction,
        'confidence': confidence,
        'reason': reason_text
    }
    
    # Apply chop detection if intraday_df provided
    if intraday_df is not None and len(intraday_df) >= 12:  # Need enough bars for chop detection
        vwap_series = intraday.get('vwap_series')
        ema_fast_series = intraday.get('ema_fast_series')
        ema_slow_series = intraday.get('ema_slow_series')
        
        if vwap_series is not None and ema_fast_series is not None and ema_slow_series is not None:
            try:
                chop_result = detect_chop(intraday_df, vwap_series, ema_fast_series, ema_slow_series)
                base_signal = apply_chop_filter(base_signal, chop_result)
            except Exception:
                # If chop detection fails, continue with original signal
                pass
    
    # Apply time-of-day filtering if current_time provided
    if current_time is not None:
        base_signal = apply_time_filter(base_signal, current_time)
    
    base_signal = apply_environment_filters(base_signal, regime, iv_context, market_phase)
    
    # Apply options-specific filters if in options mode
    if options_mode:
        direction = base_signal.get('direction', 'NONE')
        confidence = base_signal.get('confidence', 'LOW')
        reason = base_signal.get('reason', '')
        
        # Filter 1: Only allow HIGH confidence signals for options
        if confidence != 'HIGH':
            return {
                'direction': 'NONE',
                'confidence': 'LOW',
                'reason': f"{reason}; Options mode: requires HIGH confidence (current: {confidence})"
            }
        
        # Filter 2: Require minimum move (1%+) for options
        if abs(return_5) < 0.01:
            return {
                'direction': 'NONE',
                'confidence': 'LOW',
                'reason': f"{reason}; Options mode: requires 1%+ move (current: {return_5*100:.2f}%)"
            }
        
        # Filter 3: Require minimum IV (12%) for options
        if iv_context:
            atm_iv = iv_context.get('atm_iv')
            if atm_iv is not None and atm_iv < 12:
                return {
                    'direction': 'NONE',
                    'confidence': 'LOW',
                    'reason': f"{reason}; Options mode: IV too low ({atm_iv:.1f}% < 12%)"
                }
    
    return base_signal


def apply_environment_filters(signal: Dict, regime: Dict, iv_context: Optional[Dict], market_phase: Optional[Dict]) -> Dict:
    """
    Adjust signal confidence based on regime permission and IV context.
    """
    direction = signal.get('direction', 'NONE')
    confidence = signal.get('confidence', 'LOW')
    reason = signal.get('reason', '')

    permission = regime.get('0dte_status')
    if permission == 'AVOID' and direction != 'NONE':
        return {
            'direction': direction,
            'confidence': 'LOW',
            'reason': f"{reason}; 0DTE AVOID (choppy)"
        }
    elif permission == 'FAVORABLE' and confidence == 'MEDIUM':
        confidence = 'HIGH'
        reason = f"{reason}; 0DTE FAVORABLE (volatile)"

    if market_phase:
        phase_label = market_phase.get('label', '')
        
        # Block signals during Pre-Market and After Hours
        if not market_phase.get('is_open', False) and direction != 'NONE':
            return {
                'direction': 'NONE',
                'confidence': 'LOW',
                'reason': f"{reason}; Session {phase_label} - signals paused"
            }
        
        # Note: Afternoon Drift confidence is handled by chop detector (data-driven)
        # If market is actually choppy during 1:30-2:30, chop detector will catch it

    if iv_context:
        atm_iv = iv_context.get('atm_iv')
        vix_level = iv_context.get('vix_level')
        if atm_iv is not None and vix_level is not None:
            if atm_iv < 15 and vix_level < 15 and confidence == 'MEDIUM':
                confidence = 'LOW'
                reason = f"{reason}; Low IV (calm)"
            elif atm_iv > 20 or vix_level > 20:
                if confidence == 'MEDIUM':
                    confidence = 'HIGH'
                reason = f"{reason}; High IV (elevated volatility)"

    return {
        'direction': direction,
        'confidence': confidence,
        'reason': reason
    }

