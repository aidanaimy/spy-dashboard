"""
TP/SL Grid Search - Robustness Test #1

Tests whether the 80% TP / 40% SL is optimal or if a range of values work.
This is CRITICAL to determine if the edge is curve-fitted or robust.

Tests:
- TP: 60%, 70%, 80%, 90%, 100%
- SL: 30%, 35%, 40%, 45%, 50%
- Total: 25 combinations

Output: CSV with all results + heatmap visualization
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import BacktestEngine
import config

def run_tpsl_grid_search(start_date, end_date):
    """
    Run backtest across grid of TP/SL combinations.
    """
    # Define grid
    tp_values = [0.60, 0.70, 0.80, 0.90, 1.00]
    sl_values = [0.30, 0.35, 0.40, 0.45, 0.50]
    
    results = []
    total_tests = len(tp_values) * len(sl_values)
    test_num = 0
    
    print("="*80)
    print("TP/SL GRID SEARCH - ROBUSTNESS TEST #1")
    print("="*80)
    print(f"\nPeriod: {start_date.date()} to {end_date.date()}")
    print(f"Total combinations: {total_tests}")
    print("\nStarting grid search...\n")
    
    for tp in tp_values:
        for sl in sl_values:
            test_num += 1
            print(f"[{test_num}/{total_tests}] Testing TP={tp*100:.0f}% / SL={sl*100:.0f}%...", end=" ")
            
            try:
                # CRITICAL: Temporarily modify config values BEFORE creating engine
                # because run_backtest() overwrites instance variables with config values
                original_tp = config.BACKTEST_OPTIONS_TP_PCT
                original_sl = config.BACKTEST_OPTIONS_SL_PCT
                
                config.BACKTEST_OPTIONS_TP_PCT = tp
                config.BACKTEST_OPTIONS_SL_PCT = sl
                
                print(f"DEBUG: Set config TP={config.BACKTEST_OPTIONS_TP_PCT}, SL={config.BACKTEST_OPTIONS_SL_PCT}", end=" ")
                
                # Create engine (will use modified config values)
                engine = BacktestEngine(
                    tp_pct=config.BACKTEST_TP_PCT,
                    sl_pct=config.BACKTEST_SL_PCT,
                    position_size=config.BACKTEST_POSITION_SIZE,
                    use_options=True
                )
                
                print(f"Engine TP={engine.options_tp_pct}, SL={engine.options_sl_pct}", end=" ")
                
                # Run backtest
                backtest_results = engine.run_backtest(
                    start_date=start_date,
                    end_date=end_date,
                    use_options=True
                )
                
                print(f"After run TP={engine.options_tp_pct}, SL={engine.options_sl_pct}...", end=" ")
                
                # Restore original config values
                config.BACKTEST_OPTIONS_TP_PCT = original_tp
                config.BACKTEST_OPTIONS_SL_PCT = original_sl
                
                # Extract metrics
                num_trades = backtest_results['num_trades']
                win_rate = backtest_results['win_rate']
                total_pnl = backtest_results['total_pnl']
                max_dd = backtest_results['max_drawdown']
                avg_win = backtest_results['avg_win']
                avg_loss = backtest_results['avg_loss']
                avg_loss = backtest_results['avg_loss']
                
                # Calculate profit factor manually
                trades_df = backtest_results['trades']
                if not trades_df.empty:
                    gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
                    gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
                    profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0
                else:
                    profit_factor = 0
                    
                avg_r = backtest_results['avg_r_multiple']
                
                results.append({
                    'TP': tp,
                    'SL': sl,
                    'TP_pct': f"{tp*100:.0f}%",
                    'SL_pct': f"{sl*100:.0f}%",
                    'Total_Trades': num_trades,
                    'Win_Rate': win_rate,
                    'Total_PnL': total_pnl,
                    'Max_DD': max_dd,
                    'Avg_Win': avg_win,
                    'Avg_Loss': avg_loss,
                    'Profit_Factor': profit_factor,
                    'Avg_R': avg_r,
                    'PnL_per_Trade': total_pnl / num_trades if num_trades > 0 else 0
                })
                
                print(f"✓ Trades={num_trades}, WR={win_rate:.1f}%, P/L=${total_pnl:.0f}, PF={profit_factor:.2f}")
                
            except Exception as e:
                print(f"✗ ERROR: {str(e)}")
                results.append({
                    'TP': tp,
                    'SL': sl,
                    'TP_pct': f"{tp*100:.0f}%",
                    'SL_pct': f"{sl*100:.0f}%",
                    'Total_Trades': 0,
                    'Win_Rate': 0,
                    'Total_PnL': 0,
                    'Max_DD': 0,
                    'Avg_Win': 0,
                    'Avg_Loss': 0,
                    'Profit_Factor': 0,
                    'Avg_R': 0,
                    'PnL_per_Trade': 0
                })
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"robustness_tests/tpsl_grid_results_{timestamp}.csv"
    os.makedirs("robustness_tests", exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print("\n" + "="*80)
    print("GRID SEARCH COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_file}")
    
    # Print summary
    print("\n📊 TOP 5 COMBINATIONS BY TOTAL P/L:")
    top5 = df.nlargest(5, 'Total_PnL')[['TP_pct', 'SL_pct', 'Total_Trades', 'Win_Rate', 'Total_PnL', 'Profit_Factor']]
    print(top5.to_string(index=False))
    
    print("\n📊 TOP 5 COMBINATIONS BY PROFIT FACTOR:")
    top5_pf = df.nlargest(5, 'Profit_Factor')[['TP_pct', 'SL_pct', 'Total_Trades', 'Win_Rate', 'Total_PnL', 'Profit_Factor']]
    print(top5_pf.to_string(index=False))
    
    print("\n📊 TOP 5 COMBINATIONS BY WIN RATE:")
    top5_wr = df.nlargest(5, 'Win_Rate')[['TP_pct', 'SL_pct', 'Total_Trades', 'Win_Rate', 'Total_PnL', 'Profit_Factor']]
    print(top5_wr.to_string(index=False))
    
    # Analyze robustness
    print("\n" + "="*80)
    print("ROBUSTNESS ANALYSIS")
    print("="*80)
    
    profitable_combos = df[df['Total_PnL'] > 0]
    print(f"\n✓ Profitable combinations: {len(profitable_combos)}/{len(df)} ({len(profitable_combos)/len(df)*100:.1f}%)")
    
    # Check if 80/40 is in top 5
    baseline = df[(df['TP'] == 0.80) & (df['SL'] == 0.40)]
    if not baseline.empty:
        baseline_pnl = baseline['Total_PnL'].values[0]
        baseline_rank = (df['Total_PnL'] > baseline_pnl).sum() + 1
        print(f"\n📍 Baseline (80% TP / 40% SL):")
        print(f"   Rank: #{baseline_rank}/25")
        print(f"   P/L: ${baseline_pnl:.2f}")
        print(f"   Win Rate: {baseline['Win_Rate'].values[0]:.1f}%")
        print(f"   Profit Factor: {baseline['Profit_Factor'].values[0]:.2f}")
    
    # Check if multiple TP values work
    tp_groups = df.groupby('TP')['Total_PnL'].agg(['mean', 'std', 'count'])
    print(f"\n📊 Performance by TP level:")
    print(tp_groups)
    
    # Check if multiple SL values work
    sl_groups = df.groupby('SL')['Total_PnL'].agg(['mean', 'std', 'count'])
    print(f"\n📊 Performance by SL level:")
    print(sl_groups)
    
    # Verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)
    
    if len(profitable_combos) >= 15:  # 60%+ profitable
        print("\n✅ ROBUST: Multiple TP/SL combinations are profitable")
        print("   → Edge is NOT curve-fitted to 80/40")
    elif len(profitable_combos) >= 10:  # 40-60% profitable
        print("\n⚠️  MODERATE: Some TP/SL combinations work")
        print("   → Edge has some robustness but may be sensitive to TP/SL")
    else:
        print("\n❌ FRAGILE: Only a few TP/SL combinations are profitable")
        print("   → Edge is likely curve-fitted to specific TP/SL values")
    
    return df

if __name__ == "__main__":
    # Run on 1-year period (same as original backtest)
    end_date = datetime(2025, 11, 28)
    start_date = end_date - timedelta(days=365)
    
    print("\n🚀 Starting TP/SL Grid Search...")
    print(f"   This will take approximately 10-15 minutes for 25 combinations\n")
    
    results_df = run_tpsl_grid_search(start_date, end_date)
    
    print("\n✅ Grid search complete!")
    print("\n💡 Next steps:")
    print("   1. Review the results CSV")
    print("   2. Check if multiple combinations are profitable")
    print("   3. Proceed to Null Hypothesis Test (random signals)")
