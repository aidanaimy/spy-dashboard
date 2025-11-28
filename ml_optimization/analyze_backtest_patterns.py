#!/usr/bin/env python3
"""
Analyze backtest results to find patterns in wins vs losses.
Identifies which conditions lead to better outcomes.
"""

import pandas as pd
import numpy as np
from datetime import datetime

def analyze_patterns(csv_file):
    """Analyze backtest CSV for win/loss patterns."""
    
    print("=" * 80)
    print("BACKTEST PATTERN ANALYSIS")
    print("=" * 80)
    print()
    
    # Load data
    df = pd.read_csv(csv_file)
    
    # Add win/loss column
    df['win'] = df['pnl'] > 0
    
    # Parse datetimes with UTC handling
    df['entry_time'] = pd.to_datetime(df['entry_time'], utc=True)
    df['exit_time'] = pd.to_datetime(df['exit_time'], utc=True)
    
    # Calculate trade duration
    duration_diff = df['exit_time'] - df['entry_time']
    df['duration_minutes'] = duration_diff.dt.total_seconds() / 60
    
    # Extract features
    df['entry_hour'] = df['entry_time'].dt.hour
    df['entry_minute'] = df['entry_time'].dt.minute
    df['time_bucket'] = pd.cut(
        df['entry_hour'] * 60 + df['entry_minute'],
        bins=[0, 595, 630, 705, 810, 855, 870, 1440],
        labels=['Pre-9:55', '9:55-10:30', '10:30-11:45', '11:45-1:30', '1:30-2:15', '2:15-2:30', 'After 2:30']
    )
    
    # Overall stats
    print("📊 OVERALL STATISTICS:")
    print(f"  Total Trades: {len(df)}")
    print(f"  Wins: {df['win'].sum()} ({df['win'].mean():.1%})")
    print(f"  Losses: {(~df['win']).sum()} ({(~df['win']).mean():.1%})")
    print(f"  Avg Win: ${df[df['win']]['pnl'].mean():.2f}")
    print(f"  Avg Loss: ${df[~df['win']]['pnl'].mean():.2f}")
    print(f"  Avg Duration: {df['duration_minutes'].mean():.1f} minutes")
    print()
    
    # Win rate by time of day
    print("⏰ WIN RATE BY TIME OF DAY:")
    time_analysis = df.groupby('time_bucket').agg({
        'win': ['count', 'sum', 'mean'],
        'pnl': 'sum'
    }).round(3)
    
    for time_period in time_analysis.index:
        count = time_analysis.loc[time_period, ('win', 'count')]
        wins = time_analysis.loc[time_period, ('win', 'sum')]
        wr = time_analysis.loc[time_period, ('win', 'mean')]
        pnl = time_analysis.loc[time_period, ('pnl', 'sum')]
        if count > 0:
            print(f"  {time_period:20s}: {int(count):3d} trades, {int(wins):3d} wins ({wr:5.1%}), P/L: ${pnl:+8.2f}")
    print()
    
    # Win rate by direction
    print("📈 WIN RATE BY DIRECTION:")
    for direction in df['direction'].unique():
        dir_df = df[df['direction'] == direction]
        wr = dir_df['win'].mean()
        print(f"  {direction:5s}: {len(dir_df):3d} trades, {wr:5.1%} win rate, P/L: ${dir_df['pnl'].sum():+8.2f}")
    print()
    
    # Win rate by 0DTE permission
    if '0dte_permission' in df.columns:
        print("🎯 WIN RATE BY 0DTE PERMISSION:")
        for perm in df['0dte_permission'].unique():
            if pd.notna(perm):
                perm_df = df[df['0dte_permission'] == perm]
                wr = perm_df['win'].mean()
                print(f"  {perm:10s}: {len(perm_df):3d} trades, {wr:5.1%} win rate, P/L: ${perm_df['pnl'].sum():+8.2f}")
        print()
    
    # Win rate by confidence
    if 'confidence' in df.columns:
        print("💪 WIN RATE BY CONFIDENCE:")
        for conf in df['confidence'].unique():
            if pd.notna(conf):
                conf_df = df[df['confidence'] == conf]
                wr = conf_df['win'].mean()
                print(f"  {conf:6s}: {len(conf_df):3d} trades, {wr:5.1%} win rate, P/L: ${conf_df['pnl'].sum():+8.2f}")
        print()
    
    # Duration analysis
    print("⏱️  TRADE DURATION ANALYSIS:")
    print(f"  Avg Win Duration: {df[df['win']]['duration_minutes'].mean():.1f} minutes")
    print(f"  Avg Loss Duration: {df[~df['win']]['duration_minutes'].mean():.1f} minutes")
    
    # Duration buckets
    df['duration_bucket'] = pd.cut(
        df['duration_minutes'],
        bins=[0, 10, 30, 60, 120, 300],
        labels=['<10m', '10-30m', '30-60m', '1-2h', '>2h']
    )
    
    print()
    print("  Win Rate by Duration:")
    for bucket in df['duration_bucket'].cat.categories:
        bucket_df = df[df['duration_bucket'] == bucket]
        if len(bucket_df) > 0:
            wr = bucket_df['win'].mean()
            print(f"    {bucket:8s}: {len(bucket_df):3d} trades, {wr:5.1%} win rate")
    print()
    
    # Exit reason analysis
    print("🚪 EXIT REASON ANALYSIS:")
    for reason in df['exit_reason'].unique():
        reason_df = df[df['exit_reason'] == reason]
        wr = reason_df['win'].mean()
        print(f"  {reason:3s}: {len(reason_df):3d} trades, {wr:5.1%} win rate, P/L: ${reason_df['pnl'].sum():+8.2f}")
    print()
    
    # Underlying price movement analysis
    if 'entry_underlying' in df.columns and 'exit_underlying' in df.columns:
        df['underlying_move_pct'] = (df['exit_underlying'] - df['entry_underlying']) / df['entry_underlying'] * 100
        
        print("📊 UNDERLYING PRICE MOVEMENT:")
        print(f"  Avg move on wins: {df[df['win']]['underlying_move_pct'].mean():+.2f}%")
        print(f"  Avg move on losses: {df[~df['win']]['underlying_move_pct'].mean():+.2f}%")
        print()
    
    # Key insights
    print("=" * 80)
    print("🔍 KEY INSIGHTS:")
    print("=" * 80)
    
    # Find best time period
    best_time = time_analysis[('win', 'mean')].idxmax()
    best_time_wr = time_analysis.loc[best_time, ('win', 'mean')]
    print(f"✓ Best time period: {best_time} ({best_time_wr:.1%} win rate)")
    
    # Find worst time period
    worst_time = time_analysis[time_analysis[('win', 'count')] > 3][('win', 'mean')].idxmin()
    worst_time_wr = time_analysis.loc[worst_time, ('win', 'mean')]
    print(f"✗ Worst time period: {worst_time} ({worst_time_wr:.1%} win rate)")
    
    # Optimal duration
    best_duration = df.groupby('duration_bucket')['win'].mean().idxmax()
    print(f"✓ Best trade duration: {best_duration}")
    
    # Direction bias
    if len(df['direction'].unique()) > 1:
        best_dir = df.groupby('direction')['win'].mean().idxmax()
        best_dir_wr = df.groupby('direction')['win'].mean().max()
        print(f"✓ Better direction: {best_dir} ({best_dir_wr:.1%} win rate)")
    
    print()
    
    return df

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_backtest_patterns.py <backtest_results.csv>")
        print()
        print("Example:")
        print("  python analyze_backtest_patterns.py backtest_results_20251128_123046.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    try:
        df = analyze_patterns(csv_file)
        print("✅ Analysis complete!")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

