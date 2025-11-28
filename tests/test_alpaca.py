#!/usr/bin/env python3
"""Test script to check Alpaca API connectivity and data fetching."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Try Streamlit secrets first
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        ALPACA_KEY = st.secrets.get('ALPACA_KEY')
        ALPACA_SECRET = st.secrets.get('ALPACA_SECRET')
        ALPACA_BASE_URL = st.secrets.get('ALPACA_BASE_URL', 'https://data.alpaca.markets/v2')
    else:
        raise AttributeError
except:
    load_dotenv()
    ALPACA_KEY = os.getenv('ALPACA_KEY')
    ALPACA_SECRET = os.getenv('ALPACA_SECRET')
    ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://data.alpaca.markets/v2')

if not ALPACA_KEY or not ALPACA_SECRET:
    print("❌ Missing Alpaca credentials!")
    exit(1)

print(f"✅ Credentials found")
print(f"   Key: {ALPACA_KEY[:10]}...")
print(f"   Base URL: {ALPACA_BASE_URL}")

try:
    import alpaca_trade_api as tradeapi
    
    api = tradeapi.REST(
        ALPACA_KEY,
        ALPACA_SECRET,
        base_url=ALPACA_BASE_URL,
        api_version='v2'
    )
    print("✅ Alpaca API client initialized")
    
    # Test 1: Get latest trade
    print("\n📊 Test 1: Latest Trade")
    try:
        trade = api.get_latest_trade("SPY")
        if trade:
            print(f"   ✅ Latest trade: ${trade.p:.2f} at {trade.t}")
        else:
            print("   ❌ No trade data")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Get latest bar (1 minute)
    print("\n📊 Test 2: Latest 1-Min Bar")
    try:
        bars = api.get_bars("SPY", "1Min", limit=1, feed='iex')
        if bars and len(bars) > 0:
            bar = bars[0]
            print(f"   ✅ Latest bar: ${bar.c:.2f} | Time: {bar.t}")
        else:
            print("   ❌ No bar data")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Get latest bar without feed (default)
    print("\n📊 Test 3: Latest 1-Min Bar (no feed specified)")
    try:
        bars = api.get_bars("SPY", "1Min", limit=1)
        if bars and len(bars) > 0:
            bar = bars[0]
            print(f"   ✅ Latest bar: ${bar.c:.2f} | Time: {bar.t}")
        else:
            print("   ❌ No bar data")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Get last 2 days of 5-minute bars (IEX)
    print("\n📊 Test 4: Last 2 Days 5-Min Bars (IEX)")
    try:
        from datetime import timedelta
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)
        two_days_ago = now_et - timedelta(days=2)
        
        start_str = two_days_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = now_et.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        bars = api.get_bars("SPY", "5Min", start=start_str, end=end_str, feed='iex')
        if bars and len(bars) > 0:
            print(f"   ✅ Got {len(bars)} bars")
            latest = bars[-1]
            print(f"   ✅ Latest: ${latest.c:.2f} at {latest.t}")
            print(f"   ✅ First: ${bars[0].c:.2f} at {bars[0].t}")
            # Check if any are from today
            today_bars = [b for b in bars if b.t.date() == now_et.date()]
            print(f"   📅 Today's bars: {len(today_bars)}")
        else:
            print("   ❌ No bars returned")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Get last 2 days of 5-minute bars without feed
    print("\n📊 Test 5: Last 2 Days 5-Min Bars (default feed)")
    try:
        bars = api.get_bars("SPY", "5Min", start=start_str, end=end_str)
        if bars and len(bars) > 0:
            print(f"   ✅ Got {len(bars)} bars")
            latest = bars[-1]
            print(f"   ✅ Latest: ${latest.c:.2f} at {latest.t}")
            today_bars = [b for b in bars if b.t.date() == now_et.date()]
            print(f"   📅 Today's bars: {len(today_bars)}")
        else:
            print("   ❌ No bars returned")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n🕐 Current time (ET): {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
except ImportError:
    print("❌ alpaca-trade-api not installed!")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

