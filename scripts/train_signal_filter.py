#!/usr/bin/env python3
"""
Train ML Signal Filter on historical backtest data.

This script:
1. Loads backtest trade history
2. Extracts features for each trade
3. Trains XGBoost model with walk-forward validation
4. Saves model for use in live trading
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_optimization.signal_filter import SignalFilter


def load_backtest_trades(csv_path: str) -> pd.DataFrame:
    """Load backtest trades from CSV."""
    df = pd.read_csv(csv_path)
    
    # Convert timestamps
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    
    return df


def extract_features_from_trades(trades_df: pd.DataFrame) -> tuple:
    """
    Extract features and targets from trade history.
    
    Returns:
        Tuple of (features_df, targets_series)
    """
    features_list = []
    targets_list = []
    
    # Calculate rolling P/L for "recent_pnl" feature
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    
    for idx, trade in trades_df.iterrows():
        # Extract hour from entry time
        hour = trade['entry_time'].hour
        day_of_week = trade['entry_time'].dayofweek
        
        # Calculate recent P/L (last 3 trades)
        if idx >= 3:
            recent_pnl = trades_df.iloc[idx-3:idx]['pnl'].sum()
        else:
            recent_pnl = 0.0
        
        # Extract features (use placeholder values for missing data)
        # In production, these would come from the signal context
        features = {
            'vix': trade.get('vix', 15.0),  # Default if not in CSV
            'hour': hour,
            'atr': trade.get('atr', 0.5),  # Placeholder
            'vwap_distance': abs(trade.get('vwap_distance', 0.2)),  # Placeholder
            'ema_slope': trade.get('ema_slope', 0.01),  # Placeholder
            'recent_pnl': recent_pnl,
            'day_of_week': day_of_week,
            'trend_up': 1 if trade['direction'] == 'LONG' else 0,
            'trend_down': 1 if trade['direction'] == 'SHORT' else 0,
            'range_pct': trade.get('range_pct', 1.5),  # Placeholder
            'iv': trade.get('iv', 15.0)  # Placeholder
        }
        
        features_list.append(features)
        
        # Target: 1 if win, 0 if loss
        target = 1 if trade['pnl'] > 0 else 0
        targets_list.append(target)
    
    features_df = pd.DataFrame(features_list)
    targets_series = pd.Series(targets_list)
    
    return features_df, targets_series


def main():
    """Main training function."""
    print("=" * 80)
    print("ML SIGNAL FILTER TRAINING")
    print("=" * 80)
    print()
    
    # Find most recent backtest results
    results_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'scripts',
        'backtest_results'
    )
    
    # Get most recent CSV file
    csv_files = [f for f in os.listdir(results_dir) if f.startswith('backtest_trades_') and f.endswith('.csv')]
    
    if not csv_files:
        print("❌ No backtest results found!")
        print(f"   Run a backtest first: python scripts/run_full_backtest.py")
        return
    
    # Sort by timestamp in filename
    csv_files.sort(reverse=True)
    latest_csv = os.path.join(results_dir, csv_files[0])
    
    print(f"📊 Loading trades from: {csv_files[0]}")
    trades_df = load_backtest_trades(latest_csv)
    
    print(f"   Total trades: {len(trades_df)}")
    print(f"   Win rate: {(trades_df['pnl'] > 0).mean():.1%}")
    print()
    
    # Extract features
    print("🔧 Extracting features...")
    features_df, targets = extract_features_from_trades(trades_df)
    
    print(f"   Features: {list(features_df.columns)}")
    print(f"   Samples: {len(features_df)}")
    print()
    
    # Train model
    print("🚀 Training XGBoost model...")
    print("   Using walk-forward validation (33% test set)")
    print()
    
    signal_filter = SignalFilter()
    metrics = signal_filter.train(features_df, targets, test_size=0.33)
    
    # Print results
    print("=" * 80)
    print("TRAINING RESULTS")
    print("=" * 80)
    print()
    print(f"📊 Performance:")
    print(f"   Train Accuracy: {metrics['train_accuracy']:.1%} ({metrics['train_samples']} trades)")
    print(f"   Test Accuracy:  {metrics['test_accuracy']:.1%} ({metrics['test_samples']} trades)")
    print(f"   Overfit Gap:    {metrics['overfit_gap']:.1%}")
    print()
    
    if metrics['overfit_gap'] < 0.10:
        print("✅ Model shows good generalization (low overfitting)")
    elif metrics['overfit_gap'] < 0.15:
        print("⚠️ Model shows moderate overfitting (acceptable)")
    else:
        print("❌ Model shows high overfitting (may not generalize well)")
    
    print()
    print("🔍 Feature Importance:")
    importance = sorted(metrics['feature_importance'].items(), key=lambda x: x[1], reverse=True)
    for feature, score in importance[:5]:
        print(f"   {feature:20s}: {score:.3f}")
    
    print()
    
    # Save model
    model_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'models'
    )
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'signal_filter.pkl')
    
    signal_filter.save_model(model_path)
    
    print()
    print("=" * 80)
    print("✅ TRAINING COMPLETE")
    print("=" * 80)
    print()
    print(f"📁 Model saved to: {model_path}")
    print()
    print("🎯 Next Steps:")
    print("   1. Review the test accuracy and overfit gap above")
    print("   2. If acceptable, the model is ready for live use")
    print("   3. Re-run this script monthly to retrain on new data")
    print()
    print("💡 To use in live trading:")
    print("   The model will automatically load from the saved path")
    print("   and filter signals based on predicted win probability")
    print()


if __name__ == "__main__":
    main()
