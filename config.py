"""
Configuration constants for SPY trading dashboard.
All tunable parameters are centralized here.
"""

# Symbol
SYMBOL = "SPY"

# Moving averages (days)
MA_SHORT = 20
MA_LONG = 50

# Data Fetching
DAILY_LOOKBACK_DAYS = 252  # Days of daily data to fetch

# Gap thresholds (as percentage)
GAP_SMALL_THRESHOLD = 0.002  # 0.2%
GAP_LARGE_THRESHOLD = 0.01   # 1.0%

# Range thresholds (as percentage of open)
RANGE_LOW_THRESHOLD = 0.005   # 0.5%
RANGE_NORMAL_THRESHOLD = 0.015  # 1.5%
RANGE_HIGH_THRESHOLD = 0.015   # 1.5% (lowered from 2.5% to catch trending days earlier)

# Intraday settings
INTRADAY_INTERVAL = "5m"  # yfinance interval: 1m, 5m, 15m, etc.
EMA_FAST = 9
EMA_SLOW = 21
VOLATILITY_LOOKBACK = 20  # bars for realized vol calculation

# Trading session times (ET)
SESSION_START = "09:45"
SESSION_END = "15:30"

# Time-of-day filters
# Phase 1: Lunch Chop (11:45-13:30) - Reduced confidence or blocked
LUNCH_CHOP_START = "11:45"
LUNCH_CHOP_END = "13:30"

# Phase 2: Afternoon Wake-up (13:45-14:15) - Reduced confidence
AFTERNOON_WAKEUP_START = "13:45"
AFTERNOON_WAKEUP_END = "14:15"

# Phase 3: Power Hour (14:15-15:30) - Boosted confidence
POWER_HOUR_START = "14:15" 

# Block trades late in day
BLOCK_TRADE_AFTER = "14:30"  # Block all NEW entries after this time (exits allowed)

# Early open caution
REDUCE_CONFIDENCE_AFTER_OPEN_MINUTES = 10  # 9:45-9:55 reduced confidence

# Chop detection parameters
CHOP_VWAP_CROSSES_THRESHOLD = 3  # VWAP crosses in last hour
CHOP_EMA_FLAT_THRESHOLD = 0.001  # EMA slope threshold (0.1% = flat)
CHOP_ATR_THRESHOLD = 0.002  # ATR(5m) below this = chop (0.2%)
CHOP_VWAP_RANGE_THRESHOLD = 0.002  # Range inside VWAP ±0.2% = chop

# Backtest parameters
BACKTEST_TP_PCT = 0.007   # Take profit: 0.7% (for shares)
BACKTEST_SL_PCT = 0.003   # Stop loss: 0.3% (for shares)
BACKTEST_POSITION_SIZE = 100  # Number of shares

# Options Backtest parameters
BACKTEST_OPTIONS_TP_PCT = 0.20  # Take profit: 20%
BACKTEST_OPTIONS_SL_PCT = 0.50  # Stop loss: 50%
BACKTEST_OPTIONS_CONTRACTS = 1  # Number of contracts
BACKTEST_RISK_FREE_RATE = 0.045 # 4.5% annual risk-free rate
BACKTEST_REENTRY_COOLDOWN_MINUTES = 30  # Wait 30 min after stop loss before re-entering same direction

# Auto-refresh
AUTO_REFRESH_ENABLED = True
AUTO_REFRESH_INTERVAL = 30000  # 30 seconds in ms

# Data storage
JOURNAL_FILE = "data/trade_journal.csv"
