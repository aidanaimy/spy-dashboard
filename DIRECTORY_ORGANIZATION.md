# 📁 Directory Organization (v3.0)

This document explains the new organized directory structure.

---

## 🎯 What Changed

### **Before** (Messy):
```
tradev3/
├─ app.py
├─ config.py
├─ test_discord.py          ← Tests mixed with main code
├─ test_alpaca.py
├─ test_signal_notification.py
├─ analyze_backtest_patterns.py  ← ML tools mixed with main code
├─ feature_selection_optimizer.py
├─ backtest_results_*.csv
├─ logic/
├─ data/
└─ backtest/
```

### **After** (Organized):
```
tradev3/
├─ app.py                    # Main dashboard
├─ config.py                 # Configuration
├─ run_full_backtest.py      # Standalone backtest
│
├─ logic/                    # Core trading logic
├─ data/                     # Data clients
├─ backtest/                 # Backtesting engine
├─ utils/                    # Utilities
│
├─ tests/                    # ✨ NEW: All test scripts
│   ├─ README.md
│   ├─ test_discord.py
│   ├─ test_alpaca.py
│   ├─ test_alpaca_date_limits.py
│   └─ test_signal_notification.py
│
├─ ml_optimization/          # ✨ NEW: ML tools (separate from main system)
│   ├─ README.md
│   ├─ OPTIMIZATION_GUIDE.md
│   ├─ analyze_backtest_patterns.py
│   ├─ feature_selection_optimizer.py
│   ├─ backtest_results_*.csv
│   └─ backtest_1year.log
│
└─ changelog/                # Version history
    ├─ V3.md
    ├─ V2.5.md
    └─ V2.md
```

---

## 📂 Directory Purposes

### **Root Level** (Main System)
- `app.py` - Streamlit dashboard (live trading)
- `config.py` - All tunable parameters
- `run_full_backtest.py` - Standalone backtest script
- `requirements.txt` - Python dependencies
- `README.md` - Main documentation

### **logic/** (Core Trading Logic)
Contains all signal generation and analysis logic:
- `signals.py` - Main signal generation
- `regime.py` - Daily trend analysis
- `intraday.py` - 5-minute bar analysis
- `time_filters.py` - Time-of-day filtering
- `chop_detector.py` - Choppy market detection
- `iv.py` - Volatility context (IV + VIX)
- `options.py` - Black-Scholes pricing

**This is your core system** - changes here affect live trading.

### **data/** (Data Fetching)
- `alpaca_client.py` - Primary data source
- `yfinance_client.py` - Fallback data source
- `trade_journal.csv` - Manual trade log

### **backtest/** (Backtesting)
- `backtest_engine.py` - Historical simulation engine

### **utils/** (Utilities)
- `plots.py` - Plotly charts
- `journal.py` - Trade logging

### **tests/** (Testing Scripts) ✨ NEW
All test scripts isolated here:
- `test_discord.py` - Test Discord webhooks
- `test_alpaca.py` - Test Alpaca API
- `test_alpaca_date_limits.py` - Test data limits
- `test_signal_notification.py` - Test notifications

**Purpose**: Keep tests separate from main code. Run these to verify system components.

**Usage**:
```bash
python tests/test_discord.py
python tests/test_alpaca.py
```

### **ml_optimization/** (ML Tools) ✨ NEW
All machine learning and optimization tools:
- `OPTIMIZATION_GUIDE.md` - Full ML guide (start here)
- `analyze_backtest_patterns.py` - Pattern analysis (no ML needed)
- `feature_selection_optimizer.py` - ML-based optimization
- `backtest_results_*.csv` - Historical backtest data
- `backtest_1year.log` - Backtest logs

**Purpose**: Separate ML experimentation from live trading system.

**Important**: These tools are for **analysis only**. They don't modify your live system unless you manually update `config.py` based on their recommendations.

**Usage**:
```bash
# Pattern analysis (no ML libraries needed)
python ml_optimization/analyze_backtest_patterns.py ml_optimization/backtest_results_*.csv

# ML optimization (requires scikit-learn)
pip install scikit-learn matplotlib seaborn scikit-optimize
python ml_optimization/feature_selection_optimizer.py
```

### **changelog/** (Version History)
- `V3.md` - Latest changes (0DTE focus, Discord, ML tools)
- `V2.5.md` - Previous version
- `V2.md` - Earlier version

---

## 🎯 Benefits of New Structure

### **1. Clarity**
- **Main system** (root + logic/) is clearly separated from **testing** and **ML tools**
- No confusion about what affects live trading vs what's for analysis

### **2. Safety**
- ML experiments in `ml_optimization/` can't accidentally break live system
- Test scripts in `tests/` won't interfere with main code

### **3. Scalability**
- Easy to add new tests (just drop in `tests/`)
- Easy to add new ML tools (just drop in `ml_optimization/`)
- Each directory has its own README for documentation

### **4. Professionalism**
- Standard Python project structure
- Easy for others (or future you) to navigate
- Clear separation of concerns

---

## 🚀 How to Use

### **Running the Main System**
```bash
# From project root
cd /Users/aidan/Desktop/tradev3

# Start dashboard
streamlit run app.py

# Run standalone backtest
python run_full_backtest.py
```

### **Running Tests**
```bash
# Test individual components
python tests/test_discord.py
python tests/test_alpaca.py

# See tests/README.md for details
```

### **Running ML Optimization**
```bash
# Pattern analysis (quick wins)
python ml_optimization/analyze_backtest_patterns.py ml_optimization/backtest_results_*.csv

# Feature selection (advanced)
python ml_optimization/feature_selection_optimizer.py

# See ml_optimization/OPTIMIZATION_GUIDE.md for full guide
```

---

## 📝 Adding New Files

### **New Test Script**
1. Create `tests/test_your_feature.py`
2. Add usage instructions to `tests/README.md`
3. Run with: `python tests/test_your_feature.py`

### **New ML Tool**
1. Create `ml_optimization/your_tool.py`
2. Import from parent: `sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))`
3. Add usage instructions to `ml_optimization/README.md`

### **New Core Logic**
1. Create `logic/your_logic.py`
2. Import in `app.py` or `signals.py`
3. Update `config.py` if new parameters needed

---

## 🔄 Migration Notes

All files were moved without modification. The ML scripts were updated to:
- Import from parent directory correctly
- Look for CSV files in `ml_optimization/` directory

**No breaking changes** - everything still works as before, just more organized!

---

## 📚 Key Files to Read

1. **README.md** - Main project overview
2. **tests/README.md** - How to run tests
3. **ml_optimization/README.md** - ML tools overview
4. **ml_optimization/OPTIMIZATION_GUIDE.md** - Full ML guide
5. **changelog/V3.md** - Latest changes and performance

---

## 💡 Summary

- **Root + logic/** = Your live trading system
- **tests/** = Verify system components
- **ml_optimization/** = Improve win rate (analysis only)
- **changelog/** = Version history

Clean, organized, professional. 🚀

