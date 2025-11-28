"""
Time-of-day filtering logic for signal quality improvement.
Updated based on optimal trading windows.
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
    
    # === 🟥 RED ZONES (Blocked/High Caution) ===
    
    # 1. Pre-Market (< 9:45) - Blocked
    if time_str < config.SESSION_START:
        return {
            'allow_trade': False,
            'confidence_multiplier': 0.0,
            'reason': 'Pre-market period - trading blocked'
        }
        
    # 2. Lunch Chop (11:45 - 13:30) - BLOCKED (previously reduced confidence)
    # User requested block for lunch chop
    if config.LUNCH_CHOP_START <= time_str < config.LUNCH_CHOP_END:
        return {
            'allow_trade': False,
            'confidence_multiplier': 0.0,
            'reason': 'Lunch Chop (11:45-1:30) - blocked due to chop risk'
        }

    # 3. Late Day Cutoff (>= 15:30) - Blocked
    if time_str >= config.SESSION_END:
        return {
            'allow_trade': False,
            'confidence_multiplier': 0.0,
            'reason': 'Market close approaches - trading blocked'
        }

    # 4. Entry Block (>= 14:30) - Block NEW entries
    # Note: This check logic is typically handled in backtest/live execution loop
    # but good to signal here too for dashboard display
    if time_str >= config.BLOCK_TRADE_AFTER:
        return {
            'allow_trade': False,  # No NEW trades
            'confidence_multiplier': 0.0,
            'reason': f'Late day entry block (after {config.BLOCK_TRADE_AFTER}) - 0DTE theta risk'
        }

    # === 🟨 YELLOW ZONES (Reduced Confidence) ===

    # 1. Early Open Volatility (9:45 - 9:55)
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
            'reason': 'Early open volatility (first 10m) - reduced confidence'
        }
        
    # 2. Afternoon Wake-up (13:45 - 14:15) - Transition window
    # Note: Gap between 13:30 (Lunch end) and 13:45 is effectively "early afternoon" -> High Quality?
    # Based on user prompt: 1:45 PM – 2:15 PM is the transition window.
    # What about 1:30 PM - 1:45 PM? Assuming it falls into the post-lunch "High Quality" or transition?
    # Let's align strictly with prompt: 1:45 - 2:15 is reduced.
    if config.AFTERNOON_WAKEUP_START <= time_str < config.AFTERNOON_WAKEUP_END:
         return {
            'allow_trade': True,
            'confidence_multiplier': 0.7,  # Reduce confidence by 30%
            'reason': 'Afternoon transition (1:45-2:15) - reduced confidence'
        }

    # === 🟩 GREEN ZONES (Full/Boosted Confidence) ===
    
    # 1. Morning Drive (9:55 - 10:30) -> Handled by default (multiplier 1.0)
    # 2. Mid-Morning Trend (10:30 - 11:45) -> Handled by default (multiplier 1.0)
    
    # 3. Power Hour / Afternoon Breakout (14:15 - 14:30)
    # Note: Entries blocked after 14:30, so this boost applies to 14:15-14:30 window
    if config.POWER_HOUR_START <= time_str < config.BLOCK_TRADE_AFTER:
        return {
            'allow_trade': True,
            'confidence_multiplier': 1.2,  # Boost confidence by 20%
            'reason': 'Afternoon breakout window - boosted confidence'
        }

    # Default: High Quality / Normal Trading
    return {
        'allow_trade': True,
        'confidence_multiplier': 1.0,
        'reason': 'High quality trading window'
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
