#!/usr/bin/env python3
"""
Test Discord webhook notification.
Sends a sample signal alert to verify webhook is working.
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_discord_webhook_url():
    """Get Discord webhook URL from environment."""
    return os.getenv("DISCORD_WEBHOOK_URL")

def send_test_notification():
    """Send a test notification to Discord."""
    webhook_url = get_discord_webhook_url()
    
    if not webhook_url:
        print("❌ ERROR: DISCORD_WEBHOOK_URL not found in .env file")
        print("   Please add: DISCORD_WEBHOOK_URL=your_webhook_url")
        return False
    
    print(f"📡 Discord Webhook URL found: {webhook_url[:50]}...")
    print()
    
    # Create a test signal message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S ET")
    
    message = (
        "@everyone 🚨 **TEST SIGNAL - System Check**\n"
        "- Direction: **CALL**\n"
        "- Confidence: **HIGH**\n"
        "- 0DTE Permission: FAVORABLE\n"
        "- Price: $683.50 | Micro trend: BULLISH\n"
        "- ATM IV: 14.2%\n"
        "- Reason: This is a test notification to verify Discord webhook is working correctly\n"
        f"- Time: {timestamp}\n\n"
        "✅ If you see this message, your webhook is configured correctly!"
    )
    
    print("📤 Sending test notification...")
    print()
    print("Message content:")
    print("-" * 60)
    print(message)
    print("-" * 60)
    print()
    
    try:
        response = requests.post(
            webhook_url,
            json={"content": message},
            timeout=5
        )
        
        if response.status_code == 204:
            print("✅ SUCCESS! Test notification sent to Discord")
            print("   Check your Discord channel to confirm receipt")
            return True
        else:
            print(f"⚠️ WARNING: Unexpected response code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out")
        print("   Check your internet connection")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Failed to send notification")
        print(f"   Error: {str(e)}")
        return False

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("DISCORD WEBHOOK TEST")
    print("=" * 60)
    print()
    
    success = send_test_notification()
    
    print()
    if success:
        print("🎉 Test completed successfully!")
        print("   Your Discord notifications are ready to use")
    else:
        print("⚠️ Test failed. Please check:")
        print("   1. DISCORD_WEBHOOK_URL is set in .env file")
        print("   2. Webhook URL is valid and not expired")
        print("   3. You have internet connection")
    print()

