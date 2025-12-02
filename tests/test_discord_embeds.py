"""
Test Discord Enhanced Embeds

This script sends test notifications to verify the new Discord embed formatting.
It will send:
1. ACTIONABLE signal (HIGH + FAVORABLE CALL) - Green border
2. AWARENESS signal (MEDIUM + CAUTION PUT) - Orange border
3. AWARENESS signal (HIGH + CAUTION CALL) - Yellow border
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
from app import send_discord_notification

def test_actionable_signal():
    """Test HIGH + FAVORABLE signal (should ping @everyone with green border)"""
    print("📤 Sending ACTIONABLE signal (HIGH + FAVORABLE CALL)...")
    
    embed = {
        "title": "CALL Signal (HIGH)",
        "description": "🎯 **ACTIONABLE SIGNAL**\n\n**The Setup:**\nMarket showing **CALL** bias. Daily trend is **Bullish** and micro-trend is **Up**. Price ($682.16) trading **above** VWAP.",
        "color": 0x00ff88,  # Bright green
        "fields": [
            {
                "name": "📋 Signal Details",
                "value": "**Direction:** CALL\n**Confidence:** HIGH\n**0DTE Status:** FAVORABLE\n**Session:** Morning Drive",
                "inline": True
            },
            {
                "name": "📊 Market Context",
                "value": "**ATM IV:** 18.5%\n**VIX:** 22.3\n**Price:** $682.16\n**VWAP:** $680.45",
                "inline": True
            },
            {
                "name": "👉 Suggested Contract",
                "value": "**SPY 682C (0DTE)**",
                "inline": False
            },
            {
                "name": "💡 Rationale",
                "value": "Bullish trend; Micro trend up; Price above VWAP; Positive 5-bar return; Morning Drive (strong directional movement); 0DTE FAVORABLE (volatile)",
                "inline": False
            }
        ],
        "footer": {
            "text": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET")
        }
    }
    
    send_discord_notification(
        message="@everyone 🚨 **HIGH + FAVORABLE SIGNAL DETECTED**",
        embed=embed
    )
    print("✅ Sent!")


def test_awareness_put():
    """Test MEDIUM + CAUTION signal (awareness only, orange border)"""
    print("\n📤 Sending AWARENESS signal (MEDIUM + CAUTION PUT)...")
    
    embed = {
        "title": "PUT Signal (MEDIUM)",
        "description": "ℹ️ **AWARENESS ONLY** (Wait for HIGH + FAVORABLE)\n\n**The Setup:**\nMarket showing **PUT** bias. Daily trend is **Bullish** and micro-trend is **Down**. Price ($679.95) trading **below** VWAP.",
        "color": 0xff9966,  # Orange
        "fields": [
            {
                "name": "📋 Signal Details",
                "value": "**Direction:** PUT\n**Confidence:** MEDIUM\n**0DTE Status:** CAUTION\n**Session:** Mid-Morning Trend",
                "inline": True
            },
            {
                "name": "📊 Market Context",
                "value": "**ATM IV:** 10.87%\n**VIX:** 16.2\n**Price:** $679.95\n**VWAP:** $681.20",
                "inline": True
            },
            {
                "name": "👉 Suggested Contract",
                "value": "**SPY 680P (0DTE)**",
                "inline": False
            },
            {
                "name": "💡 Rationale",
                "value": "Micro trend down; Price below VWAP; Negative 5-bar return; Mid-Morning Trend (sustained moves)",
                "inline": False
            }
        ],
        "footer": {
            "text": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET")
        }
    }
    
    send_discord_notification(
        message=None,  # No @everyone ping
        embed=embed
    )
    print("✅ Sent!")


def test_awareness_call():
    """Test HIGH + CAUTION signal (awareness only, yellow border)"""
    print("\n📤 Sending AWARENESS signal (HIGH + CAUTION CALL)...")
    
    embed = {
        "title": "CALL Signal (HIGH)",
        "description": "ℹ️ **AWARENESS ONLY** (Wait for HIGH + FAVORABLE)\n\n**The Setup:**\nMarket showing **CALL** bias. Daily trend is **Bullish** and micro-trend is **Up**. Price ($683.02) trading **above** VWAP.",
        "color": 0xffaa00,  # Yellow/amber
        "fields": [
            {
                "name": "📋 Signal Details",
                "value": "**Direction:** CALL\n**Confidence:** HIGH\n**0DTE Status:** CAUTION\n**Session:** Morning Drive",
                "inline": True
            },
            {
                "name": "📊 Market Context",
                "value": "**ATM IV:** 9.71%\n**VIX:** 16.8\n**Price:** $683.02\n**VWAP:** $680.50",
                "inline": True
            },
            {
                "name": "👉 Suggested Contract",
                "value": "**SPY 683C (0DTE)**",
                "inline": False
            },
            {
                "name": "💡 Rationale",
                "value": "Bullish trend; Micro trend up; Price above VWAP; Positive 5-bar return; Morning Drive (strong directional movement)",
                "inline": False
            }
        ],
        "footer": {
            "text": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET")
        }
    }
    
    send_discord_notification(
        message=None,  # No @everyone ping
        embed=embed
    )
    print("✅ Sent!")


if __name__ == "__main__":
    print("🎨 Testing Enhanced Discord Embeds\n")
    print("=" * 50)
    
    # Check if Discord webhook is configured
    from app import get_discord_webhook_url
    webhook_url = get_discord_webhook_url()
    
    if not webhook_url:
        print("❌ ERROR: Discord webhook not configured!")
        print("Please set DISCORD_WEBHOOK_URL in your .env file or Streamlit secrets.")
        sys.exit(1)
    
    print(f"✓ Discord webhook configured: {webhook_url[:50]}...")
    print("\n" + "=" * 50 + "\n")
    
    # Send test messages
    test_actionable_signal()
    test_awareness_put()
    test_awareness_call()
    
    print("\n" + "=" * 50)
    print("\n✅ All test messages sent!")
    print("\nCheck your Discord channel to see the beautiful embeds!")
    print("\n📋 Color Key:")
    print("  🟢 Green border = ACTIONABLE (HIGH + FAVORABLE)")
    print("  🟡 Yellow border = AWARENESS (HIGH + CAUTION)")  
    print("  🟠 Orange border = AWARENESS (MEDIUM + CAUTION)")
    print("  🔴 Red border = ACTIONABLE (HIGH + FAVORABLE PUT)")
