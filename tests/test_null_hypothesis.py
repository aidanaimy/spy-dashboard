"""
Null Hypothesis Test - Robustness Test #2

Tests whether signals are actually predictive or if performance comes from TP/SL tuning.

Method:
- Generate RANDOM CALL/PUT signals (50/50) on FAVORABLE days only
- Apply same TP/SL (80/40) as actual system
- Compare performance to actual signals

If random signals ≈ actual signals → TP/SL tuning (NOT predictive)
If actual signals >> random signals → Signals are genuinely predictive
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import BacktestEngine
from logic.regime import analyze_regime
from logic.intraday import analyze_intraday
from logic.signals import generate_signal
from logic.iv import fetch_historical_vix_context
from data.yfinance_client import get_daily_data, get_intraday_data
import config

def run_null_hypothesis_test(start_date, end_date, num_iterations=5):
    """
    Run backtest with random signals and compare to actual signals.
    
    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        num_iterations: Number of random signal runs (for statistical significance)
    """
    print("="*80)
    print("NULL HYPOTHESIS TEST - ROBUSTNESS TEST #2")
    print("="*80)
    print(f"\nPeriod: {start_date.date()} to {end_date.date()}")
    print(f"Iterations: {num_iterations}")
    print("\nThis test determines if signals are predictive or if P/L comes from TP/SL tuning\n")
    
    # First, run actual system for baseline
    print("[1/2] Running ACTUAL system (baseline)...")
    engine_actual = BacktestEngine(use_options=True)
    engine_actual.options_tp_pct = 0.80
    engine_actual.options_sl_pct = 0.40
    
    actual_results = engine_actual.run_backtest(
        start_date=start_date,
        end_date=end_date,
        use_options=True
    )
    
    # Calculate profit factor manually
    trades_df = actual_results['trades']
    if not trades_df.empty:
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        actual_pf = gross_profit / gross_loss if gross_loss != 0 else 0
    else:
        actual_pf = 0

    print(f"✓ Actual System: {actual_results['num_trades']} trades, "
          f"WR={actual_results['win_rate']:.1f}%, "
          f"P/L=${actual_results['total_pnl']:.0f}, "
          f"PF={actual_pf:.2f}")
    
    # Now run random signals multiple times
    print(f"\n[2/2] Running RANDOM signals ({num_iterations} iterations)...")
    random_results = []
    
    for i in range(num_iterations):
        print(f"   Iteration {i+1}/{num_iterations}...", end=" ")
        
        # Set random seed for reproducibility
        random.seed(42 + i)
        np.random.seed(42 + i)
        
        # Run backtest with random signals
        engine_random = BacktestEngine(use_options=True)
        engine_random.options_tp_pct = 0.80
        engine_random.options_sl_pct = 0.40
        
        # Monkey-patch generate_signal in the backtest_engine module
        # This is critical because BacktestEngine imports it directly
        import backtest.backtest_engine
        original_generate_signal = backtest.backtest_engine.generate_signal
        
        def random_signal_generator(regime, intraday_data, **kwargs):
            # Only generate signals on FAVORABLE days (same as actual system)
            if regime.get('0dte_status') != 'FAVORABLE':
                return {'direction': 'NONE', 'confidence': 'LOW', 'reason': 'Not FAVORABLE'}
            
            # Random CALL or PUT with HIGH confidence
            direction = random.choice(['CALL', 'PUT'])
            return {
                'direction': direction,
                'confidence': 'HIGH',
                'reason': 'Random signal (null hypothesis test)'
            }
        
        # Replace signal generator in the engine module
        backtest.backtest_engine.generate_signal = random_signal_generator
        
        try:
            results = engine_random.run_backtest(
                start_date=start_date,
                end_date=end_date,
                use_options=True
            )
            
            random_results.append(results)
            
            # Calculate PF for this run
            r_trades = results['trades']
            if not r_trades.empty:
                r_gp = r_trades[r_trades['pnl'] > 0]['pnl'].sum()
                r_gl = abs(r_trades[r_trades['pnl'] < 0]['pnl'].sum())
                r_pf = r_gp / r_gl if r_gl != 0 else 0
            else:
                r_pf = 0
                
            # Store calculated PF in results dict for later use
            results['profit_factor'] = r_pf
            
            print(f"✓ {results['num_trades']} trades, "
                  f"WR={results['win_rate']:.1f}%, "
                  f"P/L=${results['total_pnl']:.0f}, "
                  f"PF={r_pf:.2f}")
        
        finally:
            # Restore original signal generator
            backtest.backtest_engine.generate_signal = original_generate_signal
    
    # Calculate statistics for random signals
    random_pnls = [r['total_pnl'] for r in random_results]
    random_wrs = [r['win_rate'] for r in random_results]
    random_pfs = [r['profit_factor'] for r in random_results]
    random_trades = [r['num_trades'] for r in random_results]
    
    avg_random_pnl = np.mean(random_pnls)
    std_random_pnl = np.std(random_pnls)
    avg_random_wr = np.mean(random_wrs)
    avg_random_pf = np.mean(random_pfs)
    avg_random_trades = np.mean(random_trades)
    
    # Print comparison
    print("\n" + "="*80)
    print("COMPARISON: ACTUAL vs RANDOM SIGNALS")
    print("="*80)
    
    print(f"\n📊 ACTUAL SYSTEM:")
    print(f"   Trades: {actual_results['num_trades']}")
    print(f"   Win Rate: {actual_results['win_rate']:.1f}%")
    print(f"   Total P/L: ${actual_results['total_pnl']:.2f}")
    print(f"   Profit Factor: {actual_pf:.2f}")
    print(f"   Avg R-Multiple: {actual_results['avg_r_multiple']:.2f}")
    
    print(f"\n📊 RANDOM SIGNALS (avg of {num_iterations} runs):")
    print(f"   Trades: {avg_random_trades:.0f}")
    print(f"   Win Rate: {avg_random_wr:.1f}%")
    print(f"   Total P/L: ${avg_random_pnl:.2f} (±${std_random_pnl:.2f})")
    print(f"   Profit Factor: {avg_random_pf:.2f}")
    
    # Calculate improvement
    pnl_improvement = ((actual_results['total_pnl'] - avg_random_pnl) / abs(avg_random_pnl) * 100) if avg_random_pnl != 0 else 0
    wr_improvement = actual_results['win_rate'] - avg_random_wr
    pf_improvement = actual_pf - avg_random_pf
    
    print(f"\n📈 IMPROVEMENT (Actual vs Random):")
    print(f"   P/L: {pnl_improvement:+.1f}%")
    print(f"   Win Rate: {wr_improvement:+.1f} percentage points")
    print(f"   Profit Factor: {pf_improvement:+.2f}")
    
    # Statistical significance (simple z-test)
    if std_random_pnl > 0:
        z_score = (actual_results['total_pnl'] - avg_random_pnl) / std_random_pnl
        print(f"\n📊 Statistical Significance:")
        print(f"   Z-score: {z_score:.2f}")
        if abs(z_score) > 2:
            print(f"   ✓ Statistically significant (p < 0.05)")
        else:
            print(f"   ✗ NOT statistically significant")
    
    # Verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)
    
    if actual_results['total_pnl'] > avg_random_pnl * 1.5:
        print("\n✅ PREDICTIVE: Actual signals >> random signals")
        print("   → Signals are genuinely predictive of direction")
        print("   → Edge is NOT just TP/SL tuning")
    elif actual_results['total_pnl'] > avg_random_pnl * 1.2:
        print("\n⚠️  MODERATE: Actual signals > random signals")
        print("   → Signals have some predictive power")
        print("   → But TP/SL tuning may contribute significantly")
    else:
        print("\n❌ NOT PREDICTIVE: Actual signals ≈ random signals")
        print("   → Signals are NOT predictive")
        print("   → Performance comes from TP/SL tuning, not signal quality")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"robustness_tests/null_hypothesis_results_{timestamp}.txt"
    os.makedirs("robustness_tests", exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write("NULL HYPOTHESIS TEST RESULTS\n")
        f.write("="*80 + "\n\n")
        f.write(f"Period: {start_date.date()} to {end_date.date()}\n")
        f.write(f"Iterations: {num_iterations}\n\n")
        f.write(f"ACTUAL SYSTEM:\n")
        f.write(f"  Trades: {actual_results['num_trades']}\n")
        f.write(f"  Win Rate: {actual_results['win_rate']:.1f}%\n")
        f.write(f"  Total P/L: ${actual_results['total_pnl']:.2f}\n")
        f.write(f"  Profit Factor: {actual_pf:.2f}\n\n")
        f.write(f"RANDOM SIGNALS (avg):\n")
        f.write(f"  Trades: {avg_random_trades:.0f}\n")
        f.write(f"  Win Rate: {avg_random_wr:.1f}%\n")
        f.write(f"  Total P/L: ${avg_random_pnl:.2f} (±${std_random_pnl:.2f})\n")
        f.write(f"  Profit Factor: {avg_random_pf:.2f}\n\n")
        f.write(f"IMPROVEMENT:\n")
        f.write(f"  P/L: {pnl_improvement:+.1f}%\n")
        f.write(f"  Win Rate: {wr_improvement:+.1f} pp\n")
        f.write(f"  Profit Factor: {pf_improvement:+.2f}\n")
    
    print(f"\nResults saved to: {output_file}")
    
    return {
        'actual': actual_results,
        'random_avg': {
            'total_pnl': avg_random_pnl,
            'win_rate': avg_random_wr,
            'profit_factor': avg_random_pf,
            'num_trades': avg_random_trades
        },
        'improvement_pct': pnl_improvement
    }

if __name__ == "__main__":
    # Run on 1-year period
    end_date = datetime(2025, 11, 28)
    start_date = end_date - timedelta(days=365)
    
    print("\n🚀 Starting Null Hypothesis Test...")
    print(f"   This will take approximately 5-10 minutes\n")
    
    results = run_null_hypothesis_test(start_date, end_date, num_iterations=5)
    
    print("\n✅ Null hypothesis test complete!")
    print("\n💡 Next steps:")
    print("   1. Review the comparison results")
    print("   2. If signals are predictive, proceed to regime segmentation")
    print("   3. If signals are NOT predictive, investigate signal logic")
