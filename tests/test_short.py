import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.backtest_engine import BacktestEngine
from logic.regime import analyze_regime
from logic.iv import fetch_historical_vix_context
import datetime
import pandas as pd

print('🧪 TESTING: Short 1-month period (Jan 2024)')
print('Should validate: historical data fetching + VIX filter + realistic costs')
print()

# First, let's manually check what regime January 2024 would be
print('🔍 DEBUG: Checking regime analysis for Jan 2024...')

# Fetch daily data for regime analysis
from data.alpaca_client import get_daily_data_for_period
daily_df = get_daily_data_for_period('SPY', datetime.datetime(2023, 8, 1), datetime.datetime(2024, 2, 1))
print(f'📊 Daily data: {len(daily_df)} rows from {daily_df.index.min()} to {daily_df.index.max()}')

# Check a few specific days in January 2024
test_days = [
    datetime.datetime(2024, 1, 10),  # Mid-month
    datetime.datetime(2024, 1, 19),  # Later in month
    datetime.datetime(2024, 1, 31),  # End of month
]

for test_day in test_days:
    try:
        # Get VIX data
        vix_data = fetch_historical_vix_context(test_day)
        vix_level = vix_data.get('vix_level')

        # Get today's data (mock based on intraday)
        today_data = {
            'yesterday_close': 470.0,  # Approximate
            'today_open': 475.0,
            'today_high': 480.0,
            'today_low': 472.0,
            'today_close': 478.0
        }

        # Analyze regime
        regime = analyze_regime(daily_df, today_data, vix_level=vix_level)

        vix_str = f'{vix_level:.1f}' if vix_level is not None else 'None'
        print(f'📅 {test_day.date()}: VIX={vix_str} → {regime["0dte_status"]} ({regime["0dte_reason"]})')
        print(f'   Trend: {regime["trend"]}, Gap: {regime["gap_pct"]:.2f}%, Range: {regime["range_pct"]:.2f}%')

    except Exception as e:
        print(f'❌ Error for {test_day.date()}: {e}')

print()
print('🚀 Running full backtest...')

engine = BacktestEngine(use_options=True)

# Test just January 2024 (1 month, should be quick)
start_date = datetime.datetime(2024, 1, 1)
end_date = datetime.datetime(2024, 2, 1)

print(f'📅 Period: {start_date.date()} to {end_date.date()}')

try:
    # Temporarily add debug to signal generation
    from logic.signals import generate_signal
    original_generate_signal = generate_signal

    def debug_generate_signal(intraday_df, regime, prev_signal):
        result = original_generate_signal(intraday_df, regime, prev_signal)
        if result['direction'] != 'NONE':
            print(f'📊 SIGNAL: {result["direction"]} {result["confidence"]} - {result["reason"]}')
        return result

    # Monkey patch for debugging
    import logic.signals
    logic.signals.generate_signal = debug_generate_signal

    results = engine.run_backtest(start_date, end_date, use_options=True, progress_callback=None)

    # Restore original
    logic.signals.generate_signal = original_generate_signal

    print(f'\n📊 RESULTS:')
    print(f'   Trades: {results["num_trades"]}')
    if results['num_trades'] > 0:
        print(f'   Win Rate: {results["win_rate"]*100:.1f}%')
        print(f'   Net P/L: ${results["total_pnl"]:,.2f}')
        print(f'   Commissions: ${results.get("total_commissions", 0):,.2f}')
        print(f'   Avg Trade: ${results["avg_pnl"]:.2f}')
        print(f'   Max DD: {results["max_drawdown"]*100:.1f}%')
    else:
        print(f'   Win Rate: N/A (no trades)')
        print(f'   Net P/L: $0.00')
        print(f'   Commissions: $0.00')

    print(f'\n✅ Test completed successfully!')

except Exception as e:
    print(f'\n❌ Test failed: {e}')
    import traceback
    traceback.print_exc()
