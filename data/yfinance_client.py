"""
yfinance client for fetching SPY market data.
Handles daily and intraday data retrieval.
NOTE: This is kept as a fallback. Primary data source is now Alpaca.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
import config


def get_daily_data(symbol: str = config.SYMBOL, days: int = config.DAILY_LOOKBACK_DAYS) -> pd.DataFrame:
    """
    Fetch daily OHLCV data for the symbol.

    Args:
        symbol: Stock symbol (default: SPY)
        days: Number of days to look back

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    try:
        ticker = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        df = ticker.history(start=start_date, end=end_date, interval="1d")

        if df.empty:
            raise ValueError(f"No data returned for {symbol}")

        return df
    except Exception as e:
        raise Exception(f"Error fetching daily data for {symbol}: {str(e)}")


def get_daily_data_for_period(symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Fetch daily OHLCV data for the symbol for a specific date range.

    Args:
        symbol: Stock symbol (default: SPY)
        start_date: Start date for data
        end_date: End date for data

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    try:
        ticker = yf.Ticker(symbol)

        df = ticker.history(start=start_date, end=end_date, interval="1d")

        if df.empty:
            raise ValueError(f"No data returned for {symbol} from {start_date.date()} to {end_date.date()}")

        return df
    except Exception as e:
        raise Exception(f"Error fetching daily data for {symbol} from {start_date.date()} to {end_date.date()}: {str(e)}")


def get_intraday_data(symbol: str = config.SYMBOL, interval: str = config.INTRADAY_INTERVAL, 
                      days: int = 1, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> pd.DataFrame:
    """
    Fetch intraday OHLCV data for today (or last N days).
    
    Args:
        symbol: Stock symbol (default: SPY)
        interval: yfinance interval (1m, 5m, 15m, etc.)
        days: Number of days to fetch (default: 1 for today)
        
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # Use provided dates or calculate from days parameter
        if start_date and end_date:
            fetch_start = start_date
            fetch_end = end_date
        else:
            fetch_end = datetime.now() if end_date is None else end_date
            fetch_start = fetch_end - timedelta(days=days) if start_date is None else start_date
        
        df = ticker.history(start=fetch_start, end=fetch_end, interval=interval)
        
        if df.empty:
            raise ValueError(f"No intraday data returned for {symbol}")
        
        return df
    except Exception as e:
        raise Exception(f"Error fetching intraday data for {symbol}: {str(e)}")


def get_latest_price(symbol: str = config.SYMBOL) -> float:
    """
    Get the latest available price for the symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Latest price (float)
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        return info.get('lastPrice', info.get('regularMarketPrice', 0.0))
    except Exception as e:
        raise Exception(f"Error fetching latest price for {symbol}: {str(e)}")


def get_today_data(daily_df: pd.DataFrame, intraday_df: pd.DataFrame) -> dict:
    """
    Extract today's key data points from daily and intraday dataframes.
    
    Args:
        daily_df: Daily OHLCV dataframe
        intraday_df: Intraday OHLCV dataframe
        
    Returns:
        Dictionary with today's open, high, low, close, and yesterday's close
    """
    # Get yesterday's close from daily data
    daily_df_sorted = daily_df.sort_index()
    if len(daily_df_sorted) < 2:
        # If we don't have enough daily data, use the last close as yesterday
        yesterday_close = daily_df_sorted.iloc[-1]['Close'] if len(daily_df_sorted) > 0 else 0.0
    else:
        yesterday_close = daily_df_sorted.iloc[-2]['Close']
    
    # Get today's data from intraday
    if intraday_df.empty:
        raise ValueError("No intraday data available")
    
    intraday_df_sorted = intraday_df.sort_index()
    today_open = intraday_df_sorted.iloc[0]['Open']
    today_high = intraday_df_sorted['High'].max()
    today_low = intraday_df_sorted['Low'].min()
    today_close = intraday_df_sorted.iloc[-1]['Close']
    
    return {
        'yesterday_close': yesterday_close,
        'today_open': today_open,
        'today_high': today_high,
        'today_low': today_low,
        'today_close': today_close
    }

