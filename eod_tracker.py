"""
End-of-Day Signal Tracker

Tracks all signals generated throughout the trading day and sends
a comprehensive EOD summary at 4:00 PM ET (market close).
"""

import json
import os
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Dict, List


class EODTracker:
    """Track signals and market data throughout the day."""
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.file_path = os.path.join(self.data_dir, "eod_tracker.json")
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """Load existing tracker data or create new."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return self._empty_day_data()
    
    def _empty_day_data(self) -> Dict:
        """Create empty data structure for a new day."""
        return {
            "date": None,
            "last_sent_date": None,
            "market_data": {
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": None
            },
            "vix_data": {
                "open": None,
                "close": None,
                "high": None,
                "low": None
            },
            "iv_data": {
                "high": None,
                "low": None
            },
            "range_pct": None,
            "dte_permission": None,
            "signals": [],
            "session_breakdown": {
                "Early Open (Reduced)": {"call": 0, "put": 0},
                "Morning Drive": {"call": 0, "put": 0},
                "Mid-Morning Trend": {"call": 0, "put": 0},
                "Early Afternoon": {"call": 0, "put": 0},
                "Afternoon Wake-up (Reduced)": {"call": 0, "put": 0},
                "Breakout Window (Boosted)": {"call": 0, "put": 0}
            }
        }
    
    def _save_data(self):
        """Persist tracker data to disk."""
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def reset_if_new_day(self, current_date: str):
        """Reset tracker if it's a new trading day."""
        if self.data.get("date") != current_date:
            self.data = self._empty_day_data()
            self.data["date"] = current_date
            self._save_data()
    
    def update_market_data(self, open_price: float, high: float, low: float, 
                          close: float, volume: int):
        """Update market OHLCV data."""
        self.data["market_data"] = {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        }
        self._save_data()
    
    def update_vix_data(self, vix_open: float = None, vix_close: float = None,
                       vix_high: float = None, vix_low: float = None):
        """Update VIX data."""
        if vix_open is not None:
            self.data["vix_data"]["open"] = vix_open
        if vix_close is not None:
            self.data["vix_data"]["close"] = vix_close
        if vix_high is not None:
            self.data["vix_data"]["high"] = vix_high
        if vix_low is not None:
            self.data["vix_data"]["low"] = vix_low
        self._save_data()
    
    def update_iv_range(self, iv_value: float):
        """Update IV high/low range."""
        if self.data["iv_data"]["high"] is None or iv_value > self.data["iv_data"]["high"]:
            self.data["iv_data"]["high"] = iv_value
        if self.data["iv_data"]["low"] is None or iv_value < self.data["iv_data"]["low"]:
            self.data["iv_data"]["low"] = iv_value
        self._save_data()
    
    def update_range_pct(self, range_pct: float):
        """Update daily range percentage."""
        self.data["range_pct"] = range_pct
        self._save_data()
    
    def update_dte_permission(self, permission: str):
        """Update 0DTE permission status."""
        self.data["dte_permission"] = permission
        self._save_data()
    
    def log_signal(self, time: str, direction: str, confidence: str, 
                   permission: str, session: str, reason: str):
        """Log a signal that was generated."""
        signal_entry = {
            "time": time,
            "direction": direction,
            "confidence": confidence,
            "permission": permission,
            "session": session,
            "reason": reason,
            "is_actionable": confidence == "HIGH" and permission == "FAVORABLE"
        }
        
        self.data["signals"].append(signal_entry)
        
        # Update session breakdown
        if session in self.data["session_breakdown"]:
            if direction == "CALL":
                self.data["session_breakdown"][session]["call"] += 1
            elif direction == "PUT":
                self.data["session_breakdown"][session]["put"] += 1
        
        self._save_data()
    
    def get_summary(self) -> Dict:
        """Get summary statistics for EOD report."""
        signals = self.data["signals"]
        
        total_signals = len(signals)
        call_signals = len([s for s in signals if s["direction"] == "CALL"])
        put_signals = len([s for s in signals if s["direction"] == "PUT"])
        
        high_signals = len([s for s in signals if s["confidence"] == "HIGH"])
        medium_signals = len([s for s in signals if s["confidence"] == "MEDIUM"])
        low_signals = len([s for s in signals if s["confidence"] == "LOW"])
        
        actionable_signals = len([s for s in signals if s["is_actionable"]])
        
        # Find most active session
        session_totals = {}
        for session, counts in self.data["session_breakdown"].items():
            total = counts["call"] + counts["put"]
            if total > 0:
                session_totals[session] = total
        
        most_active_session = max(session_totals.items(), key=lambda x: x[1])[0] if session_totals else "None"
        
        return {
            "total_signals": total_signals,
            "call_signals": call_signals,
            "put_signals": put_signals,
            "high_signals": high_signals,
            "medium_signals": medium_signals,
            "low_signals": low_signals,
            "actionable_signals": actionable_signals,
            "most_active_session": most_active_session,
            "session_breakdown": self.data["session_breakdown"],
            "market_data": self.data["market_data"],
            "vix_data": self.data["vix_data"],
            "iv_data": self.data["iv_data"],
            "range_pct": self.data["range_pct"],
            "dte_permission": self.data["dte_permission"],
            "last_sent_date": self.data.get("last_sent_date")
        }

    def mark_summary_sent(self, date_str: str):
        """Mark EOD summary as sent for the given date."""
        self.data["last_sent_date"] = date_str
        self._save_data()

    def was_summary_sent(self, date_str: str) -> bool:
        """Check if summary was already sent for the given date."""
        # Reload data to ensure we see updates from other sessions/workers
        self.data = self._load_data()
        return self.data.get("last_sent_date") == date_str


# Global tracker instance
_tracker = None

def get_tracker() -> EODTracker:
    """Get or create global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = EODTracker()
    return _tracker
