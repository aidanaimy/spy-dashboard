"""
Time-of-day filtering logic for signal quality improvement.
"""

from datetime import datetime
from typing import Dict
import config


def get_time_filter(current_time: datetime) -> Dict[str, any]:
    """
    Determine time-based filtering adjustments.
    
    Args:
        current_time: Current datetime
        
    Returns:
        Dictionary with 'allow_trade', 'confidence_multiplier', 'reason'
    """
    time_str = current_time.strftime('%H:%M')
    
    # Check if in lunch period (12:00-1:00) - reduce confidence instead of blocking
    # Chop detector will catch actual choppy conditions, but we reduce confidence
    # for this known lower-quality period
    if config.AVOID_TRADE_START <= time_str < config.AVOID_TRADE_END:
        return {
            'allow_trade': True,
            'confidence_multiplier': 0.6,  # Reduce confidence by 40%
            'reason': 'Lunch period (12:00-1:00) - reduced confidence (chop detector handles actual chop)'
        }
    
    # Check if within first N minutes after open (reduce confidence)
    session_start_time = datetime.strptime(config.SESSION_START, '%H:%M').time()
    current_time_only = current_time.time()
    
    # Calculate minutes since session start
    minutes_since_open = (
        (current_time_only.hour - session_start_time.hour) * 60 +
        (current_time_only.minute - session_start_time.minute)
    )
    
    if 0 <= minutes_since_open <= config.REDUCE_CONFIDENCE_AFTER_OPEN_MINUTES:
        return {
            'allow_trade': True,
            'confidence_multiplier': 0.5,  # Reduce confidence by 50%
            'reason': f'First {config.REDUCE_CONFIDENCE_AFTER_OPEN_MINUTES} min after open - reduced confidence'
        }
    
    # Check if too close to market close - block trades
    if time_str > config.BLOCK_TRADE_AFTER:
        return {
            'allow_trade': False,
            'confidence_multiplier': 0.0,
            'reason': f'Too close to market close (after {config.BLOCK_TRADE_AFTER}) - avoid late-day trades'
        }
    
    # Check if in power hour (2:30-3:30) - increase confidence
    if time_str >= config.POWER_HOUR_START:
        return {
            'allow_trade': True,
            'confidence_multiplier': 1.2,  # Increase confidence by 20%
            'reason': 'Power hour - increased confidence'
        }
    
    # Normal trading hours
    return {
        'allow_trade': True,
        'confidence_multiplier': 1.0,
        'reason': 'Normal trading hours'
    }


def apply_time_filter(signal: Dict, current_time: datetime) -> Dict:
    """
    Apply time-based filtering to a signal.
    
    Args:
        signal: Original signal dictionary
        current_time: Current datetime
        
    Returns:
        Modified signal dictionary
    """
    time_filter = get_time_filter(current_time)
    
    # If trade not allowed, return NONE signal
    if not time_filter['allow_trade']:
        return {
            'direction': 'NONE',
            'confidence': 'LOW',
            'reason': f"{signal.get('reason', '')}; {time_filter['reason']}"
        }
    
    # Adjust confidence based on multiplier
    confidence_mult = time_filter['confidence_multiplier']
    original_confidence = signal.get('confidence', 'LOW')
    
    # Map confidence to numeric, apply multiplier, map back
    confidence_map = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}
    reverse_map = {1: 'LOW', 2: 'MEDIUM', 3: 'HIGH'}
    
    numeric_conf = confidence_map.get(original_confidence, 1)
    adjusted_conf = max(1, min(3, int(numeric_conf * confidence_mult)))
    
    new_confidence = reverse_map.get(adjusted_conf, original_confidence)
    
    # If confidence dropped significantly, might want to set to NONE
    if confidence_mult < 0.6 and original_confidence == 'LOW':
        return {
            'direction': 'NONE',
            'confidence': 'LOW',
            'reason': f"{signal.get('reason', '')}; {time_filter['reason']}"
        }
    
    return {
        'direction': signal.get('direction', 'NONE'),
        'confidence': new_confidence,
        'reason': f"{signal.get('reason', '')}; {time_filter['reason']}"
    }

