
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from data.alpaca_client import get_intraday_data
import core.config as config

def get_stats():
    et_tz = ZoneInfo("America/New_York")
    today = datetime.now(et_tz)
    
    print(f"Fetching data for {today.date()}...")
    
    try:
        df = get_intraday_data(config.SYMBOL, config.INTRADAY_INTERVAL, days=1)
        
        if df.empty:
            print("No data found for today.")
            return

        # Filter for today just in case
        df = df[df.index.date == today.date()]
        
        if df.empty:
            print("No data found for today after filtering.")
            return

        open_price = df.iloc[0]['Open']
        close_price = df.iloc[-1]['Close']
        high_price = df['High'].max()
        low_price = df['Low'].min()
        volume = df['Volume'].sum()
        
        change = close_price - open_price
        change_pct = (change / open_price) * 100
        
        print(f"STATS_START")
        print(f"Date: {today.strftime('%Y-%m-%d')}")
        print(f"Open: {open_price:.2f}")
        print(f"High: {high_price:.2f}")
        print(f"Low: {low_price:.2f}")
        print(f"Close: {close_price:.2f}")
        print(f"Volume: {volume:,.0f}")
        print(f"Change: {change:.2f} ({change_pct:.2f}%)")
        print(f"STATS_END")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_stats()
