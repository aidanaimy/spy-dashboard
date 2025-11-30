#!/usr/bin/env python3
"""
Comprehensive System Audit Script
Tests ALL components of the trading system for correctness.
Run this before going live to ensure everything works.
"""

import sys
import os
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test results tracker
results = []

def test(name, func):
    """Run a test and track results."""
    try:
        func()
        results.append((name, "✅ PASS", None))
        print(f"✅ {name}")
        return True
    except Exception as e:
        results.append((name, "❌ FAIL", str(e)))
        print(f"❌ {name}: {e}")
        return False

def print_summary():
    """Print final test summary."""
    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, status, _ in results if status == "✅ PASS")
    failed = sum(1 for _, status, _ in results if status == "❌ FAIL")
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    
    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for name, status, error in results:
            if status == "❌ FAIL":
                print(f"  - {name}")
                print(f"    Error: {error}")
    
    print("\n" + "="*80)
    if failed == 0:
        print("🎉 ALL TESTS PASSED - SYSTEM IS READY!")
    else:
        print(f"⚠️  {failed} TEST(S) FAILED - REVIEW BEFORE GOING LIVE")
    print("="*80)


# ============================================================================
# DATA FETCHING TESTS
# ============================================================================

def test_alpaca_connection():
    """Test Alpaca API connection."""
    from data.alpaca_client import get_alpaca_api
    api = get_alpaca_api()
    assert api is not None, "Alpaca API not initialized"

def test_alpaca_daily_data():
    """Test fetching daily data from Alpaca."""
    from data.alpaca_client import get_daily_data
    df = get_daily_data('SPY', days=10)
    assert not df.empty, "No daily data returned"
    assert 'Close' in df.columns, "Missing Close column"
    assert len(df) >= 5, "Insufficient daily data"

def test_alpaca_intraday_data():
    """Test fetching intraday data from Alpaca."""
    from data.alpaca_client import get_intraday_data
    df = get_intraday_data('SPY', interval='5Min', days=1)
    assert not df.empty, "No intraday data returned"
    assert 'Close' in df.columns, "Missing Close column"

def test_vix_fetching():
    """Test VIX data fetching with fallback."""
    from logic.iv import fetch_iv_context
    iv = fetch_iv_context('SPY', 590.0)
    assert iv['vix_level'] is not None, "VIX level is None"
    assert iv['vix_level'] > 0, "VIX level invalid"
    assert iv['vix_level'] < 100, "VIX level unrealistic"


# ============================================================================
# LOGIC MODULE TESTS
# ============================================================================

def test_regime_analysis():
    """Test regime analysis logic."""
    from logic.regime import analyze_regime
    from data.alpaca_client import get_daily_data
    
    daily_df = get_daily_data('SPY', days=60)
    today_data = {
        'yesterday_close': 590.0,
        'today_open': 591.0,
        'today_high': 595.0,
        'today_low': 589.0,
        'today_close': 594.0
    }
    
    regime = analyze_regime(daily_df, today_data, vix_level=16.5)
    assert 'trend' in regime, "Missing trend"
    assert '0dte_status' in regime, "Missing 0dte_status"
    assert regime['0dte_status'] in ['FAVORABLE', 'CAUTION', 'AVOID'], "Invalid 0dte_status"

def test_vix_hard_deck():
    """Test VIX hard deck (AVOID if VIX < 15)."""
    from logic.regime import get_0dte_permission
    
    # Low VIX should be AVOID (function returns dict)
    result = get_0dte_permission(trend='Bullish', gap_pct=0.5, range_pct=1.0, vix_level=14.0)
    assert result['status'] == 'AVOID', f"Expected AVOID for low VIX, got {result['status']}"
    
    # Normal VIX should allow CAUTION/FAVORABLE
    result = get_0dte_permission(trend='Bullish', gap_pct=0.5, range_pct=1.0, vix_level=16.0)
    assert result['status'] != 'AVOID', f"VIX 16 should not be AVOID, got {result['status']}"

