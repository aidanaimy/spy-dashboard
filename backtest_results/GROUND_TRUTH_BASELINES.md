# 🎯 Ground Truth Baselines

**Last Updated:** November 29, 2025  
**System Version:** v3.5 (Commit: `78ca814`)  
**Purpose:** Regression detection - any code changes should produce identical results for these test periods

---

## 📊 Baseline Test Periods

### **Test 1: November 2025 (Single Month)**
- **Start Date:** 2025-11-01
- **End Date:** 2025-11-30
- **Trading Days:** 20
- **Data Source:** Alpaca (5-minute bars)

### **Test 2: 1-Year Period**
- **Start Date:** 2024-11-01
- **End Date:** 2025-11-30
- **Trading Days:** 262
- **Data Source:** Alpaca (5-minute bars)

---

## ✅ Ground Truth Results

### **November 2025 Baseline**

| Metric | Expected Value | Tolerance |
|:---|:---|:---|
| **Total Trades** | 18 | ±0 (exact) |
| **Win Rate** | 55.6% | ±0.1% |
| **Total P/L** | $1,669.22 | ±$10 |
| **Avg R-Multiple** | 0.35 | ±0.02 |
| **Max Drawdown** | 2.78% | ±0.5% |
| **Avg Win** | $271.54 | ±$20 |
| **Avg Loss** | -$130.77 | ±$20 |

**CSV File:** `baseline_november_2025.csv`

---

### **2-Year Baseline (Nov 2023 - Nov 2025) ⭐ PRIMARY BASELINE**

| Metric | Expected Value | Tolerance |
|:---|:---|:---|
| **Total Trades** | 167 | ±3 |
| **Win Rate** | 44.3% | ±1% |
| **Total P/L** | $5,552.37 | ±$150 |
| **Avg R-Multiple** | 0.17 | ±0.05 |
| **Max Drawdown** | 21.8% | ±2% |
| **Avg Win** | $258.60 | ±$30 |
| **Avg Loss** | -$146.06 | ±$30 |
| **Profit Factor** | 1.41 | ±0.1 |
| **Commissions** | $58.75 | ±$10 |

**CSV File:** `baseline_2year.csv`  
**Equity Curve:** `equity_curve_2year.png`

**Performance:** +55.5% return over 2 years (27.8% annualized)

---

### **1-Year Baseline (Nov 2024 - Nov 2025) 📈**

| Metric | Expected Value | Tolerance |
|:---|:---|:---|
| **Total Trades** | 154 | ±5 |
| **Win Rate** | 46.1% | ±2% |
| **Total P/L** | $6,996.79 | ±$200 |
| **Avg R-Multiple** | 0.20 | ±0.05 |
| **Max Drawdown** | 11.0% | ±2% |
| **Avg Win** | $261.22 | ±$20 |
| **Avg Loss** | -$139.16 | ±$20 |
| **Profit Factor** | 1.61 | ±0.1 |
| **Win/Loss Ratio** | 1.88:1 | ±0.2 |

**CSV File:** `backtest_trades_20251130_000929.csv`

**Context:** Full backtest with "Max 2 Consecutive Losses" circuit breaker enabled. This represents the new global standard for system performance.

**Key Observations:**
- **Strong Profitability**: ~$7,000 net profit over 1 year.
- **Low Drawdown**: Max drawdown contained to 11%, significantly better than the 40% seen during stress tests without the breaker.
- **Robustness**: The circuit breaker successfully filters out "bad days" without hindering profitable trends.

---

### **Liberation Day - April 2025 (Drawdown Period) ⚠️**

| Metric | Expected Value | Tolerance |
|:---|:---|:---|
| **Total Trades** | 44 | ±2 |
| **Win Rate** | 34.1% | ±1% |
| **Total P/L** | -$731.33 | ±$100 |
| **Avg R-Multiple** | -0.02 | ±0.05 |
| **Max Drawdown** | 24.8% | ±2% |
| **Avg Win** | $348.56 | ±$30 |
| **Avg Loss** | -$205.51 | ±$30 |
| **Profit Factor** | 0.88 | ±0.1 |
| **Win/Loss Ratio** | 1.70:1 | ±0.2 |
| **Max Loss Streak** | 12 | ±2 |

**CSV File:** `baseline_liberation_day_april2025.csv`

**Context:** April 2025 "Liberation Day" tariff announcement triggered significant market volatility. This baseline captures performance **WITH the "Max 2 Consecutive Losses" circuit breaker active**.

**Key Observations:**
- **Circuit Breaker Impact**: Saved **$1,911** compared to original baseline (-$2,642 vs -$731).
- **Reduced Drawdown**: Max drawdown improved from 40.4% to 24.8%.
- **Trade Reduction**: Cut 11 losing trades during extreme volatility.
- **System Protection**: The circuit breaker successfully prevented over-trading during the April 7th crash and other chaotic days.

**Lesson:** The "Max 2 Consecutive Losses" rule is a critical safety mechanism that significantly reduces downside during extreme market dislocations without impacting profitable months.


