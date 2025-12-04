
import pandas as pd
import sys
import os

# Find the latest CSV
csv_dir = '/Users/aidan/Desktop/tradev3.5/tests/backtest_results'
files = [os.path.join(csv_dir, f) for f in os.listdir(csv_dir) if f.startswith('november_2025_') and f.endswith('.csv')]
latest_file = max(files, key=os.path.getctime)

print(f"Analyzing: {latest_file}")
df = pd.read_csv(latest_file)

# Print all trade entry times
print(f"Total Trades: {len(df)}")
print("Entry Times:")
for idx, row in df.iterrows():
    print(f"{idx+1}. {row['entry_time']} ({row['direction']}) P/L: ${row['pnl']:.2f}")

# Count trades by hour
df['entry_dt'] = pd.to_datetime(df['entry_time'])
df['hour'] = df['entry_dt'].dt.hour
print("\nTrades by Hour (ET):")
print(df['hour'].value_counts().sort_index())
