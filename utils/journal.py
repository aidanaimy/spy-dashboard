"""
Trade journal utilities for saving and reading manual trade logs.
"""

import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Optional
import config


def ensure_journal_file():
    """Ensure the journal CSV file exists with proper headers."""
    journal_path = config.JOURNAL_FILE
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(journal_path), exist_ok=True)
    
    # Create file with headers if it doesn't exist
    if not os.path.exists(journal_path):
        df = pd.DataFrame(columns=[
            'timestamp', 'ticker', 'direction', 'bias_at_time', 'size',
            'entry_price', 'exit_price', 'notes', 'with_system'
        ])
        df.to_csv(journal_path, index=False)


def load_journal() -> pd.DataFrame:
    """
    Load all trades from the journal.
    
    Returns:
        DataFrame with all trades
    """
    ensure_journal_file()
    
    if not os.path.exists(config.JOURNAL_FILE):
        return pd.DataFrame()
    
    df = pd.read_csv(config.JOURNAL_FILE)
    
    # Convert timestamp to datetime if it exists
    if 'timestamp' in df.columns and len(df) > 0:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df


def save_trade(timestamp: datetime, ticker: str, direction: str, 
               bias_at_time: Optional[str], size: float, entry_price: float,
               exit_price: Optional[float], notes: str) -> None:
    """
    Save a trade to the journal.
    
    Args:
        timestamp: Trade timestamp
        ticker: Ticker symbol
        direction: 'Long' or 'Short'
        bias_at_time: Bias at time of trade ('CALL', 'PUT', 'NONE')
        size: Position size
        entry_price: Entry price
        exit_price: Exit price (optional)
        notes: Trade notes
    """
    ensure_journal_file()
    
    # Determine if trade was with or against system
    # For Long: with system if bias was CALL
    # For Short: with system if bias was PUT
    if direction == 'Long':
        with_system = (bias_at_time == 'CALL')
    elif direction == 'Short':
        with_system = (bias_at_time == 'PUT')
    else:
        with_system = False
    
    # Create new row
    new_trade = {
        'timestamp': timestamp,
        'ticker': ticker,
        'direction': direction,
        'bias_at_time': bias_at_time if bias_at_time else 'NONE',
        'size': size,
        'entry_price': entry_price,
        'exit_price': exit_price if exit_price else None,
        'notes': notes,
        'with_system': with_system
    }
    
    # Load existing journal
    df = load_journal()
    
    # Append new trade
    new_df = pd.DataFrame([new_trade])
    df = pd.concat([df, new_df], ignore_index=True)
    
    # Save
    df.to_csv(config.JOURNAL_FILE, index=False)


def get_today_trades() -> pd.DataFrame:
    """
    Get all trades from today.
    
    Returns:
        DataFrame with today's trades
    """
    df = load_journal()
    
    if df.empty:
        return df
    
    today = datetime.now().date()
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    
    return df[df['date'] == today].copy()


def calculate_trade_pnl(entry_price: float, exit_price: float, direction: str, size: float) -> float:
    """
    Calculate P/L for a trade.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        direction: 'Long' or 'Short'
        size: Position size
        
    Returns:
        P/L value
    """
    if pd.isna(exit_price) or exit_price is None:
        return 0.0
    
    if direction == 'Long':
        return (exit_price - entry_price) * size
    else:  # Short
        return (entry_price - exit_price) * size


def delete_trade(trade_index: int) -> None:
    """
    Delete a trade from the journal by index.
    
    Args:
        trade_index: Index of the trade to delete
    """
    ensure_journal_file()
    
    df = load_journal()
    
    if df.empty:
        raise ValueError("No trades to delete")
    
    if trade_index < 0 or trade_index >= len(df):
        raise ValueError(f"Invalid trade index: {trade_index}")
    
    # Remove the row
    df = df.drop(df.index[trade_index])
    
    # Reset index
    df = df.reset_index(drop=True)
    
    # Save
    df.to_csv(config.JOURNAL_FILE, index=False)


def get_journal_stats(df: pd.DataFrame) -> Dict:
    """
    Calculate statistics from journal trades.
    
    Args:
        df: DataFrame with trades
        
    Returns:
        Dictionary with statistics
    """
    if df.empty:
        return {
            'total_trades': 0,
            'total_pnl': 0.0,
            'with_system_pnl': 0.0,
            'against_system_pnl': 0.0,
            'with_system_count': 0,
            'against_system_count': 0
        }
    
    # Calculate P/L for each trade
    df['pnl'] = df.apply(
        lambda row: calculate_trade_pnl(
            row['entry_price'],
            row['exit_price'] if pd.notna(row['exit_price']) else row['entry_price'],
            row['direction'],
            row['size']
        ),
        axis=1
    )
    
    total_pnl = df['pnl'].sum()
    
    # Split by with/against system
    with_system_df = df[df['with_system'] == True]
    against_system_df = df[df['with_system'] == False]
    
    with_system_pnl = with_system_df['pnl'].sum() if not with_system_df.empty else 0.0
    against_system_pnl = against_system_df['pnl'].sum() if not against_system_df.empty else 0.0
    
    return {
        'total_trades': len(df),
        'total_pnl': total_pnl,
        'with_system_pnl': with_system_pnl,
        'against_system_pnl': against_system_pnl,
        'with_system_count': len(with_system_df),
        'against_system_count': len(against_system_df)
    }