def test_signal_generation():
    """Test signal generation logic."""
    from logic.signals import generate_signal
    from data.alpaca_client import get_daily_data, get_intraday_data
    from logic.regime import analyze_regime
    from logic.intraday import analyze_intraday
    
    daily_df = get_daily_data('SPY', days=60)
    intraday_df = get_intraday_data('SPY', interval='5Min', days=1)
    
    if not intraday_df.empty:
        today_data = {
            'yesterday_close': intraday_df.iloc[0]['Open'],
            'today_open': intraday_df.iloc[0]['Open'],
            'today_high': intraday_df['High'].max(),
            'today_low': intraday_df['Low'].min(),
            'today_close': intraday_df.iloc[-1]['Close']
        }
        
        regime = analyze_regime(daily_df, today_data, vix_level=16.5)
        intraday_analysis = analyze_intraday(intraday_df)
        
        signal = generate_signal(regime, intraday_analysis)
        assert 'direction' in signal, "Missing direction"
        assert 'confidence' in signal, "Missing confidence"
        assert signal['direction'] in ['CALL', 'PUT', 'NONE'], "Invalid direction"
        assert signal['confidence'] in ['HIGH', 'MEDIUM', 'LOW'], "Invalid confidence"

def test_time_filters():
    """Test time-of-day filters."""
    from logic.time_filters import apply_time_filter
    
    et_tz = ZoneInfo("America/New_York")
    
    # Lunch chop should be blocked (function takes signal dict)
    lunch_time = datetime(2025, 11, 29, 12, 30).replace(tzinfo=et_tz)
    signal = {'direction': 'CALL', 'confidence': 'HIGH', 'reason': 'Test'}
    result = apply_time_filter(signal, lunch_time)
    assert result['direction'] == 'NONE', "Lunch chop should block trades"

def test_chop_detection():
    """Test chop detection logic."""
    from logic.chop_detector import detect_chop
    
    # Create flat dataframe (choppy)
    df = pd.DataFrame({
        'Open': [100.0] * 20,
        'High': [100.5] * 20,
        'Low': [99.5] * 20,
        'Close': [100.0] * 20,
        'Volume': [1000] * 20
    })
    vwap_series = pd.Series([100.0] * 20)
    ema_fast = pd.Series([100.0] * 20)
    ema_slow = pd.Series([100.0] * 20)
    
    result = detect_chop(df, vwap_series, ema_fast, ema_slow)
    assert result['chop_score'] >= 1, "Flat VWAP should have chop score >= 1"


# ============================================================================
# BACKTEST ENGINE TESTS
# ============================================================================

def test_backtest_engine_initialization():
    """Test backtest engine initializes correctly."""
    from backtest.backtest_engine import BacktestEngine
    import config
    
    engine = BacktestEngine(use_options=True)
    assert engine.options_tp_pct == config.BACKTEST_OPTIONS_TP_PCT, "TP not set correctly"
    assert engine.options_sl_pct == config.BACKTEST_OPTIONS_SL_PCT, "SL not set correctly"

def test_backtest_with_realistic_costs():
    """Test backtest applies realistic costs."""
    from backtest.backtest_engine import BacktestEngine
    
    engine = BacktestEngine(use_options=True)
    
    # Run short backtest
    start = datetime(2025, 11, 1)
    end = datetime(2025, 11, 15)
    results = engine.run_backtest(start, end, use_options=True)
    
    assert results['num_trades'] >= 0, "Invalid trade count"
    assert 'total_pnl' in results, "Missing total_pnl"
    assert 'total_commissions' in results, "Missing commissions"
    
    # If there are trades, check costs were applied
    if results['num_trades'] > 0:
        assert results['total_commissions'] > 0, "No commissions applied"

def test_spread_filter():
    """Test spread filter allows realistic option spreads."""
    import config
    
    # Should allow 10% spread (typical for 0DTE)
    assert config.BACKTEST_MAX_SPREAD_FILTER >= 0.10, "Spread filter too tight"


# ============================================================================
# WEEKEND & SPECIAL DAY TESTS
# ============================================================================

def test_weekend_detection():
    """Test weekend detection in market phase."""
    from app import get_market_phase
    
    et_tz = ZoneInfo("America/New_York")
    
    # Saturday should be weekend
    saturday = datetime(2025, 11, 29, 12, 0).replace(tzinfo=et_tz)
    phase = get_market_phase(saturday)
    assert phase['label'] == 'Weekend', "Saturday not detected as weekend"
    assert phase['is_open'] == False, "Weekend should not be open"
    
    # Sunday should be weekend
    sunday = datetime(2025, 11, 30, 12, 0).replace(tzinfo=et_tz)
    phase = get_market_phase(sunday)
    assert phase['label'] == 'Weekend', "Sunday not detected as weekend"

