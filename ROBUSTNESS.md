# System Robustness & Error Handling

## Overview
This document outlines how the trading dashboard handles failures gracefully to ensure uptime during live market hours.

## Error Handling Strategy

### 1. **Data Fetching Layer**
- **Primary**: Alpaca API (with fallback to yfinance)
- **Caching**: All data fetches are cached (daily: 5min, intraday: 30s, IV: 5min)
- **Failure Mode**: If fetch fails, uses last cached value or shows last available session

```python
try:
    data = get_cached_data(...)
except Exception as e:
    st.error(f"Error: {e}")
    return  # Gracefully exits without crashing
```

### 2. **IV Context (Volatility Data)**
- **Primary**: SPY options chain + VIX index
- **Fallback**: If VIX fetch fails, uses ATM IV as proxy
- **Failure Mode**: If both fail, `iv_context = {}` and signals proceed without IV adjustments

### 3. **Signal Generation**
- **Defensive Programming**: All optional parameters checked before use
- **Failure Mode**: Returns `NONE` signal with error reason if inputs are malformed
- **Never Crashes**: Wrapped in try/except with safe defaults

### 4. **Indicator Calculations**
- **VWAP/EMA**: Continuous calculation even during blocked periods
- **ATR/Chop Detection**: Wrapped in try/except, failures skip chop filter
- **Failure Mode**: If indicators fail, signals still generate (without that filter)

## Known Limitations

### Rate Limiting
- **yfinance**: Free tier can be throttled during high usage
- **Mitigation**: Caching reduces API calls significantly
- **Fallback**: Alpaca API as primary (more reliable)

### After-Hours Data
- **Options Chain**: May show stale/zero IV after 4 PM ET
- **Mitigation**: VIX fallback provides reasonable proxy
- **Impact**: Signals still generate, IV adjustments may be less accurate

### Data Gaps
- **Intraday**: yfinance limited to last 60 days of 5-min data
- **Mitigation**: Dashboard shows last available session if today's data missing
- **Impact**: Backtest limited to ~60 days

## Testing Recommendations

### Before Market Open (Pre-9:30 AM)
1. Check dashboard loads without errors
2. Verify "No intraday data" message shows (expected)
3. Confirm regime analysis displays (uses daily data)

### During Market Hours (9:30 AM - 4:00 PM)
1. Monitor auto-refresh (every 30s)
2. Check signals update in real-time
3. Verify IV context shows valid data (not "unavailable")

### After Market Close (Post-4:00 PM)
1. Expect low/zero ATM IV (normal for after-hours)
2. VIX fallback should prevent "unavailable" message
3. Signals should still generate (using last intraday session)

## Emergency Procedures

### If Dashboard Crashes
1. Click "🧹 Clear Cache & Reboot" in sidebar
2. Hard refresh browser (Ctrl+Shift+R / Cmd+Shift+R)
3. Check Streamlit Cloud logs for specific error

### If Signals Stop Updating
1. Check "Last updated" timestamp in sidebar
2. Toggle auto-refresh off/on
3. Manually click "🔄 Refresh Now"

### If IV Shows "Unavailable"
- **Expected**: After hours or weekends
- **Unexpected**: During market hours
- **Action**: Check if yfinance is down (external issue)

## Confidence Level

**Production Readiness**: ✅ **Ready for Live Monitoring**

The system is designed to degrade gracefully rather than crash. In worst-case scenarios:
- Signals will still generate (without IV/chop adjustments)
- Dashboard will show last available data
- No trades will execute (this is a monitoring tool, not auto-trader)

**Recommendation**: Use as a **decision-support tool** with manual oversight, not as a fully automated trading system.

