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
    
    # Create subplots: price chart on top, volume on bottom
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('Price', 'Volume')
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_copy.index,
        open=df_copy['Open'],
        high=df_copy['High'],
        low=df_copy['Low'],
        close=df_copy['Close'],
        name='SPY',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
    ), row=1, col=1)
    
    # High/Low of day markers
    if len(df_copy) > 0:
        high_of_day = df_copy['High'].max()
        low_of_day = df_copy['Low'].min()
        high_time = df_copy['High'].idxmax()
        low_time = df_copy['Low'].idxmin()
        
        fig.add_trace(go.Scatter(
            x=[high_time],
            y=[high_of_day],
            mode='markers',
            marker=dict(symbol='triangle-down', size=12, color='green', line=dict(width=1, color='darkgreen')),
            name='High of Day',
            showlegend=False,
            hovertemplate='High: $%{y:.2f}<extra></extra>'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=[low_time],
            y=[low_of_day],
            mode='markers',
            marker=dict(symbol='triangle-up', size=12, color='red', line=dict(width=1, color='darkred')),
            name='Low of Day',
            showlegend=False,
            hovertemplate='Low: $%{y:.2f}<extra></extra>'
        ), row=1, col=1)
    
    # Current price line
    if current_price is not None and len(df_copy) > 0:
        signal_color = '#00ff00' if signal_direction == 'CALL' else '#ff0000' if signal_direction == 'PUT' else '#888888'
        fig.add_trace(go.Scatter(
            x=[df_copy.index[0], df_copy.index[-1]],
            y=[current_price, current_price],
            mode='lines',
            name=f'Current: ${current_price:.2f}',
            line=dict(color=signal_color, width=2, dash='dash'),
            hovertemplate=f'Current Price: ${current_price:.2f}<extra></extra>'
        ), row=1, col=1)
    
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
                line=dict(color='#2196F3', width=2.5)
            ), row=1, col=1)
    
    # Fast EMA overlay
    if ema_fast is not None:
        ema_fast_aligned = align_series(ema_fast, df_copy.index)
        if ema_fast_aligned is not None and not ema_fast_aligned.isna().all():
            fig.add_trace(go.Scatter(
                x=df_copy.index,
                y=ema_fast_aligned,
                mode='lines',
                name=f'EMA {9}',
                line=dict(color='#FF9800', width=2)
            ), row=1, col=1)
    
    # Slow EMA overlay
    if ema_slow is not None:
        ema_slow_aligned = align_series(ema_slow, df_copy.index)
        if ema_slow_aligned is not None and not ema_slow_aligned.isna().all():
            fig.add_trace(go.Scatter(
                x=df_copy.index,
                y=ema_slow_aligned,
                mode='lines',
                name=f'EMA {21}',
                line=dict(color='#9C27B0', width=2)
            ), row=1, col=1)
    
    # Volume bars
    if 'Volume' in df_copy.columns:
        colors = ['#26a69a' if df_copy.loc[idx, 'Close'] >= df_copy.loc[idx, 'Open'] else '#ef5350' 
                 for idx in df_copy.index]
        fig.add_trace(go.Bar(
            x=df_copy.index,
            y=df_copy['Volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.6,
            showlegend=False
        ), row=2, col=1)
    
    # Session markers (vertical lines)
    if market_open and market_close:
        session_times = [
            (datetime.combine(chart_date, time(9, 30)).replace(tzinfo=et_tz), 'Market Open', '#00ff00'),
            (datetime.combine(chart_date, time(12, 0)).replace(tzinfo=et_tz), 'Lunch Start', '#ffaa00'),
            (datetime.combine(chart_date, time(13, 0)).replace(tzinfo=et_tz), 'Lunch End', '#ffaa00'),
            (datetime.combine(chart_date, time(14, 30)).replace(tzinfo=et_tz), 'Power Hour', '#00ff88'),
            (datetime.combine(chart_date, time(15, 30)).replace(tzinfo=et_tz), 'Trading End', '#ff0000'),
        ]
        
        for session_time, label, color in session_times:
            if market_open <= session_time <= market_close:
                fig.add_vline(
                    x=session_time,
                    line_dash="dash",
                    line_color=color,
                    opacity=0.5,
                    annotation_text=label,
                    annotation_position="top",
                    row=1, col=1
                )
    
    # Update layout with ET timezone formatting
    fig.update_layout(
        title='SPY Intraday Chart',
        height=700,
        hovermode='x unified',
        template='plotly_dark',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Configure x-axis (shared between subplots)
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
    
    # Update both x-axes
    fig.update_xaxes(**xaxis_config, row=1, col=1)
    fig.update_xaxes(**xaxis_config, row=2, col=1)
    
    # Update y-axes
    fig.update_yaxes(title_text='Price ($)', row=1, col=1)
    fig.update_yaxes(title_text='Volume', row=2, col=1)
    
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

