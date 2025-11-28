# 🤖 ML Optimization Directory

This directory contains machine learning tools for optimizing the trading system.

**⚠️ Important**: These tools are for **analysis and optimization only**. They do not affect the live trading system unless you manually update `config.py` based on their recommendations.

---

## 📂 Contents

### **OPTIMIZATION_GUIDE.md**
Comprehensive guide explaining:
- How to use feature selection to identify important indicators
- How to run parameter optimization to find optimal thresholds
- Step-by-step roadmap for improving win rate
- Expected results and timelines

**Start here** if you're new to ML optimization.

---

### **analyze_backtest_patterns.py**
Analyzes backtest CSV files to find patterns in wins vs losses.

**Usage**:
```bash
cd /Users/aidan/Desktop/tradev3
python ml_optimization/analyze_backtest_patterns.py ml_optimization/backtest_results_20251128_123046.csv
```

**Output**:
- Win rate by time of day
- Win rate by direction (CALL/PUT)
- Win rate by confidence level
- Trade duration analysis
- Exit reason breakdown
- Key insights and recommendations

**No ML libraries required** - works with standard Python.

---

### **feature_selection_optimizer.py**
Uses machine learning to identify most important features and optimize parameters.

**Requirements**:
```bash
pip install scikit-learn matplotlib seaborn
pip install scikit-optimize  # For Bayesian optimization
pip install shap  # For interpretability (optional)
```

**Usage**:
```bash
cd /Users/aidan/Desktop/tradev3
python ml_optimization/feature_selection_optimizer.py
```

**What it does**:
1. Loads most recent backtest CSV
2. Extracts features from trades
3. Trains Random Forest model
4. Ranks features by importance
5. (Optional) Runs parameter optimization

**Output**:
- Feature importance ranking
- Permutation importance scores
- Cross-validation accuracy
- Confusion matrix
- Recommendations for system simplification

---

### **backtest_results_*.csv**
Historical backtest results with trade-level details.

**Columns**:
- `entry_time`, `exit_time`: Trade timestamps
- `direction`: CALL/PUT/LONG
- `confidence`: HIGH/MEDIUM/LOW
- `0dte_permission`: FAVORABLE/CAUTION/AVOID
- `entry_price`, `exit_price`: Option prices
- `entry_underlying`, `exit_underlying`: SPY prices
- `pnl`: Profit/loss per trade
- `exit_reason`: TP/SL/TIME
- `strike`: Option strike price
- `reason`: Signal generation reason

---

### **backtest_1year.log**
Log file from full historical backtest run.

Contains progress updates and debug information from `run_full_backtest.py`.

---

## 🎯 Typical Workflow

### **Step 1: Analyze Patterns** (No ML needed)
```bash
python ml_optimization/analyze_backtest_patterns.py ml_optimization/backtest_results_*.csv
```

Review output for quick wins:
- Which time periods have best/worst win rates?
- Do longer or shorter trades win more?
- Which exit reasons are most common?

### **Step 2: Implement Quick Wins**
Based on pattern analysis, update filters in:
- `logic/time_filters.py` (block bad time periods)
- `backtest/backtest_engine.py` (adjust SL based on duration)
- `logic/signals.py` (add VIX-based filters)

### **Step 3: Install ML Libraries** (Optional)
```bash
pip install scikit-learn matplotlib seaborn scikit-optimize shap
```

### **Step 4: Run Feature Selection**
```bash
python ml_optimization/feature_selection_optimizer.py
```

Review which features matter most for wins.

### **Step 5: Simplify System**
Based on feature importance:
- Remove low-importance features (noise reduction)
- Focus on top 10 features
- Adjust scoring weights

### **Step 6: Parameter Optimization**
Use Bayesian optimization to find optimal thresholds for:
- `GAP_SMALL_THRESHOLD`
- `RANGE_HIGH_THRESHOLD`
- `COOLDOWN_AFTER_SL_MINUTES`
- `IV_MIN_THRESHOLD`

### **Step 7: Validate**
Run backtest with new parameters on unseen data (walk-forward validation).

### **Step 8: Update Config**
If results are better, update `config.py` with optimized values.

---

## 📊 Expected Improvements

| Optimization Level | Win Rate | Annual Return | Time Required |
|-------------------|----------|---------------|---------------|
| **Current System** | 48.3% | 26.6% | - |
| **Pattern Analysis** | 52-53% | 32% | 1 week |
| **Feature Selection** | 53-55% | 35-38% | 2-3 weeks |
| **Parameter Optimization** | 55-58% | 40-45% | 4-6 weeks |
| **Continuous Learning** | 60%+ | 50%+ | Ongoing |

---

## ⚠️ Important Notes

1. **These tools are for analysis only** - they don't modify your live system
2. **Always validate on unseen data** - avoid overfitting to historical results
3. **Start with pattern analysis** - get quick wins before diving into ML
4. **Collect more data** - more trades = better ML training
5. **Update monthly** - retrain models as market conditions change

---

## 🚀 Next Steps

1. Read `OPTIMIZATION_GUIDE.md` for full details
2. Run pattern analyzer on your latest backtest
3. Implement quick wins (time filters, duration SL)
4. Install ML libraries when ready for advanced optimization
5. Run feature selection to identify key indicators
6. Optimize parameters with Bayesian search
7. Validate and update `config.py`

---

## 🤝 Questions?

See `OPTIMIZATION_GUIDE.md` for detailed explanations and examples.

