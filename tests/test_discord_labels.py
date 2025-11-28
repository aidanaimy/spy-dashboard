#!/usr/bin/env python3
"""
Test Discord notification labels for different signal types.
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import maybe_notify_signal, get_signal_cache

def test_high_favorable_signal():
    """Test HIGH + FAVORABLE signal (should get @everyone + success note)"""
    print("\n" + "="*80)
    print("TEST 1: HIGH Confidence + FAVORABLE Permission (Options Ready)")
    print("="*80)
    
    signal = {
        "direction": "CALL",
        "confidence": "HIGH",
        "reason": "Bullish trend; Micro trend up; Price above VWAP; Positive 5-bar return"
    }
    
    regime = {"0dte_status": "FAVORABLE"}
    
    intraday = {
        "price": 683.50,
        "micro_trend": "BULLISH",
        "return_5": 0.012  # 1.2% move
    }
    
    iv_context = {"atm_iv": 14.2}
    
    current_time = datetime.now(ZoneInfo("America/New_York"))
    market_phase = {"label": "Morning Drive", "is_open": True}
    
    # Clear cache
    cache = get_signal_cache()
    cache["snapshot"] = None
    
    print("\n📤 Sending notification...")
    maybe_notify_signal(signal, regime, intraday, iv_context, current_time, market_phase)
    print("✅ Should have @everyone ping + 'OPTIONS READY' note")


def test_medium_caution_signal():
    """Test MEDIUM + CAUTION signal (should get discretion warning)"""
    print("\n" + "="*80)
    print("TEST 2: MEDIUM Confidence + CAUTION Permission (Use Discretion)")
    print("="*80)
    
    signal = {
        "direction": "CALL",
        "confidence": "MEDIUM",
        "reason": "Bullish trend; Micro trend up; Price above VWAP"
    }
    
    regime = {"0dte_status": "CAUTION"}
    
    intraday = {
        "price": 683.50,
        "micro_trend": "BULLISH",
        "return_5": 0.008  # 0.8% move (below 1%)
    }
    
    iv_context = {"atm_iv": 11.5}  # Below 12%
    
    current_time = datetime.now(ZoneInfo("America/New_York"))
    market_phase = {"label": "Morning Drive", "is_open": True}
    
    # Clear cache
    cache = get_signal_cache()
    cache["snapshot"] = None
    
    print("\n📤 Sending notification...")
    maybe_notify_signal(signal, regime, intraday, iv_context, current_time, market_phase)
    print("✅ Should have NO ping + 'USE DISCRETION' warning with reasons")


def test_high_caution_signal():
    """Test HIGH + CAUTION signal (should get discretion warning)"""
    print("\n" + "="*80)
    print("TEST 3: HIGH Confidence + CAUTION Permission (Use Discretion)")
    print("="*80)
    
    signal = {
        "direction": "PUT",
        "confidence": "HIGH",
        "reason": "Bearish trend; Micro trend down; Price below VWAP; Negative 5-bar return"
    }
    
    regime = {"0dte_status": "CAUTION"}  # Not FAVORABLE
    
    intraday = {
        "price": 683.50,
        "micro_trend": "BEARISH",
        "return_5": -0.015  # -1.5% move (good)
    }
    
    iv_context = {"atm_iv": 14.2}  # Good IV
    
    current_time = datetime.now(ZoneInfo("America/New_York"))
    market_phase = {"label": "Morning Drive", "is_open": True}
    
    # Clear cache
    cache = get_signal_cache()
    cache["snapshot"] = None
    
    print("\n📤 Sending notification...")
    maybe_notify_signal(signal, regime, intraday, iv_context, current_time, market_phase)
    print("✅ Should have NO ping + 'USE DISCRETION' (0DTE is CAUTION)")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("DISCORD NOTIFICATION LABEL TESTING")
    print("="*80)
    print("\nThis will send 3 test notifications to Discord:")
    print("1. HIGH + FAVORABLE (Options Ready)")
    print("2. MEDIUM + CAUTION (Use Discretion)")
    print("3. HIGH + CAUTION (Use Discretion)")
    print("\nCheck your Discord channel to see the labels!")
    print("="*80)
    
    input("\nPress Enter to start tests...")
    
    test_high_favorable_signal()
    
    input("\nPress Enter for next test...")
    test_medium_caution_signal()
    
    input("\nPress Enter for next test...")
    test_high_caution_signal()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETE")
    print("="*80)
    print("\nCheck your Discord channel to verify the labels appear correctly!")

