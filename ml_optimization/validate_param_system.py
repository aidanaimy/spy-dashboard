#!/usr/bin/env python3
"""
Validation tests for parameter override system.
Tests that different parameters produce different results.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import BacktestEngine

print("=" * 80)
print("PARAMETER OVERRIDE VALIDATION TESTS")
print("=" * 80)
print()

# Test period: 1 month
start_date = datetime(2024, 11, 1)
end_date = datetime(2024, 11, 30)

print(f"Test Period: {start_date.date()} to {end_date.date()}")
print()

# Test 1: Baseline (no overrides)
print("=" * 80)
print("TEST 1: BASELINE (No Overrides)")
print("=" * 80)
engine_baseline = BacktestEngine(use_options=True, param_overrides={})
result_baseline = engine_baseline.run_backtest(start_date=start_date, end_date=end_date)

if result_baseline and 'trades' in result_baseline:
    trades_baseline = result_baseline['trades']
    if len(trades_baseline) > 0:
        baseline_count = len(trades_baseline)
        baseline_wr = result_baseline['win_rate']
        baseline_pnl = result_baseline['total_pnl']
        print(f"✅ Baseline: {baseline_count} trades, {baseline_wr:.1%} WR, ${baseline_pnl:.2f} P/L")
    else:
        print("❌ Baseline: No trades")
        sys.exit(1)
else:
    print("❌ Baseline: Failed to run")
    sys.exit(1)

print()

# Test 2: Different VIX threshold
print("=" * 80)
print("TEST 2: VIX THRESHOLD = 15 (Lower)")
print("=" * 80)
engine_vix15 = BacktestEngine(use_options=True, param_overrides={'vix_threshold': 15})
result_vix15 = engine_vix15.run_backtest(start_date=start_date, end_date=end_date)

if result_vix15 and 'trades' in result_vix15 and len(result_vix15['trades']) > 0:
    vix15_count = result_vix15['num_trades']
    vix15_wr = result_vix15['win_rate']
    vix15_pnl = result_vix15['total_pnl']
    print(f"✅ VIX=15: {vix15_count} trades, {vix15_wr:.1%} WR, ${vix15_pnl:.2f} P/L")
    
    if vix15_count > baseline_count:
        print(f"✅ PASS: More trades with lower VIX threshold ({vix15_count} vs {baseline_count})")
    else:
        print(f"⚠️  WARNING: Expected more trades, got {vix15_count} vs {baseline_count}")
else:
    print("❌ VIX=15: No trades")

print()

# Test 3: Disable opening range filter
print("=" * 80)
print("TEST 3: DISABLE OPENING RANGE FILTER")
print("=" * 80)
engine_no_or = BacktestEngine(use_options=True, param_overrides={'use_opening_range': False})
result_no_or = engine_no_or.run_backtest(start_date=start_date, end_date=end_date)

if result_no_or and 'trades' in result_no_or and len(result_no_or['trades']) > 0:
    no_or_count = result_no_or['num_trades']
    no_or_wr = result_no_or['win_rate']
    no_or_pnl = result_no_or['total_pnl']
    print(f"✅ No OR Filter: {no_or_count} trades, {no_or_wr:.1%} WR, ${no_or_pnl:.2f} P/L")
    
    if no_or_count != baseline_count:
        print(f"✅ PASS: Different trade count ({no_or_count} vs {baseline_count})")
    else:
        print(f"⚠️  Note: Same trade count, filter may not be active in this period")
else:
    print("❌ No OR Filter: No trades")

print()

# Test 4: Different death zone
print("=" * 80)
print("TEST 4: NO DEATH ZONE (Disable blocking)")
print("=" * 80)
engine_no_dz = BacktestEngine(use_options=True, param_overrides={
    'death_zone_start': '23:00',  # Set to after market close
    'death_zone_end': '23:30'
})
result_no_dz = engine_no_dz.run_backtest(start_date=start_date, end_date=end_date)

if result_no_dz and 'trades' in result_no_dz and len(result_no_dz['trades']) > 0:
    no_dz_count = result_no_dz['num_trades']
    no_dz_wr = result_no_dz['win_rate']
    no_dz_pnl = result_no_dz['total_pnl']
    print(f"✅ No Death Zone: {no_dz_count} trades, {no_dz_wr:.1%} WR, ${no_dz_pnl:.2f} P/L")
    
    if no_dz_count > baseline_count:
        print(f"✅ PASS: More trades without death zone ({no_dz_count} vs {baseline_count})")
    else:
        print(f"⚠️  WARNING: Expected more trades, got {no_dz_count} vs {baseline_count}")
else:
    print("❌ No Death Zone: No trades")

print()

# Summary
print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)
print(f"Baseline:        {baseline_count} trades")
print(f"VIX=15:          {vix15_count if result_vix15 else 0} trades")
print(f"No OR Filter:    {no_or_count if result_no_or else 0} trades")
print(f"No Death Zone:   {no_dz_count if result_no_dz else 0} trades")
print()

# Check if parameters are actually working
if (vix15_count != baseline_count or no_dz_count != baseline_count):
    print("✅ VALIDATION PASSED: Parameters are affecting results")
    print("✅ System is ready for optimization")
else:
    print("❌ VALIDATION FAILED: Parameters not affecting results")
    print("❌ Check parameter passing logic")
    sys.exit(1)
