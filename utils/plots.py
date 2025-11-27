"""
Plotting utilities using Plotly.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional


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
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='SPY'
    ))
    
    # VWAP overlay
    if vwap is not None:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=vwap,
            mode='lines',
            name='VWAP',
            line=dict(color='blue', width=2)
        ))
    
    # Fast EMA overlay
    if ema_fast is not None:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=ema_fast,
            mode='lines',
            name=f'EMA {9}',
            line=dict(color='orange', width=1.5)
        ))
    
    # Slow EMA overlay
    if ema_slow is not None:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=ema_slow,
            mode='lines',
            name=f'EMA {21}',
            line=dict(color='purple', width=1.5)
        ))
    
    fig.update_layout(
        title='SPY Intraday Chart',
        xaxis_title='Time',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        height=600,
        hovermode='x unified'
    )
    
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

