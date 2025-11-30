#!/usr/bin/env python3
"""
Generate baseline backtest results for comparison.
Creates two static CSVs:
1. baseline_november_2025.csv - November 2025 only
2. baseline_1year.csv - November 2024 to November 2025
"""

import sys
import os
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine

def run_baseline_backtests():
    """Generate baseline backtest CSVs."""
    
    output_dir = os.path.join(os.path.dirname(__file__), 'backtest_results')
    os.makedirs(output_dir, exist_ok=True)
    
    # Test 1: November 2025
    print("=" * 80)
    print("BASELINE 1: NOVEMBER 2025")
    print("=" * 80)
    
    engine = BacktestEngine()
    results_nov = engine.run_backtest(
        start_date=datetime(2025, 11, 1),
        end_date=datetime(2025, 11, 30),
        use_options=True
    )
    
    print(f"\n✅ November 2025: {results_nov['num_trades']} trades, "
          f"{results_nov['win_rate']:.1%} win rate, "
          f"${results_nov['total_pnl']:,.2f} P/L\n")
    
    if len(results_nov['trades']) > 0:
        df_nov = pd.DataFrame(results_nov['trades'])
        nov_path = os.path.join(output_dir, 'baseline_november_2025.csv')
        df_nov.to_csv(nov_path, index=False)
        print(f"💾 Saved to: {nov_path}\n")
    
    # Test 2: 1 Year (Nov 2024 - Nov 2025)
    print("=" * 80)
    print("BASELINE 2: 1 YEAR (NOV 2024 - NOV 2025)")
    print("=" * 80)
    
    engine = BacktestEngine()
    results_1yr = engine.run_backtest(
        start_date=datetime(2024, 11, 1),
        end_date=datetime(2025, 11, 30),
        use_options=True
    )
    
    print(f"\n✅ 1 Year: {results_1yr['num_trades']} trades, "
          f"{results_1yr['win_rate']:.1%} win rate, "
          f"${results_1yr['total_pnl']:,.2f} P/L\n")
    
    if len(results_1yr['trades']) > 0:
        df_1yr = pd.DataFrame(results_1yr['trades'])
        year_path = os.path.join(output_dir, 'baseline_1year.csv')
        df_1yr.to_csv(year_path, index=False)
        print(f"💾 Saved to: {year_path}\n")
    
    print("=" * 80)
    print("✅ BASELINE GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nGenerated files:")
    print(f"  - baseline_november_2025.csv ({results_nov['num_trades']} trades)")
    print(f"  - baseline_1year.csv ({results_1yr['num_trades']} trades)")

if __name__ == "__main__":
    run_baseline_backtests()
