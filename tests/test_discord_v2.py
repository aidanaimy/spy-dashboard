
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import maybe_notify_signal, check_and_send_eod_summary, get_signal_cache, get_eod_status
import core.config as config

def test_multi_ticker_signals():
    print("\n🧪 Testing Multi-Ticker Signals...")
    
    # Mock data
    current_time = datetime.now(ZoneInfo("America/New_York"))
    market_phase = {"is_open": True, "label": "Market Open"}
    iv_context = {"atm_iv": 15.5, "vix_level": 14.2}
    
    # Test 1: SPY Signal
    print("\n1. Sending SPY Signal...")
    spy_signal = {"direction": "CALL", "confidence": "HIGH", "reason": "Test SPY Signal"}
    spy_regime = {"0dte_status": "FAVORABLE", "trend": "BULLISH"}
    spy_intraday = {"price": 500.00, "vwap": 498.50, "micro_trend": "BULLISH"}
    
    maybe_notify_signal(
        signal=spy_signal,
        regime=spy_regime,
        intraday=spy_intraday,
        iv_context=iv_context,
        current_time=current_time,
        market_phase=market_phase,
        ticker="SPY"
    )
    
    # Test 2: IWM Signal
    print("\n2. Sending IWM Signal...")
    iwm_signal = {"direction": "PUT", "confidence": "HIGH", "reason": "Test IWM Signal"}
    iwm_regime = {"0dte_status": "FAVORABLE", "trend": "BEARISH"}
    iwm_intraday = {"price": 200.00, "vwap": 202.50, "micro_trend": "BEARISH"}
    
    maybe_notify_signal(
        signal=iwm_signal,
        regime=iwm_regime,
        intraday=iwm_intraday,
        iv_context=iv_context,
        current_time=current_time,
        market_phase=market_phase,
        ticker="IWM"
    )

def test_eod_summary():
    print("\n🧪 Testing EOD Summary...")
    
    # Force EOD check by simulating time after close
    # Note: This requires the 'force' parameter in check_and_send_eod_summary 
    # OR we need to mock the time check within the function.
    # Since we can't easily mock internal time checks without patching, 
    # we will rely on the fact that the user might have approved the 'force' change 
    # or we will just call it and see if it prints the "Generating" message if time allows.
    
    # Actually, to properly test this without modifying app.py again, 
    # we can just call it. If it's before 4:05 PM, it will return early.
    # If we really want to test it now, we should have added the 'force' param.
    # Let's try calling it with a future time object!
    
    future_time = datetime.now(ZoneInfo("America/New_York")).replace(hour=16, minute=10)
    print(f"Simulating time: {future_time}")
    
    # Reset status to ensure it runs
    status = get_eod_status()
    status["sent"] = False
    
    check_and_send_eod_summary(future_time)

if __name__ == "__main__":
    print("=" * 60)
    print("DISCORD V2 LOGIC TEST")
    print("=" * 60)
    
    # Clear caches
    get_signal_cache().clear()
    
    test_multi_ticker_signals()
    test_eod_summary()
    
    print("\n✅ Test execution complete. Check Discord for notifications.")
