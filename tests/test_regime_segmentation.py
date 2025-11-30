"""
Regime Segmentation - Robustness Test #3

Tests whether the system works across different market regimes or only in specific conditions.

Segments:
1. By VIX level: Low (<15), Mid (15-25), High (>25)
2. By SPY trend: Bull (+10% from low), Bear (-10% from high), Sideways
3. By year: 2023, 2024, 2025

Output: Performance metrics for each regime
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

def run_regime_segmentation(start_date, end_date):
    """
    Segment backtest results by market regime.
    """
    print("="*80)
    print("REGIME SEGMENTATION - ROBUSTNESS TEST #3")
    print("="*80)
    print(f"\nPeriod: {start_date.date()} to {end_date.date()}")
    print("\nThis test determines if the edge works across different market conditions\n")
    
    # Run full backtest first to get all trades
    print("[1/4] Running full backtest to collect trades...")
    engine = BacktestEngine(use_options=True)
    engine.options_tp_pct = 0.80
    engine.options_sl_pct = 0.40
    
    results = engine.run_backtest(
        start_date=start_date,
        end_date=end_date,
        use_options=True
    )
    
    trades_df = pd.DataFrame(results['trades'])
    print(f"✓ Collected {len(trades_df)} trades")
    
    # Load VIX data for regime classification
    print("\n[2/4] Loading VIX data for regime classification...")
    from data.yfinance_client import get_daily_data
    vix_df = get_daily_data('^VIX', days=800)
    spy_df = get_daily_data('SPY', days=800)
    
    # Add date column to trades
    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_time']).dt.date
    
    # Segment 1: By VIX level
    print("\n[3/4] Segmenting by VIX level...")
    vix_regimes = []
    for idx, trade in trades_df.iterrows():
        trade_date = trade['entry_date']
        vix_row = vix_df[vix_df.index.date == trade_date]
        if not vix_row.empty:
            vix_level = vix_row['Close'].values[0]
            if vix_level < 15:
                regime = 'Low VIX (<15)'
            elif vix_level < 25:
                regime = 'Mid VIX (15-25)'
            else:
                regime = 'High VIX (>25)'
            vix_regimes.append(regime)
        else:
            vix_regimes.append('Unknown')
    
    trades_df['vix_regime'] = vix_regimes
    
    # Segment 2: By SPY trend
    print("[3/4] Segmenting by SPY trend...")
    # Calculate 50-day high/low for trend classification
    spy_df['high_50'] = spy_df['Close'].rolling(50).max()
    spy_df['low_50'] = spy_df['Close'].rolling(50).min()
    
    trend_regimes = []
    for idx, trade in trades_df.iterrows():
        trade_date = trade['entry_date']
        spy_row = spy_df[spy_df.index.date == trade_date]
        if not spy_row.empty:
            price = spy_row['Close'].values[0]
            high_50 = spy_row['high_50'].values[0]
            low_50 = spy_row['low_50'].values[0]
            
            # Bull: within 5% of 50-day high
            # Bear: within 5% of 50-day low
            # Sideways: neither
            if price >= high_50 * 0.95:
                regime = 'Bull (near highs)'
            elif price <= low_50 * 1.05:
                regime = 'Bear (near lows)'
            else:
                regime = 'Sideways'
            trend_regimes.append(regime)
        else:
            trend_regimes.append('Unknown')
    
    trades_df['trend_regime'] = trend_regimes
    
    # Segment 3: By year
    trades_df['year'] = pd.to_datetime(trades_df['entry_time']).dt.year
    
    # Analyze each segment
    print("\n[4/4] Analyzing performance by regime...")
    
    def analyze_segment(df, segment_name):
        if len(df) == 0:
            return None
        
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] <= 0]
        
        return {
            'segment': segment_name,
            'trades': len(df),
            'win_rate': len(wins) / len(df) * 100 if len(df) > 0 else 0,
            'total_pnl': df['pnl'].sum(),
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0
        }
    
    # Analyze VIX regimes
    vix_results = []
    for regime in ['Low VIX (<15)', 'Mid VIX (15-25)', 'High VIX (>25)']:
        segment_df = trades_df[trades_df['vix_regime'] == regime]
        result = analyze_segment(segment_df, regime)
        if result:
            vix_results.append(result)
    
    # Analyze trend regimes
    trend_results = []
    for regime in ['Bull (near highs)', 'Sideways', 'Bear (near lows)']:
        segment_df = trades_df[trades_df['trend_regime'] == regime]
        result = analyze_segment(segment_df, regime)
        if result:
            trend_results.append(result)
    
    # Analyze by year
    year_results = []
    for year in sorted(trades_df['year'].unique()):
        segment_df = trades_df[trades_df['year'] == year]
        result = analyze_segment(segment_df, f"Year {year}")
        if result:
            year_results.append(result)
    
    # Print results
    print("\n" + "="*80)
    print("REGIME SEGMENTATION RESULTS")
    print("="*80)
    
    print("\n📊 PERFORMANCE BY VIX LEVEL:")
    vix_df_results = pd.DataFrame(vix_results)
    if not vix_df_results.empty:
        print(vix_df_results[['segment', 'trades', 'win_rate', 'total_pnl', 'profit_factor']].to_string(index=False))
    
    print("\n📊 PERFORMANCE BY TREND:")
    trend_df_results = pd.DataFrame(trend_results)
    if not trend_df_results.empty:
        print(trend_df_results[['segment', 'trades', 'win_rate', 'total_pnl', 'profit_factor']].to_string(index=False))
    
    print("\n📊 PERFORMANCE BY YEAR:")
    year_df_results = pd.DataFrame(year_results)
    if not year_df_results.empty:
        print(year_df_results[['segment', 'trades', 'win_rate', 'total_pnl', 'profit_factor']].to_string(index=False))
    
    # Verdict
    print("\n" + "="*80)
    print("VERDICT")
    print("="*80)
    
    # Check how many regimes are profitable
    vix_profitable = sum([1 for r in vix_results if r['total_pnl'] > 0])
    trend_profitable = sum([1 for r in trend_results if r['total_pnl'] > 0])
    year_profitable = sum([1 for r in year_results if r['total_pnl'] > 0])
    
    total_regimes = len(vix_results) + len(trend_results) + len(year_results)
    total_profitable = vix_profitable + trend_profitable + year_profitable
    
    print(f"\n📊 Profitable regimes: {total_profitable}/{total_regimes} ({total_profitable/total_regimes*100:.1f}%)")
    print(f"   VIX: {vix_profitable}/{len(vix_results)}")
    print(f"   Trend: {trend_profitable}/{len(trend_results)}")
    print(f"   Year: {year_profitable}/{len(year_results)}")
    
    if total_profitable >= total_regimes * 0.75:
        print("\n✅ ROBUST: System works across most market regimes")
        print("   → Edge is NOT regime-dependent")
    elif total_profitable >= total_regimes * 0.5:
        print("\n⚠️  MODERATE: System works in some regimes")
        print("   → Edge has some regime dependency")
    else:
        print("\n❌ REGIME-DEPENDENT: System only works in specific regimes")
        print("   → Edge is highly regime-dependent")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"robustness_tests/regime_segmentation_{timestamp}.csv"
    os.makedirs("robustness_tests", exist_ok=True)
    
    all_results = pd.concat([vix_df_results, trend_df_results, year_df_results], ignore_index=True)
    all_results.to_csv(output_file, index=False)
    
    print(f"\nResults saved to: {output_file}")
    
    return all_results

if __name__ == "__main__":
    # Run on 2-year period for better regime coverage
    end_date = datetime(2025, 11, 28)
    start_date = datetime(2023, 11, 29)
    
    print("\n🚀 Starting Regime Segmentation Test...")
    print(f"   This will take approximately 5 minutes\n")
    
    results = run_regime_segmentation(start_date, end_date)
    
    print("\n✅ Regime segmentation complete!")
    print("\n💡 Next steps:")
    print("   1. Review regime-specific performance")
    print("   2. Identify which regimes work best")
    print("   3. Consider regime-specific parameter tuning")
