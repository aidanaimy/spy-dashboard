# SPY Small-DTE Trading Dashboard (v1.5)

This repo contains a Streamlit cockpit that surfaces rule-based SPY small-DTE signals, intraday context, and accountability tooling. Version **1.5** adds:
- 0DTE permission and volatility context integrated directly into signal confidence.
- Chop and time-of-day filters (midday avoidance, power-hour boosts).
- Intraday fallback to the last completed session when the market is closed.
- Unified styling, cached data fetches, manual trade deletion, and IV awareness.

---

## Quick Start
```bash
pip install -r requirements.txt
streamlit run app.py
```
Visit `http://localhost:8501`.

You only need an Alpaca data key (free IEX feed). If Alpaca isn’t reachable, the app auto-falls back to yfinance.

---

## Architecture Overview

```
app.py (Streamlit UI)
 ├─ data/
 │   ├─ alpaca_client.py  (primary data source, IEX feed)
 │   └─ yfinance_client.py (fallback)
 ├─ logic/
 │   ├─ regime.py         (20D/50D trend, gap, range, 0DTE permission)
 │   ├─ intraday.py       (VWAP, EMAs, returns, realized vol)
 │   ├─ chop_detector.py  (VWAP crosses, flat EMAs, ATR, VWAP envelope)
 │   ├─ time_filters.py   (open reduction, midday avoid, power hour boost)
 │   ├─ iv.py             (ATM IV + VIX rank/percentile via yfinance)
 │   └─ signals.py        (CALL/PUT/NONE + confidence, now context-aware)
 ├─ utils/
 │   ├─ plots.py          (Plotly candlestick + equity curve)
 │   └─ journal.py        (CSV-backed trade log + stats)
 └─ backtest/backtest_engine.py (price-only replay using same logic)
```

### Data Walkthrough
1. **Daily + Intraday**  
   `app.py` fetches daily bars (cached 5 min) and 5-min intraday bars (cached 30 s) from Alpaca’s IEX feed. Outside trading hours, it reuses the last available session but clearly labels that state.
2. **Regime Engine** (`logic/regime.py`)  
   - Computes 20D/50D MAs, classifies trend, measures gap/range, sets the 🚦 0DTE permission (RED/YELLOW/GREEN).
3. **Intraday Engine** (`logic/intraday.py`)  
   - Generates VWAP, 9/21 EMA, 1-/5-bar returns, realized vol, distance from VWAP, micro trend (Up/Down/Neutral).
4. **Signal Engine** (`logic/signals.py`)  
   - Base rules: CALL if trend bullish + micro trend up + price>VWAP + positive 5-bar; PUT for the symmetric case; NONE otherwise.
   - Filters: chop detector, time-of-day, **0DTE permission**, and **IV context (ATM IV + VIX)** now auto-adjust confidence.
5. **Presentation** (`app.py`)  
   - Regime tiles, volatility card, candlestick plot, stats panel, signal card, rationale panel.
6. **Trade Journal**  
   - Manual trade logging with date/time, direction, bias, size, prices, notes. Auto-tagged “with system” or “against system.” Includes delete capability and P/L breakdowns.
7. **Signal Logging & Report**  
   - Each Discord alert can also append to a Google Sheet (via service-account credentials), enabling the new “Signal Report” tab and daily stats even when you’re asleep.  
   - Columns: timestamp, direction, confidence, price, micro trend, 0DTE status, market phase, rationale, ATM IV snapshot.
8. **Backtest**  
   - Replays historical sessions using the identical signal stack. Trades 9:45–15:30 ET with configurable TP/SL (0.7% / 0.3%). Emits metrics + equity curve.

---

## Usage Notes

- **Live data**: Refreshes every 30 s. Free IEX feed only streams regular-session bars, so overnight the dashboard displays the last session. Morning of the next trading day it automatically switches once new bars arrive.
- **Signal behavior**: The CALL/PUT/NONE direction can flip if conditions reverse. Confidence is capped or boosted by chop detection, time-of-day windows, 0DTE permission, and IV context. Only act on MED/HIGH signals unless you deliberately want to trade low-confidence scenarios.
- **Backtest range**: Current engine fetches intraday bars day-by-day; reliable up to ~60 trading days per run. For longer periods, split into chunks or extend the engine to download bulk data.
- **No broker link**: The app never sends orders. You trade manually in your broker and log the fills.
- **Files stored locally**: Trade log lives at `data/trade_journal.csv`. Delete it if you want a fresh slate.

---

## Configuration Cheat Sheet (`config.py`)
- `SYMBOL`, `DAILY_LOOKBACK_DAYS`
- Trend + gap/range thresholds (`MA_SHORT`, `MA_LONG`, `GAP_*`, `RANGE_*`)
- Intraday indicators (`INTRADAY_INTERVAL`, `EMA_FAST`, `EMA_SLOW`, `VOLATILITY_LOOKBACK`)
- Time-of-day filters (`SESSION_START`, `SESSION_END`, `AVOID_TRADE_*`, `POWER_HOUR_START`, `REDUCE_CONFIDENCE_AFTER_OPEN_MINUTES`)
- Chop thresholds (`CHOP_*`)
- Backtest parameters (`BACKTEST_TP_PCT`, `BACKTEST_SL_PCT`, `BACKTEST_POSITION_SIZE`)
- Auto-refresh (`AUTO_REFRESH_ENABLED`, `AUTO_REFRESH_INTERVAL`)
- Google Sheets logging (`GOOGLE_SHEET_NAME` + `gcp_service_account` secrets) if you want signal history + the report tab.

Update values there to tune the system; the Streamlit app will respect your changes on next run.

---

## Next-Step Recommendations
1. **Signal notifications**: Log every CALL/PUT flip and push a Slack/Discord/desktop alert so you can act without watching the page.
2. **Batch backtests**: Cache multi-month intraday data locally and let the engine process large spans without hammering the API.
3. **Parameter dashboard**: Expose key config knobs (thresholds, EMA lengths, TP/SL) as sidebar inputs for rapid “what-if” tests.
4. **Execution cues**: Add a lightweight playbook note (e.g., “Prefer ATM weekly” or “Use 0.3 delta”) so the signal card reminds you which contract to target.
5. **Performance analytics**: Track CALL vs PUT win rates over time, average hold duration, and P/L by time-of-day to see where the edge actually lives.

---

## License / Notes
- This project is for analytics + journaling only; **no broker execution**.
- Ensure your Alpaca API keys are stored in a local `.env` file (not checked into git).
- Contributions welcome—open issues for ideas or bugs.

Enjoy the signal cockpit, and trade responsibly. 🚦📈
