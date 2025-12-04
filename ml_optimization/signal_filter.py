"""
ML-based Signal Filter using XGBoost

Predicts win probability for each signal to filter out low-quality trades.
Designed to avoid overfitting with walk-forward validation and regularization.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple
import pickle
import os
from pathlib import Path

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️ XGBoost not installed. Run: pip install xgboost")


class SignalFilter:
    """ML model to predict signal win probability."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the signal filter.
        
        Args:
            model_path: Path to saved model file (optional)
        """
        self.model = None
        self.feature_names = None
        self.is_trained = False
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def extract_features(self, 
                        vix: float,
                        hour: int,
                        atr: float,
                        vwap_distance: float,
                        ema_slope: float,
                        recent_pnl: float,
                        day_of_week: int,
                        micro_trend: str,
                        range_pct: float,
                        iv: float) -> Dict[str, float]:
        """
        Extract features from signal context.
        
        Args:
            vix: VIX level
            hour: Hour of day (0-23)
            atr: Average True Range (volatility)
            vwap_distance: Distance from VWAP (%)
            ema_slope: EMA 9 slope
            recent_pnl: P/L from last 3 trades
            day_of_week: 0=Monday, 4=Friday
            micro_trend: 'Up', 'Down', or 'Neutral'
            range_pct: Daily range percentage
            iv: Implied Volatility
            
        Returns:
            Dictionary of features
        """
        # Encode micro trend
        trend_up = 1 if micro_trend == 'Up' else 0
        trend_down = 1 if micro_trend == 'Down' else 0
        
        features = {
            'vix': vix,
            'hour': hour,
            'atr': atr,
            'vwap_distance': abs(vwap_distance),  # Absolute distance
            'ema_slope': ema_slope,
            'recent_pnl': recent_pnl,
            'day_of_week': day_of_week,
            'trend_up': trend_up,
            'trend_down': trend_down,
            'range_pct': range_pct,
            'iv': iv
        }
        
        return features
    
    def train(self, 
              features_df: pd.DataFrame, 
              targets: pd.Series,
              test_size: float = 0.33) -> Dict:
        """
        Train the model with walk-forward validation.
        
        Args:
            features_df: DataFrame with features
            targets: Series with binary outcomes (1=win, 0=loss)
            test_size: Fraction of data to use for testing
            
        Returns:
            Dictionary with training metrics
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost not installed")
        
        # Split data (time-series split - no shuffling!)
        split_idx = int(len(features_df) * (1 - test_size))
        
        X_train = features_df.iloc[:split_idx]
        y_train = targets.iloc[:split_idx]
        X_test = features_df.iloc[split_idx:]
        y_test = targets.iloc[split_idx:]
        
        print(f"Training on {len(X_train)} trades, testing on {len(X_test)} trades")
        
        # Store feature names
        self.feature_names = list(features_df.columns)
        
        # Initialize model with anti-overfitting parameters
        self.model = XGBClassifier(
            max_depth=3,                # Shallow trees (prevent overfitting)
            min_child_weight=5,         # Min samples per leaf
            learning_rate=0.05,         # Slow learning
            n_estimators=50,            # Limited trees
            reg_lambda=1.0,             # L2 regularization
            reg_alpha=0.5,              # L1 regularization
            subsample=0.8,              # Use 80% of data per tree
            colsample_bytree=0.8,       # Use 80% of features per tree
            random_state=42,
            eval_metric='logloss'
        )
        
        # Train model
        self.model.fit(X_train, y_train)
        
        self.is_trained = True
        
        # Evaluate
        train_preds = self.model.predict(X_train)
        test_preds = self.model.predict(X_test)
        
        train_acc = (train_preds == y_train).mean()
        test_acc = (test_preds == y_test).mean()
        
        # Get probabilities
        train_probs = self.model.predict_proba(X_train)[:, 1]
        test_probs = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'overfit_gap': train_acc - test_acc,
            'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_))
        }
        
        # Check for overfitting
        if metrics['overfit_gap'] > 0.15:
            print(f"⚠️ WARNING: Possible overfitting detected (gap: {metrics['overfit_gap']:.2%})")
        
        return metrics
    
    def predict_win_probability(self, features: Dict[str, float]) -> float:
        """
        Predict win probability for a signal.
        
        Args:
            features: Dictionary of features
            
        Returns:
            Win probability (0.0 to 1.0)
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet")
        
        # Convert to DataFrame with correct column order
        features_df = pd.DataFrame([features])[self.feature_names]
        
        # Get probability of winning (class 1)
        prob = self.model.predict_proba(features_df)[0][1]
        
        return prob
    
    def should_trade(self, features: Dict[str, float], threshold: float = 0.55) -> Tuple[bool, float]:
        """
        Determine if signal should be traded based on win probability.
        
        Args:
            features: Dictionary of features
            threshold: Minimum win probability to trade (default: 0.55)
            
        Returns:
            Tuple of (should_trade, win_probability)
        """
        if not self.is_trained:
            # If model not trained, allow all trades
            return True, 0.5
        
        prob = self.predict_win_probability(features)
        should_trade = prob >= threshold
        
        return should_trade, prob
    
    def save_model(self, path: str):
        """Save model to disk."""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"✅ Model saved to {path}")
    
    def load_model(self, path: str):
        """Load model from disk."""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.is_trained = model_data['is_trained']
        
        print(f"✅ Model loaded from {path}")


def get_signal_filter(model_path: Optional[str] = None) -> SignalFilter:
    """
    Get or create signal filter instance.
    
    Args:
        model_path: Path to saved model (optional)
        
    Returns:
        SignalFilter instance
    """
    if model_path is None:
        # Default path
        model_path = os.path.join(
            os.path.dirname(__file__),
            'models',
            'signal_filter.pkl'
        )
    
    if os.path.exists(model_path):
        return SignalFilter(model_path)
    else:
        return SignalFilter()
