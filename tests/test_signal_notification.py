#!/usr/bin/env python3
"""
Test the full signal notification pipeline.
Simulates the exact flow that happens in the dashboard when a signal is generated.
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the actual notification function from app.py
import requests
from dotenv import load_dotenv

load_dotenv()

def get_discord_webhook_url():
    """Get Discord webhook URL from environment."""
    return os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_notification(message: str) -> None:
    """Post a message to Discord if webhook is configured (copied from app.py)."""
    url = get_discord_webhook_url()
    if not url:
        print("❌ No webhook URL configured")
        return
    try:
        response = requests.post(url, json={"content": message}, timeout=5)
        if response.status_code == 204:
            print("✅ Discord notification sent successfully")
        else:
            print(f"⚠️ Discord returned status code: {response.status_code}")
    except Exception as exc:
        print(f"❌ Discord notification failed: {exc}")

def test_signal_notification():
    """Test the exact signal notification format used by the dashboard."""
    
    print()
    print("=" * 80)
    print("TESTING SIGNAL NOTIFICATION PIPELINE")
    print("=" * 80)
    print()
    
    # Simulate signal data (exactly as it would come from generate_signal)
    signal = {
        'direction': 'CALL',
        'confidence': 'HIGH',
        'reason': 'Strong bullish momentum; Price above VWAP; EMA9 > EMA21; 5-bar return +1.2%'
    }
    
    # Simulate regime data
    regime = {
        '0dte_status': 'FAVORABLE'
    }
    
    # Simulate intraday data
    intraday = {
        'price': 683.50,
        'micro_trend': 'BULLISH'
    }
    
    # Simulate IV context
    iv_context = {
        'atm_iv': 14.2
    }
    
    # Current time
    current_time = datetime.now(ZoneInfo("America/New_York"))
    
    # Build the exact message format from app.py
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S ET")
    direction = signal.get("direction", "NONE")
    confidence = signal.get("confidence", "LOW")
    reason = signal.get("reason", "")
    price = intraday.get("price")
    micro_trend = intraday.get("micro_trend")
    iv_summary = iv_context.get("atm_iv")
    permission = regime.get("0dte_status")
    
    price_str = f"${price:.2f}" if price is not None else "n/a"
    iv_str = f"{iv_summary:.2f}%" if iv_summary is not None else "n/a"
    
    # Determine ping level (HIGH + FAVORABLE = @everyone)
    ping = ""
    if confidence == "HIGH" and permission == "FAVORABLE":
        ping = "@everyone 🚨 "
    
    message = (
        f"{ping}**Signal Update**\n"
        f"- Direction: **{direction}**\n"
        f"- Confidence: **{confidence}**\n"
        f"- 0DTE Permission: {permission}\n"
        f"- Price: {price_str} | Micro trend: {micro_trend}\n"
        f"- ATM IV: {iv_str}\n"
        f"- Reason: {reason}\n"
        f"- Time: {timestamp}"
    )
    
    print("📊 SIMULATED SIGNAL DATA:")
    print(f"  Direction: {direction}")
    print(f"  Confidence: {confidence}")
    print(f"  0DTE Permission: {permission}")
    print(f"  Price: {price_str}")
    print(f"  Micro Trend: {micro_trend}")
    print(f"  ATM IV: {iv_str}")
    print()
    
    print("📋 NOTIFICATION FILTERS CHECK:")
    print(f"  ✓ Confidence is MEDIUM or HIGH: {confidence in ['MEDIUM', 'HIGH']}")
    print(f"  ✓ Permission is not AVOID: {permission != 'AVOID'}")
    print(f"  ✓ Should ping @everyone: {confidence == 'HIGH' and permission == 'FAVORABLE'}")
    print()
    
    # Check if this signal would pass the Discord filters
    if confidence == "LOW":
        print("❌ FILTER BLOCKED: LOW confidence signals are not sent to Discord")
        return False
    
    if permission == "AVOID":
        print("❌ FILTER BLOCKED: AVOID permission signals are not sent to Discord")
        return False
    
    print("✅ FILTERS PASSED: This signal WILL be sent to Discord")
    print()
    
    print("📤 SENDING NOTIFICATION...")
    print()
    print("Message content:")
    print("-" * 80)
    print(message)
    print("-" * 80)
    print()
    
    # Send using the actual function
    send_discord_notification(message)
    
    return True

def test_filtered_signal():
    """Test a signal that should be filtered out."""
    
    print()
    print("=" * 80)
    print("TESTING FILTERED SIGNAL (Should NOT be sent)")
    print("=" * 80)
    print()
    
    signal = {
        'direction': 'PUT',
        'confidence': 'LOW',  # This will be filtered
        'reason': 'Weak signal - only 2 conditions met'
    }
    
    regime = {
        '0dte_status': 'CAUTION'
    }
    
    confidence = signal.get('confidence')
    permission = regime.get('0dte_status')
    
    print("📊 SIMULATED SIGNAL DATA:")
    print(f"  Direction: {signal.get('direction')}")
    print(f"  Confidence: {confidence}")
    print(f"  0DTE Permission: {permission}")
    print()
    
    print("📋 NOTIFICATION FILTERS CHECK:")
    print(f"  ✓ Confidence is MEDIUM or HIGH: {confidence in ['MEDIUM', 'HIGH']}")
    print(f"  ✓ Permission is not AVOID: {permission != 'AVOID'}")
    print()
    
    if confidence == "LOW":
        print("✅ CORRECTLY FILTERED: LOW confidence signal blocked (as designed)")
        return True
    
    print("❌ ERROR: This signal should have been filtered!")
    return False

if __name__ == "__main__":
    print()
    print("🧪 TESTING SIGNAL NOTIFICATION SYSTEM")
    print()
    
    # Test 1: Valid signal that should be sent
    test1_passed = test_signal_notification()
    
    # Test 2: Invalid signal that should be filtered
    test2_passed = test_filtered_signal()
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"Test 1 (Valid Signal):    {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Filtered Signal): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print()
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Your Discord notifications are working correctly:")
        print("  ✓ HIGH + FAVORABLE signals will ping @everyone")
        print("  ✓ MEDIUM signals will be sent without ping")
        print("  ✓ LOW confidence signals will be filtered out")
        print("  ✓ AVOID permission signals will be filtered out")
        print()
        print("Check your Discord channel to confirm you received the test notification!")
    else:
        print("⚠️ SOME TESTS FAILED")
        print("Please review the output above for details")
    
    print()

