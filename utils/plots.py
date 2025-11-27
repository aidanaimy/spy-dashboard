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
                              ema_slow: Optional[pd.Series] = None) -> go.Figure:
    """
    Create a candlestick chart with VWAP and EMA overlays.
    
    Args:
        df: Intraday OHLCV dataframe
        vwap: VWAP series (optional)
        ema_fast: Fast EMA series (optional)
        ema_slow: Slow EMA series (optional)
        
    Returns:
        Plotly figure
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
    
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_copy.index,
        open=df_copy['Open'],
        high=df_copy['High'],
        low=df_copy['Low'],
        close=df_copy['Close'],
        name='SPY'
    ))
    
    # Helper function to convert series index to ET and align with df_copy
    def align_series(series, target_index):
        if series is None or len(series) == 0:
            return None
        try:
            # Convert series index to ET timezone if needed
            series_copy = series.copy()
            if series_copy.index.tz is None:
                series_copy.index = pd.to_datetime(series_copy.index).tz_localize('UTC').tz_convert(et_tz)
            elif series_copy.index.tz != et_tz:
                series_copy.index = series_copy.index.tz_convert(et_tz)
            
            # Align with target index using nearest match
            aligned = series_copy.reindex(target_index, method='ffill')
            return aligned
        except Exception:
            # If alignment fails, try to match by position if lengths are similar
            if len(series) == len(target_index):
                return pd.Series(series.values, index=target_index)
            return None
    
    # VWAP overlay
    if vwap is not None:
        vwap_aligned = align_series(vwap, df_copy.index)
        if vwap_aligned is not None and not vwap_aligned.isna().all():
            fig.add_trace(go.Scatter(
                x=df_copy.index,
                y=vwap_aligned,
                mode='lines',
                name='VWAP',
                line=dict(color='blue', width=2)
            ))
    
    # Fast EMA overlay
    if ema_fast is not None:
        ema_fast_aligned = align_series(ema_fast, df_copy.index)
        if ema_fast_aligned is not None and not ema_fast_aligned.isna().all():
            fig.add_trace(go.Scatter(
                x=df_copy.index,
                y=ema_fast_aligned,
                mode='lines',
                name=f'EMA {9}',
                line=dict(color='orange', width=1.5)
            ))
    
    # Slow EMA overlay
    if ema_slow is not None:
        ema_slow_aligned = align_series(ema_slow, df_copy.index)
        if ema_slow_aligned is not None and not ema_slow_aligned.isna().all():
            fig.add_trace(go.Scatter(
                x=df_copy.index,
                y=ema_slow_aligned,
                mode='lines',
                name=f'EMA {21}',
                line=dict(color='purple', width=1.5)
            ))
    
    # Update layout with ET timezone formatting
    layout_updates = {
        'title': 'SPY Intraday Chart',
        'xaxis_title': 'Time (ET)',
        'yaxis_title': 'Price',
        'xaxis_rangeslider_visible': False,
        'height': 600,
        'hovermode': 'x unified',
    }
    
    # Configure x-axis with ET timezone and full trading day range
    xaxis_config = {
        'tickformat': '%H:%M',
        'tickmode': 'linear',
        'dtick': 3600000,  # 1 hour in milliseconds (for datetime)
        'showgrid': True,
        'tickangle': -45,
        'ticklabelmode': 'period',
    }
    
    # Set x-axis range to show full trading day (9:00 AM - 5:00 PM ET)
    if market_open and market_close:
        xaxis_config['range'] = [market_open, market_close]
    
    layout_updates['xaxis'] = xaxis_config
    
    fig.update_layout(**layout_updates)
    
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

