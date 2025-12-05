# Multi-Ticker 0DTE Trading System (v3.5)

This repo contains a Streamlit-based trading dashboard for 0DTE options (SPY + IWM) with rule-based signal generation, real-time Discord notifications, multi-ticker backtesting engine, and ML optimization tools.

**Version 3.5** includes:
- 🎯 **Multi-Ticker Support** - SPY and IWM with independent signal tracking
- 🚀 **Wide Stops Breakthrough** (TP: 80%, SL: 40%) - eliminates overtrading, +77% returns
- 📊 **Enhanced Trade Log** - Professional UI with expandable cards, daily P/L summaries, and visual grouping
- 🔔 **Smart Discord Notifications** - Real-time signal alerts + automated EOD market reports
- ⏰ **Optimized Time-of-Day Filters** (power hour boost, lunch chop block)
- 🎯 **High-Confidence 0DTE Signals** with FAVORABLE-day filtering
- 📈 **Multi-Ticker Backtesting** with Black-Scholes pricing
- 🤖 **ML Optimization Tools** for feature selection and parameter tuning
- 🚫 **Re-Entry Cooldown** to prevent overtrading after stop losses

---

## Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
```
Visit `http://localhost:8501`.

You only need an Alpaca data key (free IEX feed). If Alpaca isn’t reachable, the app auto-falls back to yfinance.

---

## 📁 Directory Structure

```
tradev3.5/
├─ app.py                    # Main Streamlit dashboard (multi-ticker)
├─ config.py                 # All tunable parameters
├─ requirements.txt          # Python dependencies
│
├─ data/                     # Data fetching clients
│   ├─ alpaca_client.py      # Primary (Alpaca API)
│   ├─ yfinance_client.py    # Fallback (yfinance)
│   ├─ iv_fetcher.py         # IV and VIX data fetching
│   └─ trade_journal.csv     # Manual trade log
│
├─ logic/                    # Core trading logic
│   ├─ regime.py             # Daily trend, gap, range, 0DTE permission
│   ├─ intraday.py           # VWAP, EMAs, returns, volatility
│   ├─ chop_detector.py      # Choppy market detection
│   ├─ time_filters.py       # Time-of-day filtering
│   ├─ iv.py                 # ATM IV + VIX context
│   ├─ signals.py            # Signal generation (CALL/PUT/NONE)
│   ├─ options.py            # Black-Scholes option pricing
│   ├─ eod_tracker.py        # EOD signal tracking
│   └─ eod_summary.py        # EOD Discord report generation
│
├─ backtest/                 # Backtesting engine
│   └─ backtest_engine.py    # Historical simulation
│
├─ scripts/                  # Standalone scripts
│   ├─ run_full_backtest.py      # Single-ticker backtest
│   └─ run_multi_ticker_backtest.py  # Multi-ticker backtest
│
├─ utils/                    # Utilities
│   ├─ plots.py              # Plotly charts
│   └─ journal.py            # Trade logging
│
├─ tests/                    # Test scripts
│   ├─ test_discord_v2.py    # Discord webhook + EOD test
│   ├─ test_alpaca.py        # Alpaca API test
│   └─ test_signal_notification.py
│
├─ ml_optimization/          # ML tools (optional)
│   ├─ OPTIMIZATION_GUIDE.md # Full ML guide
│   ├─ analyze_backtest_patterns.py
│   ├─ feature_selection_optimizer.py
│   └─ backtest_results_*.csv
│
└─ docs/                     # Documentation
    └─ EOD_SUMMARY.md        # EOD report documentation
```

### Data Walkthrough
1. **Daily + Intraday**  
   `app.py` fetches daily bars (cached 5 min) and 5-min intraday bars (cached 30 s) from Alpaca’s IEX feed. Outside trading hours, it reuses the last available session but clearly labels that state.
2. **Multi-Ticker Support**  
   Dashboard supports SPY and IWM with independent signal tracking. Switch between tickers using the buttons at the top of the dashboard.
3. **Regime Engine** (`logic/regime.py`)  
   - Computes 20D/50D MAs, classifies trend, measures gap/range, sets the 🚦 0DTE permission (RED/YELLOW/GREEN).
4. **Intraday Engine** (`logic/intraday.py`)  
   - Generates VWAP, 9/21 EMA, 1-/5-bar returns, realized vol, distance from VWAP, micro trend (Up/Down/Neutral).
5. **Signal Engine** (`logic/signals.py`)  
   - Base rules: CALL if trend bullish + micro trend up + price>VWAP + positive 5-bar; PUT for the symmetric case; NONE otherwise.
   - Filters: chop detector, time-of-day, **0DTE permission**, and **IV context (ATM IV + VIX)** now auto-adjust confidence.
6. **Presentation** (`app.py`)  
   - Regime tiles, volatility card, candlestick plot, stats panel, signal card, rationale panel.
7. **Trade Journal**  
   - Professional trade log with expandable cards, daily P/L summaries, and visual grouping by date. Auto-tagged "with system" or "against system." Includes delete capability and comprehensive P/L breakdowns.
8. **Backtest**  
   - Replays historical sessions using the identical signal stack. Trades 9:45–15:30 ET with configurable TP/SL (0.8% / 0.4%). Emits metrics + equity curve. Supports multi-ticker backtesting.
