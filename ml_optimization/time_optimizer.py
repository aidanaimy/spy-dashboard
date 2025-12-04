#!/usr/bin/env python3
"""
Time-Based Parameter Optimizer using XGBoost

Optimizes trading time windows and thresholds:
- Death Zone windows
- Power Hour windows  
- VIX threshold
- Range threshold
- Opening range filter settings
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import BacktestEngine

print("=" * 80)
print("🤖 TIME-BASED PARAMETER OPTIMIZER")
print("=" * 80)
print()

# Configuration
NUM_TRIALS = 50
BACKTEST_START = datetime.now() - timedelta(days=365)
BACKTEST_END = datetime.now()

print(f"📊 Configuration:")
print(f"   Trials: {NUM_TRIALS}")
print(f"   Period: {BACKTEST_START.date()} to {BACKTEST_END.date()}")
print()

# Step 1: Generate random parameter combinations
print("=" * 80)
print("STEP 1: TESTING PARAMETER COMBINATIONS")
print("=" * 80)
print()

results = []

for trial in range(NUM_TRIALS):
    # Generate random time-based parameters
    # Death Zone: start between 13:30-14:30, duration 15-90 min
    dz_start_min = np.random.randint(90, 270)  # Minutes after 9:30 AM
    dz_duration = np.random.randint(15, 90)
    dz_start_hour = 9 + (30 + dz_start_min) // 60
    dz_start_minute = (30 + dz_start_min) % 60
    dz_start = f"{dz_start_hour:02d}:{dz_start_minute:02d}"
    
    dz_end_min = dz_start_min + dz_duration
    dz_end_hour = 9 + (30 + dz_end_min) // 60
    dz_end_minute = (30 + dz_end_min) % 60
    dz_end = f"{dz_end_hour:02d}:{dz_end_minute:02d}"
    
    # Power Hour: start between 13:30-14:30, duration 15-60 min
    ph_start_min = np.random.randint(90, 270)
    ph_duration = np.random.randint(15, 60)
    ph_start_hour = 9 + (30 + ph_start_min) // 60
    ph_start_minute = (30 + ph_start_min) % 60
    ph_start = f"{ph_start_hour:02d}:{ph_start_minute:02d}"
    
    ph_end_min = ph_start_min + ph_duration
    ph_end_hour = 9 + (30 + ph_end_min) // 60
    ph_end_minute = (30 + ph_end_min) % 60
    ph_end = f"{ph_end_hour:02d}:{ph_end_minute:02d}"
    
    # Other parameters
    vix_threshold = np.random.uniform(15, 25)
    range_threshold = np.random.uniform(0.6, 1.5)
    use_opening_range = np.random.choice([True, False])
    opening_range_threshold = np.random.uniform(0.6, 1.2) if use_opening_range else None
    opening_range_move = np.random.uniform(0.2, 0.6) if use_opening_range else None
    
    params = {
        'death_zone_start': dz_start,
        'death_zone_end': dz_end,
        'power_hour_start': ph_start,
        'power_hour_end': ph_end,
        'vix_threshold': vix_threshold,
        'range_threshold': range_threshold,
        'use_opening_range': use_opening_range,
        'opening_range_threshold': opening_range_threshold,
        'opening_range_move_threshold': opening_range_move
    }
    
    print(f"[{trial+1}/{NUM_TRIALS}] Testing:")
    print(f"   Death Zone: {dz_start}-{dz_end}, Power Hour: {ph_start}-{ph_end}")
    print(f"   VIX≥{vix_threshold:.1f}, Range≥{range_threshold:.2f}%, OR={use_opening_range}")
    
    try:
        # Run backtest with these parameters
        engine = BacktestEngine(use_options=True, param_overrides=params)
        result = engine.run_backtest(start_date=BACKTEST_START, end_date=BACKTEST_END)
        
        if result and 'trades' in result and len(result['trades']) > 0:
            # Store results
            result_data = {
                **params,
                'num_trades': result['num_trades'],
                'win_rate': result['win_rate'],
                'total_pnl': result['total_pnl'],
                'avg_win': result['avg_win'],
                'avg_loss': result['avg_loss'],
                'max_drawdown': result['max_drawdown']
            }
            results.append(result_data)
            
            print(f"   ✅ {result['num_trades']} trades, {result['win_rate']:.1%} WR, ${result['total_pnl']:.2f} P/L")
        else:
            print(f"   ⚠️  No trades")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print()

# Save results
results_df = pd.DataFrame(results)
results_df.to_csv('ml_optimization/time_param_results.csv', index=False)

print(f"✅ Completed {len(results)}/{NUM_TRIALS} successful trials")
print(f"💾 Saved to: ml_optimization/time_param_results.csv")
print()

if len(results) < 10:
    print("❌ Not enough successful trials. Exiting.")
    sys.exit(1)

# Step 2: Train XGBoost models
print("=" * 80)
print("STEP 2: TRAINING XGBOOST MODELS")
print("=" * 80)
print()

# Prepare features
feature_cols = ['vix_threshold', 'range_threshold', 'use_opening_range']
X = results_df[feature_cols].copy()
X['use_opening_range'] = X['use_opening_range'].astype(int)

y_pnl = results_df['total_pnl']
y_wr = results_df['win_rate']
y_trades = results_df['num_trades']

# Split data
X_train, X_test, y_train_pnl, y_test_pnl = train_test_split(X, y_pnl, test_size=0.2, random_state=42)
_, _, y_train_wr, y_test_wr = train_test_split(X, y_wr, test_size=0.2, random_state=42)

# Train P/L model
print("Training P/L prediction model...")
model_pnl = xgb.XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
model_pnl.fit(X_train, y_train_pnl)

# Train Win Rate model
print("Training Win Rate prediction model...")
model_wr = xgb.XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
model_wr.fit(X_train, y_train_wr)

# Evaluate
pnl_pred = model_pnl.predict(X_test)
wr_pred = model_wr.predict(X_test)

print()
print("📊 Model Performance:")
print(f"   P/L Model R²: {r2_score(y_test_pnl, pnl_pred):.3f}")
print(f"   Win Rate Model R²: {r2_score(y_test_wr, wr_pred):.3f}")
print()

# Step 3: Find best parameters from actual results
print("=" * 80)
print("STEP 3: BEST PARAMETER COMBINATIONS")
print("=" * 80)
print()

# Sort by P/L
results_sorted = results_df.sort_values('total_pnl', ascending=False)

print("🏆 TOP 10 BY P/L:")
print()
for i, (idx, row) in enumerate(results_sorted.head(10).iterrows(), 1):
    print(f"{i}. Death Zone: {row['death_zone_start']}-{row['death_zone_end']}, "
          f"Power Hour: {row['power_hour_start']}-{row['power_hour_end']}")
    print(f"   VIX≥{row['vix_threshold']:.1f}, Range≥{row['range_threshold']:.2f}%, "
          f"OR={row['use_opening_range']}")
    print(f"   📊 {row['num_trades']:.0f} trades, {row['win_rate']:.1%} WR, ${row['total_pnl']:.2f} P/L")
    print()

# Save top results
results_sorted.head(20).to_csv('ml_optimization/top_time_params.csv', index=False)
print(f"💾 Saved top 20 to: ml_optimization/top_time_params.csv")
print()

# Step 4: Validate best parameters
print("=" * 80)
print("STEP 4: VALIDATING BEST PARAMETERS")
print("=" * 80)
print()

best = results_sorted.iloc[0]
print(f"🥇 BEST PARAMETERS:")
print(f"   Death Zone: {best['death_zone_start']} - {best['death_zone_end']}")
print(f"   Power Hour: {best['power_hour_start']} - {best['power_hour_end']}")
print(f"   VIX Threshold: {best['vix_threshold']:.1f}")
print(f"   Range Threshold: {best['range_threshold']:.2f}%")
print(f"   Opening Range: {best['use_opening_range']}")
print()
print(f"📊 PERFORMANCE:")
print(f"   Trades: {best['num_trades']:.0f}")
print(f"   Win Rate: {best['win_rate']:.1%}")
print(f"   Total P/L: ${best['total_pnl']:.2f}")
print(f"   Avg Win: ${best['avg_win']:.2f}")
print(f"   Avg Loss: ${best['avg_loss']:.2f}")
print(f"   Max Drawdown: {best['max_drawdown']:.1%}")
print()

print("=" * 80)
print("✅ OPTIMIZATION COMPLETE")
print("=" * 80)
print()
print("📝 Next Steps:")
print("1. Review top 10 combinations in top_time_params.csv")
print("2. Update config.py with best parameters")
print("3. Run full backtest to verify")
print("4. Start paper trading!")
