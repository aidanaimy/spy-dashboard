"""
Test EOD Summary - Manual Trigger

This script manually triggers the EOD summary to test the formatting
and content without waiting for 4 PM.
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eod_summary import send_eod_summary, should_send_eod_summary
from eod_tracker import get_tracker

def test_eod_summary():
    """Test the EOD summary by sending it immediately."""
    print("🧪 Testing EOD Summary...")
    print("=" * 60)
    
    # Check if it's a trading day
    et_time = datetime.now(ZoneInfo("America/New_York"))
    is_trading_day = should_send_eod_summary()
    
    print(f"Current time (ET): {et_time.strftime('%A, %B %d, %Y %I:%M %p')}")
    print(f"Trading day: {'Yes ✅' if is_trading_day else 'No ❌ (Weekend)'}")
    print()
    
    if not is_trading_day:
        print("⚠️ It's a weekend - EOD summary will not be sent")
        print("(This is expected behavior to avoid weekend alerts)")
        return
    
    # Get tracker summary
    tracker = get_tracker()
    summary = tracker.get_summary()
    
    print("📊 Current EOD Data:")
    print(f"  • Date: {tracker.data.get('date', 'Not set')}")
    print(f"  • Total signals: {summary['total_signals']}")
    print(f"  • Actionable signals: {summary['actionable_signals']}")
    print(f"  • 0DTE Permission: {summary['dte_permission']}")
    print()
    
    if tracker.data.get('date') is None:
        print("⚠️ No data available for today yet")
        print("   Dashboard needs to run first to collect data")
        return
    
    # Send the summary
    print("📤 Sending EOD summary to Discord...")
    try:
        send_eod_summary()
        print("✅ EOD summary sent successfully!")
        print()
        print("📱 Check your Discord channel to see the report!")
    except Exception as e:
        print(f"❌ Error sending EOD summary: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_eod_summary()
