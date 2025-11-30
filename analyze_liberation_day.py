import pandas as pd
import os

def analyze_liberation_day():
    # Load the data
    file_path = 'backtest_results/baseline_liberation_day_april2025.csv'
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    df = pd.read_csv(file_path)
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['date'] = df['entry_time'].dt.date

    print("=" * 80)
    print("LIBERATION DAY (APRIL 2025) - DEEP DIVE ANALYSIS")
    print("=" * 80)
    print()

    # 1. Directional Bias Analysis
    print("1. DIRECTIONAL BIAS")
    print("-" * 40)
    direction_counts = df['direction'].value_counts()
    print(f"Total Trades: {len(df)}")
    print(f"Long Trades (Calls): {direction_counts.get('LONG', 0)} ({direction_counts.get('LONG', 0)/len(df):.1%})")
    print(f"Short Trades (Puts): {direction_counts.get('SHORT', 0)} ({direction_counts.get('SHORT', 0)/len(df):.1%})")
    
    # P/L by Direction
    pnl_by_direction = df.groupby('direction')['pnl'].sum()
    print("\nP/L by Direction:")
    print(pnl_by_direction)
    print()

    # 2. Daily Breakdown
    print("2. DAILY BREAKDOWN")
    print("-" * 40)
    daily_stats = df.groupby('date').agg({
        'direction': lambda x: x.value_counts().index[0] if len(x) > 0 else 'N/A', # Dominant direction
        'pnl': 'sum',
        'entry_price': 'count' # Trade count
    }).rename(columns={'entry_price': 'trades'})
    
    daily_stats['cumulative_pnl'] = daily_stats['pnl'].cumsum()
    
    print(daily_stats)
    print()

    # 3. Why didn't it catch the trend? (Signal Reasons)
    print("3. SIGNAL REASONS (Why did we enter?)")
    print("-" * 40)
    # Extract key phrases from reasons
    all_reasons = []
    for reason in df['reason']:
        if isinstance(reason, str):
            parts = reason.split(';')
            all_reasons.extend([p.strip() for p in parts])
    
    reason_counts = pd.Series(all_reasons).value_counts().head(10)
    print("Top 10 Signal Triggers:")
    print(reason_counts)
    print()

    # 4. Loss Analysis
    print("4. LOSS ANALYSIS")
    print("-" * 40)
    # Check if stops were hit immediately (volatility)
    df['duration_mins'] = (pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])).dt.total_seconds() / 60
    
    losses = df[df['pnl'] < 0]
    print(f"Total Losses: {len(losses)}")
    print(f"Avg Loss: ${losses['pnl'].mean():.2f}")
    
    fast_losses = losses[losses['duration_mins'] < 15]
    print(f"Fast Losses (< 15 mins): {len(fast_losses)} ({len(fast_losses)/len(losses):.1%} of losses)")
    print("  -> Suggests extreme volatility stopping out positions immediately")
    print()

    # 5. April 7th Deep Dive (The Crash Day)
    print("5. APRIL 7th CRASH ANALYSIS")
    print("-" * 40)
    crash_day = df[df['date'].astype(str) == '2025-04-07']
    if not crash_day.empty:
        print(crash_day[['entry_time', 'direction', 'pnl', 'exit_reason', 'duration_mins']].to_string(index=False))
        print(f"\nTotal P/L on April 7th: ${crash_day['pnl'].sum():.2f}")
        print("Observation: Look at the flip-flopping between Long and Short.")
    else:
        print("No trades on April 7th.")

if __name__ == "__main__":
    analyze_liberation_day()
