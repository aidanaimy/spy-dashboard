#!/usr/bin/env python3
"""
Feature Selection & Parameter Optimization Framework
Uses machine learning to identify most important features and optimal parameter values.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.inspection import permutation_importance
    import matplotlib.pyplot as plt
    import seaborn as sns
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️  Warning: scikit-learn not installed. Install with: pip install scikit-learn matplotlib seaborn")

# Optional: SHAP for interpretability
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

# Optional: Bayesian optimization
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False

# Import our backtest engine
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.backtest_engine import BacktestEngine
import config


def extract_features_from_backtest(csv_file: str) -> pd.DataFrame:
    """
    Extract features from backtest results CSV.
    Limited to what's already in the CSV.
    """
    df = pd.read_csv(csv_file)
    
    # Parse datetimes
    df['entry_time'] = pd.to_datetime(df['entry_time'], utc=True)
    df['exit_time'] = pd.to_datetime(df['exit_time'], utc=True)
    
    # Target variable
    df['win'] = (df['pnl'] > 0).astype(int)
    
    # Time features
    df['entry_hour'] = df['entry_time'].dt.hour
    df['entry_minute'] = df['entry_time'].dt.minute
    df['minutes_since_open'] = (df['entry_hour'] - 9) * 60 + (df['entry_minute'] - 30)
    df['day_of_week'] = df['entry_time'].dt.dayofweek
    
    # Duration
    duration_diff = df['exit_time'] - df['entry_time']
    df['duration_minutes'] = duration_diff.dt.total_seconds() / 60
    
    # Price movement
    if 'entry_underlying' in df.columns and 'exit_underlying' in df.columns:
        df['underlying_move_pct'] = (df['exit_underlying'] - df['entry_underlying']) / df['entry_underlying'] * 100
    
    # Option price movement
    if 'entry_price' in df.columns and 'exit_price' in df.columns:
        df['option_move_pct'] = (df['exit_price'] - df['entry_price']) / df['entry_price'] * 100
    
    # Encode categorical features
    df['direction_encoded'] = (df['direction'] == 'LONG').astype(int)
    
    if 'confidence' in df.columns:
        confidence_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
        df['confidence_encoded'] = df['confidence'].map(confidence_map).fillna(1)
    
    if '0dte_permission' in df.columns:
        permission_map = {'AVOID': 0, 'CAUTION': 1, 'FAVORABLE': 2}
        df['permission_encoded'] = df['0dte_permission'].map(permission_map).fillna(1)
    
    return df


def analyze_feature_importance(df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
    """
    Use Random Forest to determine feature importance.
    """
    if not ML_AVAILABLE:
        print("❌ scikit-learn not installed. Cannot run feature importance analysis.")
        return None
    
    print("=" * 80)
    print("🔬 FEATURE IMPORTANCE ANALYSIS")
    print("=" * 80)
    print()
    
    # Prepare data
    X = df[feature_cols].fillna(0)
    y = df['win']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    
    print(f"📊 Dataset: {len(X_train)} train, {len(X_test)} test")
    print(f"   Win rate: {y.mean():.1%}")
    print()
    
    # Train Random Forest
    print("🌲 Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42
    )
    rf.fit(X_train, y_train)
    
    # Evaluate
    train_score = rf.score(X_train, y_train)
    test_score = rf.score(X_test, y_test)
    
    print(f"   Train accuracy: {train_score:.1%}")
    print(f"   Test accuracy: {test_score:.1%}")
    print()
    
    # Feature importance
    importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("📈 TOP 10 MOST IMPORTANT FEATURES:")
    for idx, row in importance_df.head(10).iterrows():
        print(f"   {row['feature']:30s}: {row['importance']:.4f}")
    print()
    
    # Permutation importance (more reliable)
    print("🔀 Computing permutation importance...")
    perm_importance = permutation_importance(rf, X_test, y_test, n_repeats=10, random_state=42)
    
    perm_df = pd.DataFrame({
        'feature': feature_cols,
        'perm_importance': perm_importance.importances_mean,
        'perm_std': perm_importance.importances_std
    }).sort_values('perm_importance', ascending=False)
    
    print("📊 TOP 10 FEATURES (Permutation Importance):")
    for idx, row in perm_df.head(10).iterrows():
        print(f"   {row['feature']:30s}: {row['perm_importance']:.4f} ± {row['perm_std']:.4f}")
    print()
    
    # Cross-validation
    print("✅ Cross-validation (5-fold):")
    cv_scores = cross_val_score(rf, X, y, cv=5)
    print(f"   CV Accuracy: {cv_scores.mean():.1%} ± {cv_scores.std():.1%}")
    print()
    
    # Predictions
    y_pred = rf.predict(X_test)
    
    print("📊 CLASSIFICATION REPORT:")
    print(classification_report(y_test, y_pred, target_names=['Loss', 'Win']))
    print()
    
    print("🎯 CONFUSION MATRIX:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"   True Negatives (correct loss): {cm[0,0]}")
    print(f"   False Positives (predicted win, was loss): {cm[0,1]}")
    print(f"   False Negatives (predicted loss, was win): {cm[1,0]}")
    print(f"   True Positives (correct win): {cm[1,1]}")
    print()
    
    return importance_df, perm_df, rf


def optimize_parameters_grid_search(param_ranges: Dict) -> Dict:
    """
    Grid search over parameter space.
    Tests all combinations to find optimal values.
    """
    print("=" * 80)
    print("⚙️  PARAMETER OPTIMIZATION (Grid Search)")
    print("=" * 80)
    print()
    
    from itertools import product
    
    # Generate all combinations
    param_names = list(param_ranges.keys())
    param_values = list(param_ranges.values())
    combinations = list(product(*param_values))
    
    print(f"🔍 Testing {len(combinations)} parameter combinations...")
    print()
    
    best_sharpe = -999
    best_params = None
    results = []
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        
        # Override config temporarily
        original_values = {}
        for key, value in params.items():
            if hasattr(config, key):
                original_values[key] = getattr(config, key)
                setattr(config, key, value)
        
        # Run backtest
        try:
            engine = BacktestEngine(
                tp_pct=config.BACKTEST_OPTIONS_TP_PCT,
                sl_pct=config.BACKTEST_OPTIONS_SL_PCT,
                position_size=config.BACKTEST_OPTIONS_CONTRACTS,
                use_options=True
            )
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)  # 3 months
            
            backtest_results = engine.run_backtest(start_date, end_date, use_options=True)
            
            # Calculate Sharpe ratio
            if backtest_results['max_drawdown'] > 0:
                sharpe = backtest_results['total_pnl'] / backtest_results['max_drawdown']
            else:
                sharpe = backtest_results['total_pnl']
            
            results.append({
                'params': params.copy(),
                'sharpe': sharpe,
                'pnl': backtest_results['total_pnl'],
                'win_rate': backtest_results['win_rate'],
                'trades': backtest_results['total_trades']
            })
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params.copy()
                print(f"✓ New best: Sharpe={sharpe:.2f}, P/L=${backtest_results['total_pnl']:.2f}, WR={backtest_results['win_rate']:.1%}")
        
        except Exception as e:
            print(f"✗ Error with params {params}: {e}")
        
        finally:
            # Restore original config
            for key, value in original_values.items():
                setattr(config, key, value)
    
    print()
    print("=" * 80)
    print("🏆 BEST PARAMETERS:")
    print("=" * 80)
    for key, value in best_params.items():
        print(f"   {key}: {value}")
    print(f"   Sharpe Ratio: {best_sharpe:.2f}")
    print()
    
    return best_params, results


def optimize_parameters_bayesian(param_space: List, n_calls: int = 50) -> Dict:
    """
    Bayesian optimization - smarter parameter search.
    """
    if not SKOPT_AVAILABLE:
        print("❌ scikit-optimize not installed. Install with: pip install scikit-optimize")
        return None
    
    print("=" * 80)
    print("🧠 PARAMETER OPTIMIZATION (Bayesian)")
    print("=" * 80)
    print()
    
    def objective(params):
        """Objective function to minimize (negative Sharpe)."""
        # Map params to config
        param_dict = {
            'RANGE_HIGH_THRESHOLD': params[0],
            'GAP_SMALL_THRESHOLD': params[1],
            'COOLDOWN_AFTER_SL_MINUTES': int(params[2])
        }
        
        # Override config
        original_values = {}
        for key, value in param_dict.items():
            if hasattr(config, key):
                original_values[key] = getattr(config, key)
                setattr(config, key, value)
        
        try:
            # Run backtest
            engine = BacktestEngine(
                tp_pct=config.BACKTEST_OPTIONS_TP_PCT,
                sl_pct=config.BACKTEST_OPTIONS_SL_PCT,
                position_size=config.BACKTEST_OPTIONS_CONTRACTS,
                use_options=True
            )
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            results = engine.run_backtest(start_date, end_date, use_options=True)
            
            # Calculate Sharpe
            if results['max_drawdown'] > 0:
                sharpe = results['total_pnl'] / results['max_drawdown']
            else:
                sharpe = results['total_pnl']
            
            print(f"   Tested: {param_dict} → Sharpe={sharpe:.2f}")
            
            return -sharpe  # Minimize negative Sharpe
        
        except Exception as e:
            print(f"   Error: {e}")
            return 999  # Penalize errors
        
        finally:
            # Restore config
            for key, value in original_values.items():
                setattr(config, key, value)
    
    # Run optimization
    result = gp_minimize(
        objective,
        param_space,
        n_calls=n_calls,
        random_state=42,
        verbose=False
    )
    
    print()
    print("=" * 80)
    print("🏆 OPTIMAL PARAMETERS:")
    print("=" * 80)
    print(f"   RANGE_HIGH_THRESHOLD: {result.x[0]:.4f}")
    print(f"   GAP_SMALL_THRESHOLD: {result.x[1]:.4f}")
    print(f"   COOLDOWN_AFTER_SL_MINUTES: {int(result.x[2])}")
    print(f"   Expected Sharpe: {-result.fun:.2f}")
    print()
    
    return result


def main():
    """Main execution."""
    print("=" * 80)
    print("🤖 FEATURE SELECTION & PARAMETER OPTIMIZATION")
    print("=" * 80)
    print()
    
    # Check for backtest CSV in ml_optimization directory
    import glob
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_files = glob.glob(os.path.join(script_dir, 'backtest_results_*.csv'))
    
    if not csv_files:
        print("❌ No backtest CSV files found in ml_optimization/ directory.")
        print("   Run a backtest first, then move the CSV to ml_optimization/")
        return
    
    # Use most recent
    csv_file = max(csv_files, key=lambda x: x.split('_')[-1])
    print(f"📂 Using: {os.path.basename(csv_file)}")
    print()
    
    # Extract features
    print("📊 Extracting features from backtest...")
    df = extract_features_from_backtest(csv_file)
    print(f"   Loaded {len(df)} trades")
    print()
    
    # Define feature columns
    feature_cols = [
        'entry_hour',
        'entry_minute',
        'minutes_since_open',
        'day_of_week',
        'direction_encoded',
    ]
    
    if 'confidence_encoded' in df.columns:
        feature_cols.append('confidence_encoded')
    if 'permission_encoded' in df.columns:
        feature_cols.append('permission_encoded')
    if 'underlying_move_pct' in df.columns:
        feature_cols.append('underlying_move_pct')
    
    # Feature importance analysis
    if ML_AVAILABLE:
        importance_df, perm_df, model = analyze_feature_importance(df, feature_cols)
    
    # Parameter optimization
    print("=" * 80)
    print("Would you like to run parameter optimization?")
    print("  1. Grid Search (systematic, slower)")
    print("  2. Bayesian Optimization (smarter, faster)")
    print("  3. Skip")
    print("=" * 80)
    
    # For now, skip interactive prompt
    print("Skipping parameter optimization (run manually if needed)")
    print()
    
    print("✅ Analysis complete!")
    print()
    print("💡 NEXT STEPS:")
    print("   1. Review feature importance above")
    print("   2. Focus on top 5-10 features for optimization")
    print("   3. Run parameter optimization to fine-tune thresholds")
    print("   4. Collect more live data for better ML training")
    print()


if __name__ == "__main__":
    main()

