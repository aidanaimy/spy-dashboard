"""
Configuration constants for SPY trading dashboard.
All tunable parameters are centralized here.
"""

# Symbol
SYMBOL = "SPY"

# Moving averages (days)
MA_SHORT = 20
MA_LONG = 50

# Gap thresholds (as percentage)
GAP_SMALL_THRESHOLD = 0.002  # 0.2%
GAP_LARGE_THRESHOLD = 0.01   # 1.0%

# Range thresholds (as percentage of open)
RANGE_LOW_THRESHOLD = 0.005   # 0.5%
RANGE_NORMAL_THRESHOLD = 0.015  # 1.5%
RANGE_HIGH_THRESHOLD = 0.025   # 2.5%

# Intraday settings
INTRADAY_INTERVAL = "5m"  # yfinance interval: 1m, 5m, 15m, etc.
EMA_FAST = 9
EMA_SLOW = 21
VOLATILITY_LOOKBACK = 20  # bars for realized vol calculation

# Trading session times (ET)
SESSION_START = "09:45"
SESSION_END = "15:30"

# Time-of-day filters
AVOID_TRADE_START = "12:00"  # Start of lunch period (reduced confidence, not blocked)
AVOID_TRADE_END = "13:00"    # End of lunch period
POWER_HOUR_START = "14:30"   # Power hour start (increase confidence)
BLOCK_TRADE_AFTER = "15:30"  # Block all signals after this time (too close to market close at 16:00)
REDUCE_CONFIDENCE_AFTER_OPEN_MINUTES = 10  # Reduce confidence for first N minutes after open

# Chop detection parameters
CHOP_VWAP_CROSSES_THRESHOLD = 3  # VWAP crosses in last hour
CHOP_EMA_FLAT_THRESHOLD = 0.001  # EMA slope threshold (0.1% = flat)
CHOP_ATR_THRESHOLD = 0.002  # ATR(5m) below this = chop (0.2%)
CHOP_VWAP_RANGE_THRESHOLD = 0.002  # Range inside VWAP ±0.2% = chop

# Backtest parameters
BACKTEST_TP_PCT = 0.007   # Take profit: 0.7%
BACKTEST_SL_PCT = 0.003   # Stop loss: 0.3%
BACKTEST_POSITION_SIZE = 1.0  # Fixed position size (units)

# Journal settings
JOURNAL_FILE = "data/trade_journal.csv"

# Data lookback (request more to account for weekends/holidays)
# We need at least MA_LONG (50) trading days, so request ~80 calendar days
DAILY_LOOKBACK_DAYS = 80

# Auto-refresh settings
AUTO_REFRESH_ENABLED = True  # Enable/disable auto-refresh
AUTO_REFRESH_INTERVAL = 30000  # Refresh interval in milliseconds (30000 = 30 seconds)
# Note: Alpaca free tier = 200 requests/min, paid = 1000 requests/min
# With 30s refresh = 2 requests/min per page load (well within limits)

