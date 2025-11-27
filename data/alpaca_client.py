"""
Alpaca API client for fetching SPY market data.
Provides better data quality and historical intraday data than yfinance.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv
import config

# Try to import and initialize Alpaca API
try:
    import alpaca_trade_api as tradeapi
    
    # Load environment variables
    load_dotenv()
    
    # Try Streamlit secrets first (for Streamlit Cloud), then fall back to environment
    ALPACA_KEY = None
    ALPACA_SECRET = None
    ALPACA_BASE_URL = None
    
    # Check if we're in a Streamlit context
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            ALPACA_KEY = st.secrets.get('ALPACA_KEY')
            ALPACA_SECRET = st.secrets.get('ALPACA_SECRET')
            ALPACA_BASE_URL = st.secrets.get('ALPACA_BASE_URL', 'https://data.alpaca.markets/v2')
    except (ImportError, AttributeError, RuntimeError):
        pass
    
    # Fall back to environment variables if secrets weren't found
    if not ALPACA_KEY:
        ALPACA_KEY = os.getenv('ALPACA_KEY')
    if not ALPACA_SECRET:
        ALPACA_SECRET = os.getenv('ALPACA_SECRET')
    if not ALPACA_BASE_URL:
        ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://data.alpaca.markets/v2')

    if not ALPACA_KEY or not ALPACA_SECRET:
        raise RuntimeError("Missing Alpaca API credentials. Set ALPACA_KEY and ALPACA_SECRET in environment/secrets.")
    
    # Initialize Alpaca API client
    try:
        # Alpaca REST client: key, secret, base_url, api_version
        # For data API, base_url should be the data endpoint
        api = tradeapi.REST(
            ALPACA_KEY,
            ALPACA_SECRET,
            base_url=ALPACA_BASE_URL,
            api_version='v2'
        )
    except Exception as e:
        print(f"Warning: Could not initialize Alpaca API: {str(e)}")
        api = None
except ImportError:
    # Alpaca package not installed
    api = None
    ALPACA_KEY = None
    ALPACA_SECRET = None
    ALPACA_BASE_URL = None


def get_daily_data(symbol: str = config.SYMBOL, days: int = config.DAILY_LOOKBACK_DAYS) -> pd.DataFrame:
    """
    Fetch daily OHLCV data for the symbol using Alpaca.
    
    Args:
        symbol: Stock symbol (default: SPY)
        days: Number of days to look back
        
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    if api is None:
        raise Exception("Alpaca API not initialized")
    
    try:
        end_date = datetime.now()
        # Add significant buffer for weekends/holidays (add 50% more days)
        buffer_days = max(int(days * 1.5), 100)  # At least 100 days to ensure we have enough
        start_date = end_date - timedelta(days=buffer_days)
        
        # Fetch daily bars - Alpaca expects date strings in YYYY-MM-DD format
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        bar_set = api.get_bars(
            symbol,
            '1Day',
            start=start_str,
            end=end_str,
            feed='iex',
            adjustment='raw'
        )
        
        # Convert to DataFrame
        bars = bar_set.df
        
        if bars.empty:
            raise ValueError(f"No data returned for {symbol}")
        
        # Rename columns to match expected format (Alpaca uses lowercase)
        if 'open' in bars.columns:
            bars = bars.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
        
        # Alpaca returns UTC timestamps - convert to timezone-naive for consistency
        if bars.index.tz is not None:
            bars.index = bars.index.tz_localize(None)
        
        # Filter to requested date range (convert end_date to timezone-naive for comparison)
        if end_date.tzinfo is not None:
            end_date_naive = end_date.replace(tzinfo=None)
        else:
            end_date_naive = end_date
        bars = bars[bars.index <= end_date_naive]
        
        return bars
    
    except Exception as e:
        raise Exception(f"Error fetching daily data for {symbol}: {str(e)}")


def get_intraday_data(symbol: str = config.SYMBOL, interval: str = config.INTRADAY_INTERVAL,
                      days: int = 1, start_date: Optional[datetime] = None, 
                      end_date: Optional[datetime] = None) -> pd.DataFrame:
    """
    Fetch intraday OHLCV data using Alpaca.
    
    Args:
        symbol: Stock symbol (default: SPY)
        interval: Alpaca interval (1Min, 5Min, 15Min, etc.)
        days: Number of days to fetch (default: 1 for today) - ignored if start_date/end_date provided
        start_date: Specific start date (optional)
        end_date: Specific end date (optional)
        
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    if api is None:
        raise Exception("Alpaca API not initialized")
    
    try:
        # Convert interval format (5m -> 5Min)
        if interval.endswith('m'):
            minutes = int(interval[:-1])
            alpaca_interval = f"{minutes}Min"
        elif interval.endswith('Min'):
            alpaca_interval = interval
        else:
            alpaca_interval = "5Min"  # Default
        
        # Use provided dates or calculate from days parameter
        if start_date and end_date:
            fetch_start = start_date
            fetch_end = end_date
        else:
            fetch_end = datetime.now() if end_date is None else end_date
            fetch_start = fetch_end - timedelta(days=days + 1) if start_date is None else start_date
        
        # Fetch intraday bars - Alpaca expects RFC3339 format (YYYY-MM-DDTHH:MM:SSZ)
        # For intraday, we need to include time, but format it properly
        # Convert to UTC if needed
        if fetch_start.tzinfo is None:
            fetch_start_utc = fetch_start
        else:
            fetch_start_utc = fetch_start.astimezone(pd.Timestamp.now().tz)
        
        if fetch_end.tzinfo is None:
            fetch_end_utc = fetch_end
        else:
            fetch_end_utc = fetch_end.astimezone(pd.Timestamp.now().tz)
        
        start_str = fetch_start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = fetch_end_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        bar_set = api.get_bars(
            symbol,
            alpaca_interval,
            start=start_str,
            end=end_str,
            feed='iex',
            adjustment='raw'
        )
        
        # Convert to DataFrame
        bars = bar_set.df
        
        if bars.empty:
            raise ValueError(f"No intraday data returned for {symbol}")
        
        # Rename columns to match expected format (Alpaca uses lowercase)
        if 'open' in bars.columns:
            bars = bars.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
        
        # Alpaca returns UTC timestamps - convert to timezone-naive for consistency
        if bars.index.tz is not None:
            bars.index = bars.index.tz_localize(None)
        
        return bars
    
    except Exception as e:
        raise Exception(f"Error fetching intraday data for {symbol}: {str(e)}")


def get_latest_price(symbol: str = config.SYMBOL) -> float:
    """
    Get the latest available price for the symbol using Alpaca.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Latest price (float)
    """
    if api is None:
        raise Exception("Alpaca API not initialized")
    
    try:
        # Try to get latest trade
        trade = api.get_latest_trade(symbol)
        if trade:
            return float(trade.p)
        
        # Fallback to latest quote
        quote = api.get_latest_quote(symbol)
        if quote:
            # Use mid price
            bid = float(quote.bp) if quote.bp else 0
            ask = float(quote.ap) if quote.ap else 0
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
            elif bid > 0:
                return bid
            elif ask > 0:
                return ask
        
        # Last resort: get latest bar
        bars = api.get_bars(symbol, '1Min', limit=1)
        if bars and hasattr(bars, 'df') and not bars.df.empty:
            return float(bars.df.iloc[-1]['close'])
        elif bars and len(bars) > 0:
            return float(bars[-1].c)
        
        raise ValueError(f"No price data available for {symbol}")
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

