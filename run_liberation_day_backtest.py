#!/usr/bin/env python3
"""
Liberation Day Backtest - April 2025
Tests system performance during the April 2025 market drawdown.
"""

import sys
import os
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
import config

def run_liberation_day_backtest():
    """Run backtest for Liberation Day period (April 2025)."""
    
    print("=" * 80)
    print("LIBERATION DAY BACKTEST - APRIL 2025")
    print("Testing System Performance During Market Drawdown")
    print("=" * 80)
    print()
    
    # April 2025 date range
    start_date = datetime(2025, 4, 1)
    end_date = datetime(2025, 4, 30)
    
    print(f"📅 Backtest Period: {start_date.date()} to {end_date.date()}")
    print(f"📊 Mode: Options (Black-Scholes)")
    print(f"🎯 Filters: HIGH confidence + FAVORABLE days only")
    print(f"⚙️  TP/SL: {config.BACKTEST_OPTIONS_TP_PCT*100:.0f}% / {config.BACKTEST_OPTIONS_SL_PCT*100:.0f}%")
    print(f"⏱️  Cooldown: {config.BACKTEST_REENTRY_COOLDOWN_MINUTES} minutes after stop loss")
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
        print("LIBERATION DAY BACKTEST RESULTS")
        print("=" * 80)
        print()
        
        # Summary metrics
        print("📊 PERFORMANCE SUMMARY (NET OF ALL COSTS):")
        print(f"  Total Trades: {results['num_trades']}")
        print(f"  Win Rate: {results['win_rate']:.1%}")
        print(f"  Avg R-Multiple: {results['avg_r_multiple']:.2f}")
        print(f"  Max Drawdown: {results['max_drawdown']:.1%}")
        print(f"  Net P/L: ${results['total_pnl']:,.2f}")
        
        # Handle case of no trades
        if results['num_trades'] > 0:
            print(f"  Avg Win: ${results['avg_win']:.2f}")
            print(f"  Avg Loss: ${results['avg_loss']:.2f}")
            print(f"  Win/Loss Ratio: {abs(results['avg_win'] / results['avg_loss']):.2f}:1" if results['avg_loss'] != 0 else "  Win/Loss Ratio: ∞")
        else:
            print("  Avg Win: $0.00 (no trades)")
            print("  Avg Loss: $0.00 (no trades)")
        
        print(f"  Commissions Paid: ${results.get('total_commissions', 0):,.2f}")
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
            
            if len(daily_pnl) > 0:
                best_day = daily_pnl.idxmax()
                worst_day = daily_pnl.idxmin()
                print(f"  Best Day: {best_day} (${daily_pnl.max():.2f})")
                print(f"  Worst Day: {worst_day} (${daily_pnl.min():.2f})")
            
            # Trading days
            trading_days = len(daily_pnl)
            print(f"  Trading Days: {trading_days}")
            print(f"  Avg Trades/Day: {results['num_trades'] / trading_days:.1f}" if trading_days > 0 else "  Avg Trades/Day: 0.0")
            print()
            
            # Direction breakdown
            call_trades = trades_df[trades_df['direction'] == 'CALL']
            put_trades = trades_df[trades_df['direction'] == 'PUT']
            
            print("📈 DIRECTION BREAKDOWN:")
            if len(call_trades) > 0:
                call_wins = len(call_trades[call_trades['pnl'] > 0])
                print(f"  CALL: {len(call_trades)} trades, {call_wins/len(call_trades):.1%} WR, ${call_trades['pnl'].sum():.2f} P/L")
            else:
                print("  CALL: 0 trades")
            
            if len(put_trades) > 0:
                put_wins = len(put_trades[put_trades['pnl'] > 0])
                print(f"  PUT: {len(put_trades)} trades, {put_wins/len(put_trades):.1%} WR, ${put_trades['pnl'].sum():.2f} P/L")
            else:
                print("  PUT: 0 trades")
            print()
        
        # Debug info
        if 'debug_info' in results:
            debug = results['debug_info']
            print("🔍 DEBUG INFO:")
            print(f"  Days Processed: {debug.get('days_processed', 0)}")
            print(f"  Days Skipped: {debug.get('days_skipped', 0)}")
            print(f"  Signals Generated: {debug.get('signals_generated', 0)}")
            print()
        
        # Save results to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_results")
        os.makedirs(results_dir, exist_ok=True)
        
        # Save as baseline CSV
        baseline_file = os.path.join(results_dir, "baseline_liberation_day_april2025.csv")
        if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
            trades_df.to_csv(baseline_file, index=False)
            print(f"💾 Baseline saved to: {baseline_file}")
            
            # Also save timestamped version
            timestamped_file = os.path.join(results_dir, f"liberation_day_april2025_{timestamp}.csv")
            trades_df.to_csv(timestamped_file, index=False)
            print(f"💾 Timestamped copy saved to: {timestamped_file}")
            print()
            
            # Show sample trades
            print("📋 SAMPLE TRADES (First 10):")
            display_cols = ['entry_time', 'direction', 'confidence', '0dte_permission', 
                          'entry_price', 'exit_price', 'pnl', 'exit_reason']
            available_cols = [col for col in display_cols if col in trades_df.columns]
            
            sample_df = trades_df[available_cols].head(10).copy()
            sample_df['entry_time'] = pd.to_datetime(sample_df['entry_time']).dt.strftime('%m/%d %H:%M')
            
            print(sample_df.to_string(index=False))
            print()
            
            # Win/Loss breakdown
            wins = trades_df[trades_df['pnl'] > 0]
            losses = trades_df[trades_df['pnl'] <= 0]
            
            print("💰 WIN/LOSS BREAKDOWN:")
            print(f"  Wins: {len(wins)} trades, Avg: ${wins['pnl'].mean():.2f}, Total: ${wins['pnl'].sum():.2f}")
            print(f"  Losses: {len(losses)} trades, Avg: ${losses['pnl'].mean():.2f}, Total: ${losses['pnl'].sum():.2f}")
            if len(losses) > 0 and losses['pnl'].sum() != 0:
                print(f"  Profit Factor: {wins['pnl'].sum() / abs(losses['pnl'].sum()):.2f}")
            else:
                print("  Profit Factor: ∞")
            print()
        else:
            print("⚠️  No trades executed during this period.")
            print()
        
        print("=" * 80)
        print("✅ LIBERATION DAY BACKTEST COMPLETE")
        print("=" * 80)
        print()
        print("📝 Next Steps:")
        print("  1. Review the results above")
        print("  2. Update GROUND_TRUTH_BASELINES.md with Liberation Day metrics")
        print("  3. Compare performance vs normal market conditions")
        print()
        
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
    print("Starting Liberation Day backtest...")
    print()
    
    results = run_liberation_day_backtest()
    
    if results:
        sys.exit(0)
    else:
        print()
        print("⚠️ Backtest failed. Check error messages above.")
        print()
        sys.exit(1)
