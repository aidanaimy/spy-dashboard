#!/usr/bin/env python3
"""
Test Circuit Breaker Rule
Simulates "Max 2 Consecutive Losses" rule on April 2025 data.
"""

import pandas as pd
import os

def test_circuit_breaker():
    # Load the 1-Year baseline trades
    file_path = 'backtest_results/baseline_1year.csv'
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    df = pd.read_csv(file_path)
    df['entry_time'] = pd.to_datetime(df['entry_time'], utc=True)
    df['date'] = df['entry_time'].dt.date
    
    print("=" * 80)
    print("CIRCUIT BREAKER TEST: 1-YEAR BASELINE")
    print("=" * 80)
    print()
    
    # Original Stats
    original_pl = df['pnl'].sum()
    original_trades = len(df)
    print(f"Original P/L: ${original_pl:,.2f} ({original_trades} trades)")
    
    # Apply Circuit Breaker Logic
    filtered_trades = []
    skipped_trades = 0
    skipped_pl = 0
    
    # Group by day
    days = df['date'].unique()
    
    for day in days:
        day_trades = df[df['date'] == day].sort_values('entry_time')
        
        consecutive_losses = 0
        circuit_breaker_triggered = False
        
        for _, trade in day_trades.iterrows():
            if circuit_breaker_triggered:
                skipped_trades += 1
                skipped_pl += trade['pnl']
                continue
            
            # Add trade to filtered list
            filtered_trades.append(trade)
            
            # Check result
            if trade['pnl'] < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0 # Reset on win
            
            # Trigger breaker?
            if consecutive_losses >= 2:
                circuit_breaker_triggered = True
    
    # New Stats
    new_df = pd.DataFrame(filtered_trades)
    new_pl = new_df['pnl'].sum()
    new_trades = len(new_df)
    
    print(f"New P/L:      ${new_pl:,.2f} ({new_trades} trades)")
    print(f"Improvement:  ${new_pl - original_pl:,.2f}")
    print(f"Trades Cut:   {skipped_trades}")
    print(f"Avoided Loss: ${-skipped_pl:,.2f}")
    print()
    
    # Check April 7th specifically
    print("April 7th Comparison:")
    orig_7th = df[df['date'].astype(str) == '2025-04-07']['pnl'].sum()
    new_7th = new_df[new_df['date'].astype(str) == '2025-04-07']['pnl'].sum()
    print(f"  Original: ${orig_7th:,.2f}")
    print(f"  With Breaker: ${new_7th:,.2f}")
    print(f"  Saved: ${new_7th - orig_7th:,.2f}")

if __name__ == "__main__":
    test_circuit_breaker()
