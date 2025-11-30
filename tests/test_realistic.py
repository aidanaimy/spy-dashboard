#!/usr/bin/env python3
"""
Test V3.5 with realistic costs on recent data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.backtest_engine import BacktestEngine
import datetime

# Test on a shorter, more recent period where VIX might be higher
print('Testing V3.5 with realistic costs on recent data (2024-2025)...')
engine = BacktestEngine(use_options=True)
results = engine.run_backtest(datetime.datetime(2024, 1, 1), datetime.datetime(2025, 6, 1), use_options=True, progress_callback=lambda x,y: print(f'{x*100:.0f}% complete') if int(x*10) % 10 == 0 and x*100 % 10 == 0 else None)

print('\nRealistic V3.5 Results (with VIX filter + costs):')
print(f'Trades: {results["num_trades"]}')
print(f'Win Rate: {results["win_rate"]*100:.1f}%')
print(f'Net P/L: ${results["total_pnl"]:.2f}')
print(f'Commissions: ${results.get("total_commissions", 0):.2f}')

if results["num_trades"] > 0:
    profit_factor = results["avg_win"] / abs(results["avg_loss"]) if results["avg_loss"] != 0 else float('inf')
    print(f'Profit Factor: {profit_factor:.2f}')
    print(f'Avg Win: ${results["avg_win"]:.2f}')
    print(f'Avg Loss: ${results["avg_loss"]:.2f}')
else:
    print('Profit Factor: N/A (no trades)')
    print('Avg Win/Loss: N/A (no trades)')