---

## ⚙️ System Configuration (Locked)

These parameters **must not change** for baseline comparisons:

```python
# Options Trading Parameters
BACKTEST_OPTIONS_TP_PCT = 0.8          # 80% take profit
BACKTEST_OPTIONS_SL_PCT = 0.4          # 40% stop loss
BACKTEST_OPTIONS_CONTRACTS = 1         # 1 contract per trade
BACKTEST_RISK_FREE_RATE = 0.045        # 4.5% annual

# Realistic Costs
BACKTEST_COMMISSION_PER_CONTRACT = 1.25  # $1.25 per contract
BACKTEST_SLIPPAGE_PCT = 0.001           # 0.1% slippage
BACKTEST_MAX_SPREAD_FILTER = 0.15       # 15% max spread

# Trading Rules
BACKTEST_REENTRY_COOLDOWN_MINUTES = 30  # 30-min cooldown after SL
BLOCK_TRADE_AFTER = "14:30"             # No new entries after 2:30 PM

# Signal Filters
- HIGH confidence only
- FAVORABLE 0DTE permission only
- VIX hard deck (no trades if VIX < 15)
- Chop detection enabled
- Time-of-day filters enabled
```

---

## 🔍 How to Run Regression Tests

### **Quick Test (November 2025 only):**
```bash
python run_november_backtest.py
```

**Expected output:**
```
Total Trades: 18
Win Rate: 55.6%
Total P/L: $1,669.22
```

### **Full Test (1-Year):**
```bash
python generate_baselines.py
```

**Expected output:**
```
November 2025: 18 trades, 55.6% win rate, $1,669.22 P/L
1 Year: 132 trades, 40.9% win rate, $3,083.97 P/L
```

---

## 🚨 Regression Detection Rules

### **PASS Criteria:**
- Trade count matches exactly (±tolerance)
- P/L within tolerance range
- Win rate within tolerance range

### **FAIL Criteria (Investigate Immediately):**
- Trade count differs by >2 trades
- P/L differs by >$100 (1-year) or >$10 (November)
- Win rate differs by >1%
- Different trades executed (check CSV)

### **Common Causes of Regression:**
1. ❌ Changed TP/SL percentages
2. ❌ Modified signal filters (confidence, 0DTE permission)
3. ❌ Changed time filters (BLOCK_TRADE_AFTER, etc.)
4. ❌ Modified Black-Scholes pricing logic
5. ❌ Changed commission/slippage calculations
6. ❌ Updated VIX hard deck threshold

---

## 📝 Baseline Verification Checklist

Before accepting new code changes, verify:

- [ ] November 2025 test passes (18 trades, $1,669 P/L)
- [ ] 1-Year test passes (132 trades, $3,084 P/L)
- [ ] Local and hosted dashboards match
- [ ] `audit_system.py` shows 100% pass rate
- [ ] CSV files match baseline CSVs (same trades, same order)

---

## 📅 Baseline History

### **v3.5 (November 29, 2025) - 2-Year Baseline ⭐**
- Commit: `78ca814`
- Features: Wide stops (80% TP / 40% SL), realistic costs, VIX hard deck
- **2-Year (Nov 2023 - Nov 2025):** 167 trades, 44.3% WR, +$5,552 P/L (+55.5% return)
- **1-Year (Nov 2024 - Nov 2025):** 132 trades, 40.9% WR, +$3,084 P/L (+30.8% return)
- **November 2025:** 18 trades, 55.6% WR, +$1,669 P/L (+16.7% return)
- **Liberation Day (Apr 2025):** 55 trades, 29.1% WR, -$2,642 P/L (Stress Test)
- **Annualized Return:** 27.8%
- **Max Drawdown:** 21.8%
- **Profit Factor:** 1.41


---

## 🔒 Data Integrity

**Baseline CSV Files (DO NOT MODIFY):**
- `baseline_november_2025.csv` - 18 trades with full details
- `baseline_1year.csv` - 132 trades with full details
- `baseline_liberation_day_april2025.csv` - 55 trades (Stress Test)

**Verification:**
```bash
# Check file exists and has correct number of trades
wc -l backtest_results/baseline_november_2025.csv
# Expected: 19 lines (18 trades + 1 header)

wc -l backtest_results/baseline_1year.csv
# Expected: 133 lines (132 trades + 1 header)
```

---

## ⚡ Quick Reference

**If regression detected:**
1. Run `git diff` to see what changed
2. Check `config.py` for parameter changes
3. Compare CSV files: `diff baseline_november_2025.csv <new_csv>`
4. Review `backtest_engine.py` for logic changes
5. Revert changes and re-test

**If baselines need updating:**
1. Document reason in this file under "Baseline History"
2. Run `generate_baselines.py` to create new CSVs
3. Update "Ground Truth Results" section
4. Commit with message: `"Update baselines: [reason]"`
5. Tag commit: `git tag baseline-vX.X`

---

**Remember:** These baselines are your **regression safety net**. Any deviation means something changed in the logic, data, or configuration. Investigate before accepting!
