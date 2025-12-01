#!/usr/bin/env python3
"""
Backtest for November 2024 only - to compare with dashboard results.
"""

import sys
import os
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
import config

def run_november_backtest():
    """Run backtest for November 2024 only."""
    
    print("=" * 80)
    print("SPY 0DTE OPTIONS BACKTEST - NOVEMBER 2025")
    print("=" * 80)
    print()
    
    # November 2025 date range
    start_date = datetime(2025, 11, 1)
    end_date = datetime(2025, 11, 30)
    
    print(f"📅 Backtest Period: {start_date.date()} to {end_date.date()}")
    print(f"📊 Mode: Options (Black-Scholes)")
    print(f"🎯 Filters: HIGH confidence + FAVORABLE days only")
    print(f"⏱️  Cooldown: 30 minutes after stop loss")
    print()
    
    # Initialize engine
    print("🚀 Initializing backtest engine...")
    engine = BacktestEngine()
    
    # Progress callback
    def progress_callback(progress, message):
        print(f"[{progress*100:.0f}%] {message}")
    
    # Run backtest
    print("🔄 Running backtest...")
    print()
    
    try:
        results = engine.run_backtest(
            start_date=start_date,
            end_date=end_date,
            use_options=True,
            progress_callback=progress_callback
        )
        
        print()
        print("=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)
        print()
        
        # Summary metrics
        print("📊 PERFORMANCE SUMMARY:")
        print(f"  Total Trades: {results['num_trades']}")
        print(f"  Win Rate: {results['win_rate']:.1%}")
        print(f"  Avg R-Multiple: {results['avg_r_multiple']:.2f}")
        print(f"  Max Drawdown: {results['max_drawdown']:.1%}")
        print(f"  Total P/L: ${results['total_pnl']:,.2f}")
        
        if results['num_trades'] > 0:
            print(f"  Avg Win: ${results['avg_win']:.2f}")
            print(f"  Avg Loss: ${results['avg_loss']:.2f}")
        
        print()
        
        # Save results
        output_dir = os.path.join(os.path.dirname(__file__), 'backtest_results')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(output_dir, f'november_2025_{timestamp}.csv')
        
        if results['trades']:
            trades_df = pd.DataFrame(results['trades'])
            trades_df.to_csv(csv_path, index=False)
            print(f"💾 Results saved to: {csv_path}")
        
        print()
        print("=" * 80)
        print("✅ BACKTEST COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error running backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(run_november_backtest())
