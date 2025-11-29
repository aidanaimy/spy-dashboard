#!/usr/bin/env python3
"""
Standalone backtest script for SPY 0DTE options trading system.
Runs the maximum available historical period and saves detailed results.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
import config

def run_full_backtest():
    """Run backtest over maximum available period."""
    
    print("=" * 80)
    print("SPY 0DTE OPTIONS BACKTEST - 2 YEAR HISTORICAL PERIOD")
    print("=" * 80)
    print()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years
    
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
        print(f"  Avg Win: ${results['avg_win']:.2f}")
        print(f"  Avg Loss: ${results['avg_loss']:.2f}")
        print()
        
        # Detailed Analysis
        trades_df = results.get('trades')
        if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
            print("🕵️ DETAILED ANALYSIS:")
            
            # Win/Loss Streaks
            wins = trades_df['pnl'] > 0
            current_streak = 0
            max_win_streak = 0
            max_loss_streak = 0
            
            for win in wins:
                if win:
                    if current_streak > 0:
                        current_streak += 1
                    else:
                        current_streak = 1
                    max_win_streak = max(max_win_streak, current_streak)
                else:
                    if current_streak < 0:
                        current_streak -= 1
                    else:
                        current_streak = -1
                    max_loss_streak = min(max_loss_streak, current_streak)
            
            print(f"  Max Win Streak: {max_win_streak}")
            print(f"  Max Loss Streak: {abs(max_loss_streak)}")
            
            # Best/Worst Days
            trades_df['date'] = pd.to_datetime(trades_df['entry_time']).dt.date
            daily_pnl = trades_df.groupby('date')['pnl'].sum()
            best_day = daily_pnl.idxmax()
            worst_day = daily_pnl.idxmin()
            
            print(f"  Best Day: {best_day} (${daily_pnl.max():.2f})")
            print(f"  Worst Day: {worst_day} (${daily_pnl.min():.2f})")
            print()

        # Time-of-day analysis
        if 'time_analysis' in results and results['time_analysis']:
            print("⏰ PERFORMANCE BY TIME OF DAY:")
            for period, stats in results['time_analysis'].items():
                if isinstance(stats, dict) and 'count' in stats:
                    print(f"  {period}:")
                    print(f"    Trades: {stats['count']}")
                    if stats['count'] > 0:
                        print(f"    Win Rate: {stats.get('win_rate', 0):.1%}")
                        print(f"    Avg R: {stats.get('avg_r_multiple', 0):.2f}")
                        print(f"    P/L: ${stats.get('total_pnl', 0):,.2f}")
            print()
        
        # Debug info
        if 'debug_info' in results:
            debug = results['debug_info']
            print("🔍 DEBUG INFO:")
            print(f"  Days Processed: {debug.get('days_processed', 0)}")
            print(f"  Days Skipped: {debug.get('days_skipped', 0)}")
            print(f"  Signals Generated: {debug.get('signals_generated', 0)}")
            print()
        
        # Save detailed results
        if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
            # Create results directory if it doesn't exist
            results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backtest_results')
            os.makedirs(results_dir, exist_ok=True)
            
            output_file = os.path.join(results_dir, f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            trades_df.to_csv(output_file, index=False)
            print(f"💾 Detailed results saved to: {output_file}")
            print()
            
            # Show sample trades
            print("📋 SAMPLE TRADES (First 10):")
            display_cols = ['entry_time', 'direction', 'confidence', '0dte_permission', 
                          'entry_price', 'exit_price', 'pnl', 'exit_reason']
            available_cols = [col for col in display_cols if col in trades_df.columns]
            
            sample_df = trades_df[available_cols].head(10).copy()
            sample_df['entry_time'] = pd.to_datetime(sample_df['entry_time']).dt.strftime('%m/%d %H:%M')
            if 'exit_time' in trades_df.columns:
                sample_df['exit_time'] = pd.to_datetime(trades_df['exit_time']).dt.strftime('%m/%d %H:%M')
            
            print(sample_df.to_string(index=False))
            print()
            
            # Win/Loss breakdown
            wins = trades_df[trades_df['pnl'] > 0]
            losses = trades_df[trades_df['pnl'] <= 0]
            
            print("💰 WIN/LOSS BREAKDOWN:")
            print(f"  Wins: {len(wins)} trades, Avg: ${wins['pnl'].mean():.2f}, Total: ${wins['pnl'].sum():.2f}")
            print(f"  Losses: {len(losses)} trades, Avg: ${losses['pnl'].mean():.2f}, Total: ${losses['pnl'].sum():.2f}")
            print(f"  Profit Factor: {wins['pnl'].sum() / abs(losses['pnl'].sum()):.2f}" if len(losses) > 0 else "  Profit Factor: ∞")
            print()
        
        print("=" * 80)
        print("✅ BACKTEST COMPLETE")
        print("=" * 80)
        
        return results
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ BACKTEST FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print()
    print("Starting backtest...")
    print()
    
    results = run_full_backtest()
    
    if results:
        print()
        print("🎯 To run again with different dates, edit the script and modify:")
        print("   start_date = end_date - timedelta(days=60)")
        print()
        sys.exit(0)
    else:
        print()
        print("⚠️ Backtest failed. Check error messages above.")
        print()
        sys.exit(1)

