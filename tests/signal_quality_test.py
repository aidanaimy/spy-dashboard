#!/usr/bin/env python3
"""
Analyze V3.5 signal quality by confidence level and 0DTE permission
"""

import pandas as pd
import numpy as np
from pathlib import Path

def main():
    # Load the latest backtest results
    results_dir = Path('backtest_results')
    csv_files = list(results_dir.glob('backtest_results_*.csv'))
    if not csv_files:
        print('No backtest CSV files found')
        return

    # Get most recent
    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
    print(f'Analyzing: {latest_csv}')

    # Load data
    df = pd.read_csv(latest_csv)
    print(f'Loaded {len(df)} trades')

    # Analyze by confidence level
    confidence_analysis = []
    for confidence in ['LOW', 'MEDIUM', 'HIGH']:
        conf_trades = df[df['confidence'] == confidence]
        if len(conf_trades) > 0:
            win_rate = (conf_trades['pnl'] > 0).mean() * 100
            avg_pnl = conf_trades['pnl'].mean()
            total_pnl = conf_trades['pnl'].sum()
            wins_sum = conf_trades[conf_trades['pnl'] > 0]['pnl'].sum()
            losses_sum = abs(conf_trades[conf_trades['pnl'] <= 0]['pnl'].sum())
            profit_factor = wins_sum / losses_sum if losses_sum > 0 else float('inf')

            confidence_analysis.append({
                'Confidence': confidence,
                'Trades': len(conf_trades),
                'Win_Rate': win_rate,
                'Avg_PnL': avg_pnl,
                'Total_PnL': total_pnl,
                'Profit_Factor': profit_factor
            })

    # Analyze by 0DTE permission
    permission_analysis = []
    for permission in df['0dte_permission'].unique():
        perm_trades = df[df['0dte_permission'] == permission]
        if len(perm_trades) > 0:
            win_rate = (perm_trades['pnl'] > 0).mean() * 100
            avg_pnl = perm_trades['pnl'].mean()
            total_pnl = perm_trades['pnl'].sum()
            wins_sum = perm_trades[perm_trades['pnl'] > 0]['pnl'].sum()
            losses_sum = abs(perm_trades[perm_trades['pnl'] <= 0]['pnl'].sum())
            profit_factor = wins_sum / losses_sum if losses_sum > 0 else float('inf')

            permission_analysis.append({
                'Permission': permission,
                'Trades': len(perm_trades),
                'Win_Rate': win_rate,
                'Avg_PnL': avg_pnl,
                'Total_PnL': total_pnl,
                'Profit_Factor': profit_factor
            })

    print('\n=== SIGNAL CONFIDENCE ANALYSIS ===')
    print(f"{'Confidence':8} | {'Trades':6} | {'Win%':5} | {'Avg P/L':9} | {'Total P/L':10} | {'PF':4}")
    print('-' * 60)
    for row in confidence_analysis:
        print(f"{row['Confidence']:8} | {row['Trades']:6} | {row['Win_Rate']:5.1f} | ${row['Avg_PnL']:8.2f} | ${row['Total_PnL']:9.2f} | {row['Profit_Factor']:.2f}")

    print('\n=== 0DTE PERMISSION ANALYSIS ===')
    print(f"{'Permission':10} | {'Trades':6} | {'Win%':5} | {'Avg P/L':9} | {'Total P/L':10} | {'PF':4}")
    print('-' * 60)
    for row in permission_analysis:
        print(f"{row['Permission']:10} | {row['Trades']:6} | {row['Win_Rate']:5.1f} | ${row['Avg_PnL']:8.2f} | ${row['Total_PnL']:9.2f} | {row['Profit_Factor']:.2f}")

    # Overall stats
    total_trades = len(df)
    win_rate = (df['pnl'] > 0).mean() * 100
    total_pnl = df['pnl'].sum()
    wins_sum = df[df['pnl'] > 0]['pnl'].sum()
    losses_sum = abs(df[df['pnl'] <= 0]['pnl'].sum())
    profit_factor = wins_sum / losses_sum if losses_sum > 0 else float('inf')

    print(f'\n=== OVERALL PERFORMANCE ===')
    print(f'Total Trades: {total_trades}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Total P/L: ${total_pnl:.2f}')
    print(f'Profit Factor: {profit_factor:.2f}')

if __name__ == '__main__':
    main()
