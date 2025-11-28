#!/usr/bin/env python3
"""Test Alpaca data limits for different date ranges."""

import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, '/Users/aidan/Desktop/tradev3')

from data.alpaca_client import get_intraday_data
import config

def test_date_range(start_date, end_date, description):
    """Test fetching data for a specific date range."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Range: {start_date.date()} to {end_date.date()}")
    print(f"Days: {(end_date - start_date).days}")
    print(f"{'='*60}")
    
    try:
        df = get_intraday_data(
            config.SYMBOL,
            interval=config.INTRADAY_INTERVAL,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            print("❌ FAILED: Empty DataFrame returned")
        else:
            print(f"✅ SUCCESS: Retrieved {len(df)} bars")
            print(f"   First bar: {df.index[0]}")
            print(f"   Last bar: {df.index[-1]}")
            
            # Calculate actual date range
            first_date = df.index[0].date()
            last_date = df.index[-1].date()
            actual_days = (last_date - first_date).days
            print(f"   Actual span: {actual_days} days")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    print("🔍 Testing Alpaca Data Limits for Backtesting")
    
    # Test cases
    end_date = datetime(2025, 11, 28)
    
    # Working range (3 months)
    test_date_range(
        datetime(2025, 9, 1),
        end_date,
        "3 months (Sep 1 - Nov 28) - SHOULD WORK"
    )
    
    # Failing range (4 months)
    test_date_range(
        datetime(2025, 8, 1),
        end_date,
        "4 months (Aug 1 - Nov 28) - USER SAYS FAILS"
    )
    
    # Test boundary (3.5 months)
    test_date_range(
        datetime(2025, 8, 15),
        end_date,
        "3.5 months (Aug 15 - Nov 28) - BOUNDARY TEST"
    )
    
    # Test exact 90 days
    test_date_range(
        end_date - timedelta(days=90),
        end_date,
        "Exactly 90 days - COMMON API LIMIT"
    )
    
    # Test exact 100 days
    test_date_range(
        end_date - timedelta(days=100),
        end_date,
        "Exactly 100 days"
    )
    
    print("\n" + "="*60)
    print("Testing complete!")
