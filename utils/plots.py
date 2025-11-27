"""
Plotting utilities using Plotly.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional
from zoneinfo import ZoneInfo
from datetime import datetime, time


def plot_intraday_candlestick(df: pd.DataFrame, vwap: Optional[pd.Series] = None,
                              ema_fast: Optional[pd.Series] = None,
                              ema_slow: Optional[pd.Series] = None,
                              current_price: Optional[float] = None,
                              signal_direction: Optional[str] = None) -> go.Figure:
    """
    Create a candlestick chart with VWAP, EMA overlays, volume, and session markers.
    
    Args:
        df: Intraday OHLCV dataframe
        vwap: VWAP series (optional)
        ema_fast: Fast EMA series (optional)
        ema_slow: Slow EMA series (optional)
        current_price: Current price for marker (optional)
        signal_direction: Current signal direction for color coding (optional)
        
    Returns:
        Plotly figure with subplots
    """
    # Ensure timezone is ET and convert index if needed
    et_tz = ZoneInfo("America/New_York")
    df_copy = df.copy()
    
    # Convert index to ET if it's timezone-naive or in a different timezone
    if df_copy.index.tz is None:
        # Assume UTC if naive, convert to ET
        df_copy.index = pd.to_datetime(df_copy.index).tz_localize('UTC').tz_convert(et_tz)
    elif df_copy.index.tz != et_tz:
        df_copy.index = df_copy.index.tz_convert(et_tz)
    
    # Get the date from the first timestamp for setting the range
    if len(df_copy) > 0:
        first_timestamp = df_copy.index[0]
        chart_date = first_timestamp.date()
        
        # Set x-axis range to show full trading day (9:00 AM - 5:00 PM ET for context)
        market_open = datetime.combine(chart_date, time(9, 0)).replace(tzinfo=et_tz)
        market_close = datetime.combine(chart_date, time(17, 0)).replace(tzinfo=et_tz)
    else:
        market_open = None
        market_close = None
    
    # Create single figure for volume chart only
    fig = go.Figure()
    
    # Volume bars
    if 'Volume' in df_copy.columns:
        colors = ['#26a69a' if df_copy.loc[idx, 'Close'] >= df_copy.loc[idx, 'Open'] else '#ef5350' 
                 for idx in df_copy.index]
        fig.add_trace(go.Bar(
            x=df_copy.index,
            y=df_copy['Volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.6
        ))
    
    # Update layout with ET timezone formatting
    fig.update_layout(
        title='SPY Volume Chart',
        height=400,
        hovermode='x unified',
        template='plotly_dark',
        showlegend=True,
        xaxis_title='Time (ET)',
        yaxis_title='Volume'
    )
    
    # Configure x-axis
    xaxis_config = {
        'tickformat': '%H:%M',
        'tickmode': 'linear',
        'dtick': 3600000,  # 1 hour in milliseconds
        'showgrid': True,
        'tickangle': -45,
    }
    
    # Set x-axis range to show full trading day (9:00 AM - 5:00 PM ET)
    if market_open and market_close:
        xaxis_config['range'] = [market_open, market_close]
    
    fig.update_xaxes(**xaxis_config)
    
    return fig


def plot_equity_curve(equity_curve: pd.DataFrame) -> go.Figure:
    """
    Plot equity curve from backtest results.
    
    Args:
        equity_curve: DataFrame with 'timestamp' and 'equity' columns
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=equity_curve['timestamp'],
        y=equity_curve['equity'],
        mode='lines',
        name='Equity',
        line=dict(color='green', width=2)
    ))
    
    fig.update_layout(
        title='Backtest Equity Curve',
        xaxis_title='Date',
        yaxis_title='Equity',
        height=400,
        hovermode='x unified'
    )
    
    return fig

