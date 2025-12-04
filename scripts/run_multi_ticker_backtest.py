"""
Multi-ticker backtest script.
Runs the v1.6 strategy on SPY, QQQ, and IWM and aggregates results.
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import BacktestEngine
import core.config as config

def run_multi_ticker_backtest(tickers=['SPY', 'QQQ', 'IWM'], days=262):
    """
    Run backtest on multiple tickers and aggregate results.
    
    Args:
        tickers: List of ticker symbols to backtest
        days: Number of trading days to backtest
        
    Returns:
        Dictionary with aggregate and per-ticker results
    """
    print("=" * 80)
    print("MULTI-TICKER BACKTEST")
    print("=" * 80)
    print(f"\nTickers: {', '.join(tickers)}")
    print(f"Period: Last {days} trading days")
    print(f"Strategy: v1.6 (200 EMA Trend Filter)")
    print("\n" + "=" * 80)
    
    all_trades = []
    ticker_results = {}
    
    for ticker in tickers:
        print(f"\n[{ticker}] Running backtest...")
        
        # Temporarily override config.SYMBOL for this ticker
        original_symbol = config.SYMBOL
        config.SYMBOL = ticker
        
        # Create engine
        engine = BacktestEngine(
            tp_pct=config.BACKTEST_TP_PCT,
            sl_pct=config.BACKTEST_SL_PCT,
            position_size=config.BACKTEST_POSITION_SIZE,
            use_options=True
        )
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Run backtest
        try:
            results = engine.run_backtest(
                start_date,
                end_date,
                use_options=True
            )
            
            trades_df = results['trades']
            
            # Add ticker column
            trades_df['ticker'] = ticker
            
            # Store results
            all_trades.append(trades_df)
            ticker_results[ticker] = {
                'trades': results['num_trades'],
                'win_rate': results['win_rate'],
                'net_pnl': results['total_pnl'],
                'profit_factor': abs(results['avg_win'] * results['win_rate'] / (results['avg_loss'] * (100 - results['win_rate']))) if results['avg_loss'] != 0 else 0,
                'avg_win': results['avg_win'],
                'avg_loss': results['avg_loss']
            }
            
            print(f"[{ticker}] ✓ Complete: {results['num_trades']} trades, {results['win_rate']:.1f}% WR, ${results['total_pnl']:.2f} P/L")
            
        except Exception as e:
            print(f"[{ticker}] ✗ Error: {e}")
            ticker_results[ticker] = {
                'trades': 0,
                'win_rate': 0,
                'net_pnl': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        finally:
            # Restore original symbol
            config.SYMBOL = original_symbol
    
    # Combine all trades
    if all_trades:
        combined_trades = pd.concat(all_trades, ignore_index=True)
        combined_trades = combined_trades.sort_values('entry_time')
        
        # Calculate aggregate stats
        total_trades = len(combined_trades)
        wins = combined_trades[combined_trades['pnl'] > 0]
        losses = combined_trades[combined_trades['pnl'] <= 0]
        
        aggregate_stats = {
            'total_trades': total_trades,
            'win_rate': (len(wins) / total_trades * 100) if total_trades > 0 else 0,
            'net_pnl': combined_trades['pnl'].sum(),
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0
        }
    else:
        combined_trades = pd.DataFrame()
        aggregate_stats = {
            'total_trades': 0,
            'win_rate': 0,
            'net_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0
        }
    
    # Print results
    print("\n" + "=" * 80)
    print("MULTI-TICKER BACKTEST RESULTS")
    print("=" * 80)
    print("\n📊 AGGREGATE PERFORMANCE:")
    print(f"  Total Trades: {aggregate_stats['total_trades']}")
    print(f"  Win Rate: {aggregate_stats['win_rate']:.1f}%")
    print(f"  Net P/L: ${aggregate_stats['net_pnl']:.2f}")
    print(f"  Profit Factor: {aggregate_stats['profit_factor']:.2f}")
    print(f"  Avg Win: ${aggregate_stats['avg_win']:.2f}")
    print(f"  Avg Loss: ${aggregate_stats['avg_loss']:.2f}")
    
    print("\n📈 BREAKDOWN BY TICKER:")
    for ticker, results in ticker_results.items():
        print(f"  {ticker}: {results['trades']} trades, {results['win_rate']:.1f}% WR, ${results['net_pnl']:.2f} P/L")
    
    print("\n" + "=" * 80)
    print("✅ MULTI-TICKER BACKTEST COMPLETE")
    print("=" * 80)
    
    # Save combined trades
    if not combined_trades.empty:
        output_file = f"backtest_results/multi_ticker_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        combined_trades.to_csv(output_file, index=False)
        print(f"\n💾 Combined trades saved to: {output_file}")
    
    return {
        'aggregate': aggregate_stats,
        'by_ticker': ticker_results,
        'trades': combined_trades
    }


if __name__ == "__main__":
    results = run_multi_ticker_backtest(tickers=['SPY', 'IWM'], days=262)