9. **EOD Reports**  
   - Automated end-of-day market summary sent to Discord at 4:05 PM ET. Includes SPY and IWM performance, 0DTE permission, VIX levels, and market insights.

---

## Usage Notes

- **Multi-Ticker Dashboard**: Use the SPY and IWM buttons at the top to switch between tickers. Each ticker has independent signal tracking and analysis.
- **Live Data**: Refreshes every 30 s. Free IEX feed only streams regular-session bars, so overnight the dashboard displays the last session. Morning of the next trading day it automatically switches once new bars arrive.
- **Signal Behavior**: The CALL/PUT/NONE direction can flip if conditions reverse. Confidence is capped or boosted by chop detection, time-of-day windows, 0DTE permission, and IV context. Only act on MED/HIGH signals unless you deliberately want to trade low-confidence scenarios.
- **Discord Notifications**: 
  - Real-time signal alerts for HIGH confidence + FAVORABLE/CAUTION signals
  - Automated EOD market summary at 4:05 PM ET with SPY and IWM performance, 0DTE environment assessment, and trading insights
  - @everyone pings only for actionable (HIGH + FAVORABLE) signals
- **Backtest Range**: Current engine fetches intraday bars day-by-day; reliable up to ~60 trading days per run. For longer periods, split into chunks or extend the engine to download bulk data.
- **No Broker Link**: The app never sends orders. You trade manually in your broker and log the fills.
- **Files Stored Locally**: Trade log lives at `data/trade_journal.csv`. Delete it if you want a fresh slate.

---

## Configuration Cheat Sheet (`config.py`)
- `SYMBOL`, `DAILY_LOOKBACK_DAYS`
- Trend + gap/range thresholds (`MA_SHORT`, `MA_LONG`, `GAP_*`, `RANGE_*`)
- Intraday indicators (`INTRADAY_INTERVAL`, `EMA_FAST`, `EMA_SLOW`, `VOLATILITY_LOOKBACK`)
- Time-of-day filters (`SESSION_START`, `SESSION_END`, `AVOID_TRADE_*`, `POWER_HOUR_START`, `REDUCE_CONFIDENCE_AFTER_OPEN_MINUTES`)
- Chop thresholds (`CHOP_*`)
- Backtest parameters (`BACKTEST_TP_PCT`, `BACKTEST_SL_PCT`, `BACKTEST_POSITION_SIZE`)
- Auto-refresh (`AUTO_REFRESH_ENABLED`, `AUTO_REFRESH_INTERVAL`)

Update values there to tune the system; the Streamlit app will respect your changes on next run.

---

## 🧪 Testing

Run tests to verify system components:

```bash
# Test Discord notifications and EOD reports
python tests/test_discord_v2.py

# Test Alpaca API
python tests/test_alpaca.py

# Test signal notifications
python tests/test_signal_notification.py
```

See individual test files for details.

---

## 🤖 ML Optimization (Optional)

Improve win rate using machine learning:

```bash
# Analyze backtest patterns (no ML libraries needed)
python ml_optimization/analyze_backtest_patterns.py ml_optimization/backtest_results_*.csv

# Feature selection & parameter optimization (requires scikit-learn)
pip install scikit-learn matplotlib seaborn scikit-optimize
python ml_optimization/feature_selection_optimizer.py
```

**Expected improvements**:
- Pattern analysis: +4-5% win rate
- ML optimization: +7-10% win rate

See `ml_optimization/OPTIMIZATION_GUIDE.md` for full details.

---

## 📊 Performance Metrics

**V3.5 - 2-Year Backtest Results** (Nov 2023 - Nov 2025, Wide Stops):
- **Total Trades**: 211 over 523 trading days
- **Win Rate**: 45.0%
- **Win/Loss Ratio**: 2.12:1 ($225.18 avg win / $106.18 avg loss)
- **Total P/L**: +$9,074.46
- **Annual Return**: ~45% per contract ($4,537/year gross)
- **Max Drawdown**: 8.7%
- **Profit Factor**: 1.74
- **Net Annual Return**: ~23% ($2,295/year after costs)

**V3.5 Breakthrough - Wide Stops**:
- **Take Profit**: 80% (vs 40% in V3.0) - captures full 0DTE moves
- **Stop Loss**: 40% (vs 15% in V3.0) - room for volatility
- **Result**: +77% higher returns, -31% fewer trades, +4.4% higher win rate
- **Key Insight**: Wider stops eliminate overtrading and let 0DTE edge work

**System Characteristics**:
- **Selectivity**: 0.4 trades/day (~2 trades/week)
- **Filters Applied**: HIGH confidence + FAVORABLE days only
- **Cooldown**: 30 minutes after stop loss only (no cooldown after TP)
- **Edge**: 45% win rate vs 32% breakeven = 13% edge above random

---

## 🚀 Next Steps

1. **Collect live data** for 2-4 weeks
2. **Run pattern analysis** to find quick wins
3. **Implement ML optimization** to improve win rate to 55-60%
4. **Monitor Discord notifications** for signal changes
5. **Review backtest results** monthly and adjust parameters

---

## License / Notes
- This project is for analytics + journaling only; **no broker execution**.
- Ensure your Alpaca API keys are stored in a local `.env` file (not checked into git).
- Contributions welcome—open issues for ideas or bugs.

Enjoy the signal cockpit, and trade responsibly. 🚦📈