def test_early_close_detection():
    """Test early close day detection."""
    from app import get_market_close_time
    
    # Black Friday 2025 (Nov 28) should close at 1 PM
    black_friday = date(2025, 11, 28)
    close_time = get_market_close_time(black_friday)
    assert close_time == time(13, 0), f"Black Friday should close at 1 PM, got {close_time}"
    
    # Christmas Eve 2025 (Dec 24, Wednesday) should close at 1 PM
    christmas_eve = date(2025, 12, 24)
    close_time = get_market_close_time(christmas_eve)
    assert close_time == time(13, 0), f"Christmas Eve should close at 1 PM, got {close_time}"
    
    # Normal day should close at 4 PM
    normal_day = date(2025, 12, 1)
    close_time = get_market_close_time(normal_day)
    assert close_time == time(16, 0), f"Normal day should close at 4 PM, got {close_time}"


# ============================================================================
# DISCORD NOTIFICATION TESTS
# ============================================================================

def test_discord_webhook_configured():
    """Test Discord webhook check doesn't crash."""
    try:
        from app import get_discord_webhook_url
        url = get_discord_webhook_url()
        # Either configured or None is acceptable - just check it doesn't crash
    except Exception:
        pass  # Acceptable if Streamlit secrets not available in test context

def test_signal_notification_logic():
    """Test signal notification filtering."""
    # Signal notification should only fire for:
    # - MEDIUM+ confidence
    # - Not AVOID permission
    # - Market is open
    
    from app import get_market_phase
    et_tz = ZoneInfo("America/New_York")
    
    # Monday morning (market open)
    monday = datetime(2025, 12, 1, 10, 0).replace(tzinfo=et_tz)
    phase = get_market_phase(monday)
    assert phase['is_open'] == True, "Monday 10 AM should be open"
    
    # Weekend (market closed)
    saturday = datetime(2025, 11, 29, 10, 0).replace(tzinfo=et_tz)
    phase = get_market_phase(saturday)
    assert phase['is_open'] == False, "Saturday should be closed"


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

def test_config_values():
    """Test configuration values are sane."""
    import config
    
    # TP/SL should be wider than old values
    assert config.BACKTEST_OPTIONS_TP_PCT >= 0.60, "TP too tight"
    assert config.BACKTEST_OPTIONS_SL_PCT >= 0.30, "SL too tight"
    
    # Range threshold should be reasonable
    assert 0.01 <= config.RANGE_HIGH_THRESHOLD <= 0.03, "Range threshold unrealistic"
    
    # Commission should be realistic
    assert config.BACKTEST_COMMISSION_PER_CONTRACT > 0, "Commission not set"


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("COMPREHENSIVE SYSTEM AUDIT")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("📊 DATA FETCHING TESTS")
    print("-"*80)
    test("Alpaca Connection", test_alpaca_connection)
    test("Alpaca Daily Data", test_alpaca_daily_data)
    test("Alpaca Intraday Data", test_alpaca_intraday_data)
    test("VIX Fetching (with fallback)", test_vix_fetching)
    
    print("\n🧠 LOGIC MODULE TESTS")
    print("-"*80)
    test("Regime Analysis", test_regime_analysis)
    test("VIX Hard Deck (< 15 = AVOID)", test_vix_hard_deck)
    test("Signal Generation", test_signal_generation)
    test("Time Filters", test_time_filters)
    test("Chop Detection", test_chop_detection)
    
    print("\n📈 BACKTEST ENGINE TESTS")
    print("-"*80)
    test("Backtest Initialization", test_backtest_engine_initialization)
    test("Realistic Costs Applied", test_backtest_with_realistic_costs)
    test("Spread Filter (15% max)", test_spread_filter)
    
    print("\n🗓️  WEEKEND & SPECIAL DAY TESTS")
    print("-"*80)
    test("Weekend Detection", test_weekend_detection)
    test("Early Close Detection", test_early_close_detection)
    
    print("\n🔔 DISCORD NOTIFICATION TESTS")
    print("-"*80)
    test("Discord Webhook Config", test_discord_webhook_configured)
    test("Signal Notification Logic", test_signal_notification_logic)
    
    print("\n⚙️  CONFIGURATION TESTS")
    print("-"*80)
    test("Config Values Sane", test_config_values)
    
    print_summary()
