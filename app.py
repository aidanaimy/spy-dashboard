"""
Main Streamlit app for SPY small-DTE trading dashboard.
"""

import os
from datetime import datetime, timedelta, time, date
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import textwrap
from streamlit_autorefresh import st_autorefresh

# Try Alpaca first, fallback to yfinance
try:
    from data.alpaca_client import get_daily_data, get_intraday_data, get_today_data
except (ImportError, AttributeError):
    from data.yfinance_client import get_daily_data, get_intraday_data, get_today_data

# Import logic modules
try:
    from logic.regime import analyze_regime
    from logic.intraday import analyze_intraday
    from logic.signals import generate_signal
    from logic.iv import fetch_iv_context
    from logic.options import get_atm_strike
except ImportError as e:
    st.error(f"Error importing logic modules: {e}")
    raise
from utils.plots import plot_intraday_candlestick, plot_equity_curve
from utils.journal import (
    load_journal, save_trade, get_today_trades, get_journal_stats, delete_trade
)
# Add a comment to trigger redeploy.
from backtest.backtest_engine import BacktestEngine
from logic.eod_tracker import get_tracker
from logic.eod_summary import send_eod_summary, should_send_eod_summary
import core.config as config

# Page config
st.set_page_config(
    page_title="SPY Trading Dashboard - Main Application",
    page_icon="📈",
    layout="wide"
)

# Global styling
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg-dark: #060b11;
            --panel-dark: #0f1724;
            --panel-light: #162132;
            --text-primary: #f2f5f9;
            --text-secondary: #8ea0bc;
            --accent-green: #2bd47d;
            --accent-red: #ff5f6d;
            --accent-yellow: #f7b500;
            --border-color: #1f2a3c;
            --shadow-soft: 0 8px 24px rgba(0, 0, 0, 0.35);
        }

        html, body, [class*="css"]  {
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: var(--text-primary);
            background-color: var(--bg-dark);
        }

        /* Override default Streamlit typography */
        .stMarkdown, .stText, .stNumberInput, .stSelectbox, .stButton, .stDateInput, .stTimeInput,
        .stDataFrame, .stTable, .stMetric, .stAlert, .stRadio, .stCheckbox, .stSlider,
        .st-expander, .stForm, .stPlotlyChart, .stSubheader, .stHeader {
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        .stats-group {
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding-bottom: 1rem;
        }

        .stats-group h5 {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
            margin-bottom: 0.6rem;
            font-weight: 700;
        }
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary) !important;
            letter-spacing: 0.02em;
        }

        .dashboard-section {
            padding: 1.5rem;
            background: var(--panel-light);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-soft);
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
        }

        .dashboard-section h4 {
            margin: 0 0 1rem 0;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .card-strip {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }
        
        .card-strip.two-columns {
            grid-template-columns: repeat(2, 1fr);
        }

        @media (max-width: 1400px) {
            .card-strip {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 700px) {
            .card-strip {
                grid-template-columns: 1fr;
            }
        }

        .info-card {
            background: var(--panel-light);
            border-radius: 12px;
            padding: 1.5rem 1.25rem 1.25rem 1.25rem;
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            height: 100%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            width: 100%;
        }

        .stats-panel {
            background: var(--panel-light);
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-soft);
            height: 100%;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            position: relative;
            overflow: hidden;
        }

        .info-card h4 {
            margin: 0 0 0.75rem 0;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .info-card .primary-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--text-primary);
            line-height: 1.2;
            margin-bottom: 0.25rem;
            letter-spacing: -0.02em;
        }

        .info-card p {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
            line-height: 1.4;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.6rem;
            margin-top: 0.4rem;
            margin-bottom: 0;
        }
        
        .info-card p:last-child {
            margin-top: 1.25rem;
            margin-bottom: 0;
        }

        .metric-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 0.6rem;
        }

        .metric-card .label {
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.2rem;
        }

        .metric-card .value {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-primary);
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .permission-bar {
            border-radius: 8px;
            padding: 1rem;
            color: #000;
            font-weight: 800;
            text-align: center;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .rationale-content {
            color: var(--text-primary);
            font-size: 0.9rem;
            line-height: 1.6;
        }
        
        .rationale-content ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .rationale-content li {
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .rationale-content li:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }
        
        /* Remove default Streamlit spacing */
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem;
            max-width: 100%;
        }
        
        /* Remove spacing around title */
        .main .block-container > div:first-child {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        
        .stMarkdown {
            margin-bottom: 0 !important;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: var(--panel-dark);
            border-right: 1px solid var(--border-color);
        }
        
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] .stText,
        [data-testid="stSidebar"] label {
            color: var(--text-secondary) !important;
        }
        
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: var(--text-primary) !important;
        }
        
        /* Sidebar Buttons */
        [data-testid="stSidebar"] .stButton button {
            background-color: var(--panel-light);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }
        
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: var(--accent-green);
            color: #000;
            border-color: var(--accent-green);
        }
        
        /* Sidebar Inputs */
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
        
        [data-testid="stSidebar"] .stCheckbox span {
            color: var(--text-secondary);
        }
        
        /* Separator */
        [data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.1);
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize session state
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = config.AUTO_REFRESH_ENABLED
if 'last_refresh_counter' not in st.session_state:
    st.session_state.last_refresh_counter = -1


def get_status_color(status: str) -> str:
    """Get color for 0DTE status badge."""
    colors = {
        'AVOID': '#FF4444',      # Red
        'CAUTION': '#FFAA00',    # Yellow/Orange
        'FAVORABLE': '#00AA00'   # Green
    }
    return colors.get(status, '#888888')


def build_info_card(title: str, icon: str, body_html: str, accent: str = "#2E7BFF") -> str:
    """Return standardized HTML for regime/stat cards."""

    return f'<div class="info-card" style="border-top: 4px solid {accent};"><h4>{icon} {title}</h4><div>{body_html}</div></div>'


def confidence_class(level: str) -> str:
    """Map confidence level to color."""
    mapping = {
        "HIGH": "background: rgba(43,212,125,0.2); color: var(--accent-green); border: 1px solid rgba(43,212,125,0.4);",
        "MEDIUM": "background: rgba(247,181,0,0.15); color: var(--accent-yellow); border: 1px solid rgba(247,181,0,0.4);",
        "LOW": "background: rgba(255,95,109,0.15); color: var(--accent-red); border: 1px solid rgba(255,95,109,0.4);"
    }
    return mapping.get(level, "background: rgba(255,255,255,0.08); color: #fff; border: 1px solid rgba(255,255,255,0.1);")


def get_discord_webhook_url() -> str:
    """Return Discord webhook URL from secrets or environment."""
    try:
        if "DISCORD_WEBHOOK_URL" in st.secrets:
            return st.secrets["DISCORD_WEBHOOK_URL"]
    except Exception:
        # Secrets file doesn't exist or can't be read
        pass
    return os.getenv("DISCORD_WEBHOOK_URL", "")


def send_discord_notification(message: str = None, embed: Dict = None) -> None:
    """Post a message to Discord if webhook is configured.
    
    Args:
        message: Plain text message (for @everyone pings)
        embed: Discord embed object for rich formatting
    """
    url = get_discord_webhook_url()
    if not url:
        return
    try:
        payload = {}
        if message:
            payload["content"] = message
        if embed:
            payload["embeds"] = [embed]
        requests.post(url, json=payload, timeout=5)
    except Exception as exc:
        print(f"Discord notification failed: {exc}")


@st.cache_resource
def get_signal_cache() -> Dict[str, Dict]:
    """Cache for tracking last sent signals with timestamps."""
    return {}


def maybe_notify_signal(signal: Dict[str, str], regime: Dict, intraday: Dict,
                        iv_context: Dict, current_time: datetime,
                        market_phase: Dict, ticker: str = "SPY") -> None:
    """Send Discord alert when signal direction/confidence changes."""
    direction = signal.get("direction", "NONE")
    confidence = signal.get("confidence", "LOW")
    permission = regime.get("0dte_status")
    is_open = market_phase.get("is_open", False)
    
    # Include ticker in snapshot to track signals per ticker
    snapshot = f"{ticker}:{direction}:{confidence}"

    cache = get_signal_cache()
    
    # Check if we've sent this exact signal before
    ticker_cache = cache.get(ticker, {})
    last_snapshot = ticker_cache.get("snapshot")
    last_timestamp = ticker_cache.get("timestamp")
    
    # Deduplication: Skip if same signal
    if snapshot == last_snapshot:
        return
    
    # Time-based cooldown: Skip if less than 15 minutes since last notification
    if last_timestamp:
        time_since_last = (current_time - last_timestamp).total_seconds() / 60
        if time_since_last < 15:
            return  # Cooldown active, skip notification
    
    # Update cache with new snapshot (will be finalized after filters pass)
    # Note: We update here to prevent rapid checks, but only send if filters pass

    # === FILTER: Only send Discord for HIGH quality signals ===
    # Multi-ticker expansion: Only post premium setups to avoid spam
    # Requirements:
    # 1. HIGH confidence (best setups only)
    # 2. FAVORABLE permission (volatile, trending days)
    # 3. Market is open (not blocked period)
    
    if confidence != "HIGH":
        return  # Skip MEDIUM and LOW confidence
    
    # Allow FAVORABLE and CAUTION (for Awareness), skip AVOID
    if permission == "AVOID":
        return
        
    if not is_open:
        return  # Skip blocked trading periods
    
    # 4. Circuit breaker is active (global file-based check)
    circuit_breaker_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "circuit_breaker_status.json")
    if os.path.exists(circuit_breaker_file):
        try:
            import json
            with open(circuit_breaker_file, 'r') as f:
                data = json.load(f)
                file_date = datetime.fromisoformat(data['date']).date()
                current_date = current_time.date()
                if file_date == current_date:
                    # Circuit breaker is active for today, suppress all signals
                    return
        except Exception:
            pass

    # === Build Discord Embed ===
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S ET")
    reason = signal.get("reason", "")
    price = intraday.get("price", 0)
    vwap = intraday.get("vwap", 0)
    micro_trend = intraday.get("micro_trend", "Neutral")
    iv_summary = iv_context.get("atm_iv")
    vix_level = iv_context.get("vix_level")
    trend = regime.get("trend", "Neutral")

    price_str = f"${price:.2f}" if price is not None else "n/a"
    iv_str = f"{iv_summary:.2f}%" if iv_summary is not None else "n/a"
    vix_str = f"{vix_level:.2f}" if vix_level is not None else "n/a"
    vwap_status = "above" if price > vwap else "below"
    
    # === Determine actionability ===
    # HIGH + FAVORABLE = Actionable
    # HIGH + CAUTION = Awareness Only
    is_actionable = (confidence == "HIGH" and permission == "FAVORABLE")
    
    # === Color coding (Discord embed colors are hex integers) ===
    if is_actionable:
        if direction == "CALL":
            color = 0x00ff88  # Bright green for actionable CALL
        else:
            color = 0xff5555  # Bright red for actionable PUT
    else:
        # Non-actionable signals (awareness only)
        if direction == "CALL":
            color = 0xffaa00  # Yellow/amber for CAUTION CALL
        else:
            color = 0xff9966  # Orange for CAUTION PUT
    
    # === Actionability badge ===
    if is_actionable:
        actionability_badge = "🎯 **ACTIONABLE SIGNAL**"
        ping_message = "@everyone 🚨 **HIGH + FAVORABLE SIGNAL DETECTED**"
    elif permission == "CAUTION":
        actionability_badge = "⚠️ **AWARENESS ONLY** (High Quality but Caution Day)"
        ping_message = None  # No @everyone ping
    else:
        actionability_badge = "ℹ️ **AWARENESS ONLY**"
        ping_message = None
    
    # === Option contract suggestion ===
    contract_suggestion = ""
    
    if price is not None and price > 0:
        from logic.options import get_atm_strike
        option_type = "CALL" if direction == "CALL" else "PUT"
        strike = int(get_atm_strike(price, option_type))
        contract_suggestion = f"{ticker} {strike}{option_type[0]} (0DTE)"
    
    # === Build embed object ===
    embed = {
        "title": f"{ticker} {direction} Signal ({confidence})",
        "description": f"{actionability_badge}\n\n**The Setup:**\nMarket showing **{direction}** bias. Daily trend is **{trend}** and micro-trend is **{micro_trend}**. Price ({price_str}) trading **{vwap_status}** VWAP.",
        "color": color,
        "fields": [
            {
                "name": "📋 Signal Details",
                "value": f"**Ticker:** {ticker}\n**Direction:** {direction}\n**Confidence:** {confidence}\n**0DTE Status:** {permission}\n**Session:** {market_phase.get('label', 'Unknown')}",
                "inline": True
            },
            {
                "name": "📊 Market Context",
                "value": f"**ATM IV:** {iv_str}\n**VIX:** {vix_str}\n**Price:** {price_str}\n**VWAP:** ${vwap:.2f}",
                "inline": True
            }
        ],
        "footer": {
            "text": timestamp
        }
    }
    
    # Add contract suggestion field
    if contract_suggestion:
        contract_field = {
            "name": "👉 Suggested Contract",
            "value": f"**{contract_suggestion}**",
            "inline": False
        }
        embed["fields"].append(contract_field)
    
    # Add rationale field
    rationale_field = {
        "name": "💡 Rationale",
        "value": reason[:1024] if len(reason) <= 1024 else reason[:1021] + "...",  # Discord field limit
        "inline": False
    }
    embed["fields"].append(rationale_field)
    
    # Send to Discord
    send_discord_notification(message=ping_message, embed=embed)
    
    # Update cache with timestamp after successful send
    cache[ticker] = {
        "snapshot": snapshot,
        "timestamp": current_time
    }


def get_eod_status() -> Dict:
    """Track if EOD report has been sent for today using file-based persistence."""
    status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "eod_summary_status.json")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    
    # Read existing status
    if os.path.exists(status_file):
        try:
            import json
            with open(status_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    
    return {"sent": False, "date": None}


def update_eod_status(sent: bool, date: str):
    """Update EOD status file."""
    status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "eod_summary_status.json")
    import json
    with open(status_file, 'w') as f:
        json.dump({"sent": sent, "date": date}, f)


def check_and_send_eod_summary(current_time: datetime, force: bool = False) -> None:
    """
    Check if it's time to send EOD summary and send it if not already sent.
    Aggregates performance for SPY and IWM.
    """
    # 1. Check time (e.g., after 4:05 PM ET)
    market_close = current_time.replace(hour=16, minute=5, second=0, microsecond=0)
    if not force and current_time < market_close:
        return

    # 2. Check if already sent today (file-based, works across all sessions)
    status = get_eod_status()
    today = current_time.date().isoformat()
    
    if status.get("sent") and status.get("date") == today:
        return
        
    # 3. Generate Report
    print("📝 Generating EOD Summary Report...")
    
    tickers = ["SPY", "IWM"]
    fields = []
    
    for ticker in tickers:
        try:
            # Fetch data
            daily_df = get_cached_daily_data(ticker, config.DAILY_LOOKBACK_DAYS)
            intraday_df = get_cached_intraday_data(
                ticker, 
                config.INTRADAY_INTERVAL, 
                start_date=current_time.replace(hour=9, minute=30),
                end_date=current_time
            )
            
            if daily_df.empty or intraday_df.empty:
                continue
            
            # Filter to market hours only (9:30 AM - 4:00 PM ET) FIRST
            from datetime import time as dt_time
            intraday_df['time_only'] = intraday_df.index.time
            market_hours_df = intraday_df[
                (intraday_df['time_only'] >= dt_time(9, 30)) & 
                (intraday_df['time_only'] <= dt_time(16, 0))
            ].copy()
            
            if market_hours_df.empty:
                print(f"No market hours data for {ticker}, skipping...")
                continue
            
            # Get today's data (use full intraday for range, market hours for open/close)
            today_data = {
                'yesterday_close': daily_df.iloc[-2]['Close'] if len(daily_df) > 1 else daily_df.iloc[-1]['Close'],
                'today_open': market_hours_df['Open'].iloc[0],  # 9:30 AM open
                'today_high': intraday_df['High'].max(),
                'today_low': intraday_df['Low'].min(),
            }
            
            # Calculate stats - use daily open (official opening auction price)
            # The intraday first bar's open can differ from the official market open
            close_price = market_hours_df['Close'].iloc[-1]
            
            # Get today's official open from daily data (last row)
            open_price = daily_df.iloc[-1]['Open']
            
            # Debug: Log the actual prices
            intraday_open = market_hours_df['Open'].iloc[0]
            open_time = market_hours_df.index[0]
            print(f"📊 {ticker} - Daily open: ${open_price:.2f}, Intraday first bar open: ${intraday_open:.2f}, Close: ${close_price:.2f}")
            
            pct_change = ((close_price - open_price) / open_price) * 100
            dollar_change = close_price - open_price
            
            # Range calculation
            range_val = today_data['today_high'] - today_data['today_low']
            range_pct = (range_val / open_price) * 100
            range_threshold = config.RANGE_HIGH_THRESHOLD * 100
            range_status = "✅" if range_pct > range_threshold else "⚠️"
            
            # Volume
            volume = market_hours_df['Volume'].sum()  # Use market hours volume
            volume_str = f"{volume/1e6:.1f}M" if volume > 1e6 else f"{volume/1e3:.0f}K"
            
            # Determine trend
            from logic.regime import calculate_moving_averages, get_trend, get_0dte_permission
            mas = calculate_moving_averages(daily_df)
            trend_info = get_trend(close_price, mas['ma_short'], mas['ma_long'])
            trend = trend_info.get('trend', 'Neutral')
            
            # Get 0DTE permission
            from logic.regime import calculate_gap, calculate_range
            gap_info = calculate_gap(today_data['yesterday_close'], today_data['today_open'])
            range_info = calculate_range(today_data['today_open'], today_data['today_high'], today_data['today_low'])
            
            # Get VIX and IV - use file-based cache of last known values
            iv_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"iv_cache_{ticker}_{today}.json")
            vix_level = 0
            atm_iv = 0
            
            # Try to read from cache file first
            if os.path.exists(iv_cache_file):
                try:
                    import json
                    with open(iv_cache_file, 'r') as f:
                        cached_iv = json.load(f)
                        vix_level = cached_iv.get('vix_level', 0)
                        atm_iv = cached_iv.get('atm_iv', 0)
                        print(f"✅ Using cached IV for {ticker}: VIX={vix_level:.1f}, ATM IV={atm_iv:.1f}%")
                except Exception as e:
                    print(f"⚠️ Error reading IV cache for {ticker}: {e}")
            
            # If no cache or cache is empty, try to fetch fresh
            if vix_level == 0 or atm_iv == 0:
                try:
                    from data.iv_fetcher import get_cached_iv_context
                    iv_context = get_cached_iv_context(ticker, close_price)
                    vix_level = iv_context.get('vix_level', 0)
                    atm_iv = iv_context.get('atm_iv', 0)
                    
                    if vix_level > 0 and atm_iv > 0:
                        print(f"✅ Fetched fresh IV for {ticker}: VIX={vix_level:.1f}, ATM IV={atm_iv:.1f}%")
                    else:
                        print(f"⚠️ No IV data available for {ticker} (after hours?)")
                        
                except Exception as e:
                    print(f"❌ Error fetching IV for {ticker}: {e}")
            
            permission = get_0dte_permission(
                trend_info['trend'],
                gap_info['gap_pct'],
                range_info['range_pct'],
                vix_level if vix_level > 0 else None  # Pass None if VIX unavailable
            )
            
            # Format emoji
            change_emoji = "🟢" if pct_change > 0 else "🔴" if pct_change < 0 else "⚪"
            permission_emoji = "✅" if permission['status'] == "FAVORABLE" else "⚠️" if permission['status'] == "CAUTION" else "🚫"
            
            # Build detailed field
            field_value = (
                f"**Open:** ${open_price:.2f} → **Close:** ${close_price:.2f}\n"
                f"**Change:** {change_emoji} ${dollar_change:+.2f} ({pct_change:+.2f}%)\n"
                f"**Range:** ${today_data['today_low']:.2f} - ${today_data['today_high']:.2f} ({range_pct:.2f}% {range_status})\n"
                f"**Volume:** {volume_str}\n"
                f"**0DTE Permission:** {permission['status']} {permission_emoji}\n"
                f"**VIX:** {vix_level:.1f}\n"
                f"**ATM IV:** {atm_iv:.1f}%"
            )
            
            fields.append({
                "name": f"📈 {ticker} Performance",
                "value": field_value,
                "inline": False
            })
            
        except Exception as e:
            print(f"Error generating EOD stats for {ticker}: {e}")
            
    if not fields:
        return

    # 4. Build Embed
    embed = {
        "title": f"🏁 End of Day Summary - {today}",
        "description": "Daily performance wrap-up for tracked tickers.",
        "color": 0x2b2d31,  # Dark grey
        "fields": fields,
        "footer": {
            "text": "TradeV3.5 Automated Report"
        }
    }
    
    
    # 5. Send and Update Status
    send_discord_notification(embed=embed)
    update_eod_status(sent=True, date=today)
    print("✅ EOD Summary sent!")


def get_market_close_time(target_date: date) -> time:
    """
    Returns the market close time for a given date.
    Handles early close days (1:00 PM ET) like Black Friday, Christmas Eve, etc.
    
    Args:
        target_date: date object to check
    
    Returns:
        time object (13:00 for early close, 16:00 for normal)
    """
    from datetime import time
    
    # Early close days (1:00 PM ET)
    # Day after Thanksgiving (Black Friday) - Friday after 4th Thursday of November
    if target_date.month == 11 and target_date.weekday() == 4 and 23 <= target_date.day <= 29:
        return time(13, 0)
    
    # Day before Independence Day (July 3rd if weekday)
    if target_date.month == 7 and target_date.day == 3 and target_date.weekday() < 5:
        return time(13, 0)
    
    # Christmas Eve (Dec 24 if weekday)
    if target_date.month == 12 and target_date.day == 24 and target_date.weekday() < 5:
        return time(13, 0)
    
    # Normal close
    return time(16, 0)


def get_market_phase(current_time: datetime) -> Dict[str, Optional[str]]:
    """Return session label and whether regular trading is active."""
    et_time = current_time.astimezone(ZoneInfo("America/New_York"))
    
    # Check for weekend (5=Saturday, 6=Sunday)
    if et_time.weekday() >= 5:
        return {"label": "Weekend", "is_open": False}

    minutes = et_time.hour * 60 + et_time.minute

    def within(start_h, start_m, end_h, end_m):
        return (start_h * 60 + start_m) <= minutes < (end_h * 60 + end_m)

    # Parse config times
    def parse_time(t_str):
        h, m = map(int, t_str.split(':'))
        return h * 60 + m

    session_start = parse_time(config.SESSION_START)
    lunch_start = parse_time(config.LUNCH_CHOP_START)
    lunch_end = parse_time(config.LUNCH_CHOP_END)
    wakeup_start = parse_time(config.AFTERNOON_WAKEUP_START)
    wakeup_end = parse_time(config.AFTERNOON_WAKEUP_END)
    power_start = parse_time(config.POWER_HOUR_START)
    block_after = parse_time(config.BLOCK_TRADE_AFTER)
    session_end = parse_time(config.SESSION_END)

    if minutes < session_start:
        return {"label": "Pre-Market", "is_open": False}
    
    # Early Open (First 10 mins)
    if minutes < session_start + 10:
        return {"label": "Early Open (Reduced)", "is_open": True}
        
    # Morning Drive
    if minutes < 10 * 60 + 30: # 10:30
        return {"label": "Morning Drive", "is_open": True}
        
    # Mid-Morning
    if minutes < lunch_start:
        return {"label": "Mid-Morning Trend", "is_open": True}
        
    # Lunch Chop
    if minutes < lunch_end:
        return {"label": "Lunch Chop", "is_open": False}
        
    # Early Afternoon
    if minutes < wakeup_start:
        return {"label": "Early Afternoon", "is_open": True}
        
    # Afternoon Wake-up
    if minutes < wakeup_end:
        return {"label": "Afternoon Wake-up (Reduced)", "is_open": True}
        
    # Power Hour / Breakout
    if minutes < block_after:
        return {"label": "Breakout Window (Boosted)", "is_open": True}
        
    # Late Day (Blocked but Open)
    if minutes < session_end:
        return {"label": "Late Day (Blocked)", "is_open": False}
        
    return {"label": "After Hours", "is_open": False}


def main():
    # Ticker selector at the top
    st.markdown("""
        <div style="padding: 0; margin: 0 0 1rem 0;">
            <h1 style="
                font-size: 2.5rem;
                font-weight: 800;
                margin: 0;
                padding: 0;
                letter-spacing: -0.02em;
                background: linear-gradient(135deg, #f2f5f9 0%, #8ea0bc 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                line-height: 1.1;
            ">Multi-Ticker Trading Dashboard</h1>
            <p style="
                margin: 0.25rem 0 0 0;
                font-size: 0.9rem;
                color: #8ea0bc;
                font-weight: 500;
                letter-spacing: 0.05em;
            ">0DTE OPTIONS SIGNAL SYSTEM v3.5</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Ticker selector (SPY + IWM only - QQQ removed due to negative backtest results)
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        spy_selected = st.button("📈 SPY", use_container_width=True, type="primary" if st.session_state.get('selected_ticker', 'SPY') == 'SPY' else "secondary")
    with col2:
        iwm_selected = st.button("🏭 IWM", use_container_width=True, type="primary" if st.session_state.get('selected_ticker', 'SPY') == 'IWM' else "secondary")
    
    # Update selected ticker based on button clicks
    if spy_selected:
        st.session_state.selected_ticker = 'SPY'
        st.rerun()
    elif iwm_selected:
        st.session_state.selected_ticker = 'IWM'
        st.rerun()
    
    # Get the active ticker (default to SPY)
    active_ticker = st.session_state.get('selected_ticker', 'SPY')
    
    # Auto-refresh control in sidebar
    with st.sidebar:
        st.header("⚙️ Dashboard Settings")
        
        # Check for EOD summary (runs on every refresh)
        current_time = datetime.now(ZoneInfo("America/New_York"))
        check_and_send_eod_summary(current_time)
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox(
            "Auto-refresh (30s)", 
            value=st.session_state.auto_refresh,
            help="Automatically refresh data every 30 seconds"
        )
        st.session_state.auto_refresh = auto_refresh
        
        if st.button("🔄 Refresh Now"):
            # Clear cache and refresh
            get_cached_daily_data.clear()
            get_cached_intraday_data.clear()
            st.rerun()
            
        if st.button("🧹 Clear Cache & Reboot"):
            # Clear Streamlit cache
            st.cache_data.clear()
            st.cache_resource.clear()
            
            # Clear yfinance cache (platformdirs)
            import shutil
            import platformdirs
            try:
                cache_dir = platformdirs.user_cache_dir("py-yfinance")
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                    st.success(f"Cleared yfinance cache at {cache_dir}")
            except Exception as e:
                st.error(f"Failed to clear yfinance cache: {e}")
                
            st.rerun()
        
        # Show last update time in user's local timezone
        if st.session_state.last_update:
            # Get local timezone name
            import time
            local_tz_name = time.tzname[time.daylight]  # e.g., "PST" or "PDT"
            update_time_str = st.session_state.last_update.strftime('%I:%M:%S %p')
            st.caption(f"Last updated: {update_time_str} {local_tz_name}")
        
        
        # Circuit Breaker Controls
        st.markdown("### 🛑 Circuit Breaker")
        
        # File-based circuit breaker for global state (affects dashboard + Discord)
        circuit_breaker_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "circuit_breaker_status.json")
        os.makedirs(os.path.dirname(circuit_breaker_file), exist_ok=True)
        
        # Initialize session state for loss tracking
        if 'daily_losses' not in st.session_state:
            st.session_state.daily_losses = 0
        if 'circuit_breaker_date' not in st.session_state:
            st.session_state.circuit_breaker_date = datetime.now(ZoneInfo("America/New_York")).date()
        
        # Check if circuit breaker file exists and is for today
        current_date = datetime.now(ZoneInfo("America/New_York")).date()
        circuit_breaker_active = False
        
        if os.path.exists(circuit_breaker_file):
            try:
                import json
                with open(circuit_breaker_file, 'r') as f:
                    data = json.load(f)
                    file_date = datetime.fromisoformat(data['date']).date()
                    if file_date == current_date:
                        circuit_breaker_active = True
                        st.session_state.daily_losses = 2  # Sync session state
                    else:
                        # Old file from previous day, delete it
                        os.remove(circuit_breaker_file)
            except Exception:
                # Corrupted file, delete it
                os.remove(circuit_breaker_file)
        
        # Reset counter if it's a new day
        if st.session_state.circuit_breaker_date != current_date:
            st.session_state.daily_losses = 0
            st.session_state.circuit_breaker_date = current_date
            # Delete old circuit breaker file if it exists
            if os.path.exists(circuit_breaker_file):
                os.remove(circuit_breaker_file)
        
        # Display loss counter
        loss_count = st.session_state.daily_losses
        max_losses = 2
        
        # Color coding
        if loss_count >= max_losses or circuit_breaker_active:
            counter_color = "#ff5f6d"  # Red
            status_text = "🔴 LOCKED"
        elif loss_count == 1:
            counter_color = "#f7b500"  # Yellow
            status_text = "🟡 CAUTION"
        else:
            counter_color = "#2bd47d"  # Green
            status_text = "🟢 ACTIVE"
        
        st.markdown(f"""
        <div style="background: var(--panel-light); border-radius: 8px; padding: 1rem; border: 1px solid var(--border-color); margin-bottom: 1rem;">
            <div style="text-align: center;">
                <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Today's Losses</div>
                <div style="font-size: 2.5rem; font-weight: 800; color: {counter_color}; line-height: 1;">{loss_count} / {max_losses}</div>
                <div style="font-size: 0.85rem; color: {counter_color}; font-weight: 600; margin-top: 0.5rem;">{status_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Loss button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👎 Log Loss", use_container_width=True, disabled=(loss_count >= max_losses)):
                st.session_state.daily_losses += 1
                
                # Send Discord notification and create file if circuit breaker just triggered
                if st.session_state.daily_losses >= 2:
                    # Create circuit breaker file
                    import json
                    with open(circuit_breaker_file, 'w') as f:
                        json.dump({
                            'date': current_date.isoformat(),
                            'timestamp': datetime.now(ZoneInfo("America/New_York")).isoformat()
                        }, f)
                    
                    # Send Discord notification
                    current_time = datetime.now(ZoneInfo("America/New_York"))
                    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S ET")
                    message = (
                        f"@everyone 🛑 **CIRCUIT BREAKER ACTIVATED** 🛑\n\n"
                        f"**Two consecutive losses have been logged.**\n\n"
                        f"Signal generation has been **suspended for the rest of the day**.\n"
                        f"No more trades should be taken today.\n\n"
                        f"Take a break, review your trades, and come back tomorrow.\n\n"
                        f"_{timestamp}_"
                    )
                    send_discord_notification(message)
                
                st.rerun()
        
        with col2:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.daily_losses = 0
                # Delete circuit breaker file
                if os.path.exists(circuit_breaker_file):
                    os.remove(circuit_breaker_file)
                st.rerun()
        
        if loss_count >= max_losses or circuit_breaker_active:
            st.error("⚠️ **Circuit Breaker Tripped!** Stop trading for today.")
        elif loss_count == 1:
            st.warning("⚠️ One more loss will trigger the circuit breaker.")
        
        st.markdown("---")
    
    refresh_counter = 0
    if st.session_state.auto_refresh:
        # Initialize last_refresh_counter if not exists
        if "last_refresh_counter" not in st.session_state:
            st.session_state.last_refresh_counter = -1
        
        # st_autorefresh runs indefinitely as long as:
        # 1. Streamlit app is running
        # 2. Browser tab is open and active
        # 3. No network disconnections
        # It will continue every 30 seconds without timeout/expiration
        refresh_counter = st_autorefresh(
            interval=config.AUTO_REFRESH_INTERVAL, 
            key="data_refresh",
            limit=None  # No limit - runs indefinitely
        )
        
        last_counter = st.session_state.get("last_refresh_counter", -1)
        if refresh_counter > last_counter:
            # Force cache invalidation to ensure fresh data
            get_cached_intraday_data.clear()
            get_cached_daily_data.clear()
            get_cached_iv_context.clear()
            st.session_state.last_refresh_counter = refresh_counter
            st.session_state.last_update = datetime.now()
    
    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Trade Journal", "Backtest"]
    )
    
    if page == "Dashboard":
        render_dashboard(active_ticker)
    elif page == "Trade Journal":
        render_journal()
    elif page == "Backtest":
        render_backtest()


@st.cache_data(ttl=300)  # Cache daily data for 5 minutes (changes once per day)
def get_cached_daily_data(symbol: str, days: int):
    """Cached daily data fetch."""
    return get_daily_data(symbol, days)

@st.cache_data(ttl=60)  # Cache intraday data for 60 seconds
def get_cached_intraday_data(symbol: str, interval: str, days: int = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """Cached intraday data fetch."""
    if start_date is not None and end_date is not None:
        result = get_intraday_data(symbol, interval, start_date=start_date, end_date=end_date)
    else:
        result = get_intraday_data(symbol, interval, days=days if days is not None else 1)
    
    return result


@st.cache_data(ttl=3600)
def get_cached_iv_context(symbol: str, reference_price: float):
    """Cached IV context fetch."""
    return fetch_iv_context(symbol, reference_price)

def render_dashboard(active_ticker: str = 'SPY'):
    """Render main dashboard with regime, intraday, and signals."""
    iv_context = {}

    # Load data with caching
    try:
        with st.spinner("Loading market data..."):
            # Use cached functions
            daily_df = get_cached_daily_data(active_ticker, config.DAILY_LOOKBACK_DAYS)
            
            # Request last 5 days to ensure we get enough history (especially on Mondays)
            # But explicitly set end time to current time in ET to avoid timezone issues
            from zoneinfo import ZoneInfo
            et_tz = ZoneInfo("America/New_York")
            current_time_et = datetime.now(et_tz)
            start_time_et = current_time_et - timedelta(days=5)
            
            intraday_raw = get_cached_intraday_data(
                active_ticker,
                config.INTRADAY_INTERVAL,
                start_date=start_time_et,
                end_date=current_time_et
            )
            
            # Update last refresh time
            st.session_state.last_update = datetime.now()
            
            # Filter to today only
            intraday_raw.index = pd.to_datetime(intraday_raw.index)
            et_tz = ZoneInfo("America/New_York")
            
            # Check if we got any data at all
            if intraday_raw.empty:
                st.error("❌ No intraday data available from data source. This could mean:")
                st.error("1. Alpaca API keys are not configured (check Streamlit secrets)")
                st.error("2. Data source is experiencing issues")
                st.error("3. No trading data available for the requested period")
                st.info("💡 Try refreshing the page in a few minutes, or check your Alpaca API configuration.")
                return
            
            # Build status header with data source and market info
            try:
                from data.alpaca_client import get_alpaca_api
                alpaca_api = get_alpaca_api()
                data_source = "Alpaca" if alpaca_api is not None else "yfinance"
                data_source_color = "#2bd47d" if alpaca_api is not None else "#f7b500"
            except:
                data_source = "yfinance"
                data_source_color = "#f7b500"
            
            # Get current time and market phase
            current_time = datetime.now(et_tz)
            market_phase = get_market_phase(current_time)
            phase_label = market_phase.get('label', 'Unknown')
            phase_is_open = market_phase.get('is_open', False)
            
            # Determine market status based on current time and phase
            # Market is OPEN only during regular trading hours (9:30 AM - 4:00 PM ET)
            current_time_only = current_time.time()
            market_open_time = time(9, 30)
            
            today = datetime.now(et_tz).date()
            market_close_time = get_market_close_time(today)
            
            # Check for weekend (5=Saturday, 6=Sunday)
            is_weekend = current_time.weekday() >= 5
            
            if is_weekend:
                market_status = "CLOSED (Weekend)"
                market_status_color = "#ff5f6d"
            elif market_open_time <= current_time_only < market_close_time:
                market_status = "OPEN"
                market_status_color = "#2bd47d"
            else:
                market_status = "CLOSED"
                market_status_color = "#ff5f6d"
            
            intraday_df = intraday_raw[intraday_raw.index.date == today].copy()
            
            # Filter to regular trading hours only (9:30 AM - 4:00 PM ET)
            # VWAP and EMAs should only use regular session data
            if not intraday_df.empty:
                # Convert index to ET timezone if needed
                # Data from alpaca_client is already timezone-aware in ET
                if intraday_df.index.tz is None:
                    # If somehow timezone-naive, assume it's ET and localize
                    intraday_df.index = pd.to_datetime(intraday_df.index).tz_localize(et_tz)
                elif intraday_df.index.tz != et_tz:
                    # Convert from other timezone to ET
                    intraday_df.index = intraday_df.index.tz_convert(et_tz)
                
                # Filter to regular trading hours (9:30 AM - 4:00 PM ET)
                market_open_time = time(9, 30)
                market_close_time = get_market_close_time(today)
                
                # Get time component of index
                intraday_df['time_only'] = intraday_df.index.time
                
                # Filter to regular hours only
                intraday_df = intraday_df[
                    (intraday_df['time_only'] >= market_open_time) & 
                    (intraday_df['time_only'] <= market_close_time)
                ].copy()
                
                # Drop the temporary time column
                intraday_df = intraday_df.drop(columns=['time_only'], errors='ignore')
            
            # Build modern status header
            if not intraday_raw.empty:
                latest_bar_time = intraday_raw.index[-1]
                latest_bar_str = latest_bar_time.strftime('%H:%M:%S ET')
                current_time_str = current_time.strftime('%H:%M:%S ET')
                
                # Determine if data is stale (>5 min old during market hours)
                time_diff = (current_time - latest_bar_time).total_seconds() / 60
                is_stale = time_diff > 5 and phase_is_open
                data_freshness = "⚠️ STALE" if is_stale else "✓ LIVE"
                freshness_color = "#f7b500" if is_stale else "#2bd47d"
                
                # Build clean status bar
                status_html = f"""
                <div style="background: var(--panel-light); border-radius: 8px; padding: 1rem 1.5rem; margin: 0 0 1.5rem 0; border: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                    <div style="display: flex; gap: 2rem; align-items: center; flex-wrap: wrap;">
                        <div>
                            <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Data Source</div>
                            <div style="font-size: 0.95rem; font-weight: 600; color: {data_source_color};">{data_source}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Data Freshness</div>
                            <div style="font-size: 0.95rem; font-weight: 600; color: {freshness_color};">{data_freshness}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Market Status</div>
                            <div style="font-size: 0.95rem; font-weight: 600; color: {market_status_color};">{market_status}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Session Phase</div>
                            <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary);">{phase_label}</div>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">Latest Bar</div>
                        <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary);">{latest_bar_str}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.15rem;">Bars: {len(intraday_df)}</div>
                    </div>
                </div>
                """
                st.markdown(status_html, unsafe_allow_html=True)
            
            if intraday_df.empty:
                # Fallback: use last available session so dashboard still renders
                last_available_date = intraday_raw.index[-1].date()
                intraday_df = intraday_raw[intraday_raw.index.date == last_available_date].copy()
                
                # Filter fallback data to regular trading hours too
                if not intraday_df.empty:
                    # Convert index to ET timezone if needed
                    # Data from alpaca_client is already timezone-aware in ET
                    if intraday_df.index.tz is None:
                        # If somehow timezone-naive, assume it's ET and localize
                        intraday_df.index = pd.to_datetime(intraday_df.index).tz_localize(et_tz)
                    elif intraday_df.index.tz != et_tz:
                        # Convert from other timezone to ET
                        intraday_df.index = intraday_df.index.tz_convert(et_tz)
                    
                    market_open_time = time(9, 30)
                    market_close_time = get_market_close_time(last_available_date)
                    intraday_df['time_only'] = intraday_df.index.time
                    intraday_df = intraday_df[
                        (intraday_df['time_only'] >= market_open_time) & 
                        (intraday_df['time_only'] <= market_close_time)
                    ].copy()
                    intraday_df = intraday_df.drop(columns=['time_only'], errors='ignore')
                
                if is_weekend:
                    st.info(f"Market Closed (Weekend). Showing last session ({last_available_date}).")
                else:
                    st.info(f"No intraday data for today yet. Showing last available session ({last_available_date}).")
                if intraday_df.empty:
                    st.warning("No intraday data available.")
                    return
            
            today_data = get_today_data(daily_df, intraday_df)

            # Fetch IV context first (needed for regime analysis)
            try:
                iv_context = get_cached_iv_context(active_ticker, intraday_df.iloc[0]['Open'])
                vix_level = iv_context.get('vix_level')
                
                # Save IV to cache file for EOD summary (if we got valid data)
                if vix_level and vix_level > 0:
                    atm_iv = iv_context.get('atm_iv', 0)
                    today_str = current_time.date().isoformat()
                    iv_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"iv_cache_{active_ticker}_{today_str}.json")
                    try:
                        import json
                        with open(iv_cache_file, 'w') as f:
                            json.dump({'vix_level': vix_level, 'atm_iv': atm_iv}, f)
                    except Exception as e:
                        pass  # Silent fail, not critical
                        
            except Exception:
                iv_context = {}
                vix_level = None

            # Analyze regime (now with VIX level)
            regime = analyze_regime(daily_df, today_data, vix_level=vix_level)
            
            # Update EOD tracker with market data
            current_time = datetime.now(ZoneInfo("America/New_York"))
            tracker = get_tracker()
            tracker.reset_if_new_day(current_time.date().isoformat())
            
            # Update market OHLCV
            tracker.update_market_data(
                open_price=today_data['today_open'],
                high=today_data['today_high'],
                low=today_data['today_low'],
                close=today_data['today_close'],
                volume=int(intraday_df['Volume'].sum()) if 'Volume' in intraday_df.columns else 0
            )
            
            # Update VIX data
            if vix_level:
                tracker.update_vix_data(vix_close=vix_level)
            
            # Update IV range
            if iv_context.get('atm_iv'):
                tracker.update_iv_range(iv_context['atm_iv'])
            
            # Update range percentage
            if today_data['today_open'] > 0:
                range_pct = ((today_data['today_high'] - today_data['today_low']) / today_data['today_open']) * 100
                tracker.update_range_pct(range_pct)
            
            # Update 0DTE permission
            tracker.update_dte_permission(regime.get('0dte_status', 'UNKNOWN'))
            
            # Calculate previous day's EMA values for continuity
            previous_ema_fast = None
            previous_ema_slow = None
            
            # Get previous trading day's data (robust logic for Mondays)
            # Find the last available date in intraday_raw that is strictly before today
            available_dates = sorted(list(set(intraday_raw.index.date)))
            past_dates = [d for d in available_dates if d < today]
            
            if past_dates:
                last_trading_day = past_dates[-1]
                yesterday_df = intraday_raw[intraday_raw.index.date == last_trading_day].copy()
            else:
                yesterday_df = pd.DataFrame()
            
            if not yesterday_df.empty:
                # Filter yesterday's data to regular trading hours
                # Convert index to ET timezone if needed
                # Data from alpaca_client is already timezone-aware in ET
                if yesterday_df.index.tz is None:
                    # If somehow timezone-naive, assume it's ET and localize
                    yesterday_df.index = pd.to_datetime(yesterday_df.index).tz_localize(et_tz)
                elif yesterday_df.index.tz != et_tz:
                    # Convert from other timezone to ET
                    yesterday_df.index = yesterday_df.index.tz_convert(et_tz)
                
                market_open_time = time(9, 30)
                market_close_time = get_market_close_time(last_trading_day)
                yesterday_df['time_only'] = yesterday_df.index.time
                yesterday_df = yesterday_df[
                    (yesterday_df['time_only'] >= market_open_time) & 
                    (yesterday_df['time_only'] <= market_close_time)
                ].copy()
                yesterday_df = yesterday_df.drop(columns=['time_only'], errors='ignore')
                
                if not yesterday_df.empty:
                    yesterday_df_sorted = yesterday_df.sort_index()
                    # Calculate yesterday's EMAs to get the last values
                    from logic.intraday import calculate_ema
                    yesterday_ema_fast = calculate_ema(yesterday_df_sorted, config.EMA_FAST)
                    yesterday_ema_slow = calculate_ema(yesterday_df_sorted, config.EMA_SLOW)
                    
                    if not yesterday_ema_fast.empty:
                        last_fast = yesterday_ema_fast.iloc[-1]
                        if pd.notna(last_fast):
                            previous_ema_fast = float(last_fast)
                    if not yesterday_ema_slow.empty:
                        last_slow = yesterday_ema_slow.iloc[-1]
                        if pd.notna(last_slow):
                            previous_ema_slow = float(last_slow)
            
            # Analyze intraday with previous day's EMA values for continuity
            intraday_analysis = analyze_intraday(intraday_df, previous_ema_fast, previous_ema_slow)
            
            # Generate signal (with time filtering and chop detection)
            current_time = datetime.now(ZoneInfo("America/New_York"))
            market_phase = get_market_phase(current_time)

            # Check for Discord notification
            signal = generate_signal(
                regime, 
                intraday_analysis, 
                current_time=current_time,
                intraday_df=intraday_df,
                iv_context=iv_context,
                market_phase=market_phase
            )

            # Check for Discord notification
            maybe_notify_signal(
                signal=signal,
                regime=regime,
                intraday=intraday_analysis,
                iv_context=iv_context,
                current_time=current_time, # Assuming current_time_et should be current_time
                market_phase=market_phase,
                ticker=active_ticker
            )
            
            # Track signal for EOD summary (only if signal was generated)
            if signal.get('direction') != 'NONE':
                tracker = get_tracker()
                tracker.reset_if_new_day(current_time.date().isoformat())
                tracker.log_signal(
                    time=current_time.strftime("%H:%M"),
                    direction=signal.get('direction', 'NONE'),
                    confidence=signal.get('confidence', 'LOW'),
                    permission=regime.get('0dte_status', 'UNKNOWN'),
                    session=market_phase.get('label', 'Unknown'),
                    reason=signal.get('reason', '')
                )
            
            # Check if it's 4 PM ET and send EOD summary (once per day)
            if current_time.hour == 16 and current_time.minute < 5:  # 4:00-4:05 PM window
                today_str = current_time.date().isoformat()
                tracker = get_tracker()
                
                # Check persistent tracker instead of session state to prevent duplicates across sessions
                if not tracker.was_summary_sent(today_str):
                    try:
                        send_eod_summary()
                        tracker.mark_summary_sent(today_str)
                        st.success("📊 EOD Summary sent to Discord!")
                    except Exception as e:
                        st.warning(f"⚠️ Failed to send EOD summary: {e}")
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.exception(e)
        return
    
    # ========== TODAY'S REGIME HEADER ==========
    # Format date for display (e.g., "Fri, Nov 28")
    display_date = intraday_df.index[-1].strftime("%a, %b %d")
    
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
            <h2 style="
                font-size: 1.5rem;
                font-weight: 700;
                margin: 0;
                padding: 0;
                letter-spacing: -0.01em;
            ">Regime Analysis ({display_date})</h2>
        </div>
    """, unsafe_allow_html=True)
    
    trend_color = "#2bd47d" if regime['trend'] == "Bullish" else "#ff5f6d" if regime['trend'] == "Bearish" else "#f7b500"
    regime_cards = []
    
    # Calculate distance from MAs for additional context
    dist_from_20d = ((regime['latest_close'] - regime['ma_short']) / regime['ma_short']) * 100
    dist_from_50d = ((regime['latest_close'] - regime['ma_long']) / regime['ma_long']) * 100 if regime['ma_long'] > 0 else 0
    
    # Calculate daily price change
    yesterday_close = today_data['yesterday_close']
    price_change = regime['latest_close'] - yesterday_close
    price_change_pct = (price_change / yesterday_close) * 100 if yesterday_close > 0 else 0
    price_change_color = "#2bd47d" if price_change >= 0 else "#ff5f6d"
    
    # Generate trend summary
    def describe_trend(trend, dist_20d, dist_50d):
        if trend == "Bullish":
            strength = "strong" if dist_20d > 2 else "moderate" if dist_20d > 0.5 else "weak"
            return f"<p><strong>Bullish trend:</strong> SPY trading {strength}ly above key moving averages. Price momentum favors upside continuation.</p>"
        elif trend == "Bearish":
            strength = "strong" if dist_20d < -2 else "moderate" if dist_20d < -0.5 else "weak"
            return f"<p><strong>Bearish trend:</strong> SPY trading {strength}ly below key moving averages. Price momentum favors downside continuation.</p>"
        else:
            return f"<p><strong>Mixed trend:</strong> SPY trading between key moving averages. Direction unclear; wait for clearer signal.</p>"
    
    trend_summary = describe_trend(regime['trend'], dist_from_20d, dist_from_50d)
    
    # Get EMA 200 from intraday analysis
    ema_200 = intraday_analysis.get('ema_trend', 0)
    ema_200_status = "Above" if regime['latest_close'] > ema_200 and ema_200 > 0 else "Below" if ema_200 > 0 else "N/A"
    ema_200_color = "#2bd47d" if ema_200_status == "Above" else "#ff5f6d" if ema_200_status == "Below" else "#8ea0bc"
    ema_200_arrow = "↑" if ema_200_status == "Above" else "↓" if ema_200_status == "Below" else ""
    
    trend_body = f"""<div><div class="primary-value" style="color:{trend_color}">{regime['trend']}</div><p>{regime['trend_description']}</p></div><div class="metric-grid"><div class="metric-card"><div class="label">Latest Close</div><div class="value">${regime['latest_close']:.2f} <span style="color:{price_change_color};">({price_change_pct:+.2f}%)</span></div></div><div class="metric-card"><div class="label">200 EMA</div><div class="value">${ema_200:.2f} <span style="color:{ema_200_color}; font-weight: 700;">{ema_200_arrow}</span></div></div><div class="metric-card"><div class="label">20D MA</div><div class="value">${regime['ma_short']:.2f}</div></div><div class="metric-card"><div class="label">50D MA</div><div class="value">${regime['ma_long']:.2f}</div></div></div>{trend_summary}"""
    regime_cards.append(build_info_card("Trend Bias", "📊", trend_body, trend_color))
    
    gap_sign = "+" if regime['gap'] > 0 else ""
    
    # Generate gap & range summary
    def describe_gap_range(gap_pct, range_pct, range_class):
        gap_desc = "gapped up" if gap_pct > 0 else "gapped down" if gap_pct < 0 else "opened flat"
        gap_magnitude = "significantly" if abs(gap_pct) > 0.5 else "moderately" if abs(gap_pct) > 0.2 else "slightly"
        range_desc = "wide" if range_class == "High" else "narrow" if range_class == "Low" else "normal"
        return f"<p><strong>Session context:</strong> Market {gap_desc} {gap_magnitude} at open. Trading in a {range_desc} range, indicating {'high volatility' if range_class == 'High' else 'low volatility' if range_class == 'Low' else 'normal volatility'}.</p>"
    
    gap_summary = describe_gap_range(regime['gap_pct'], regime['range_pct'], regime['range_class'])
    gap_body = f"""<div><div class="primary-value">{gap_sign}{regime['gap_pct']:.2f}% Gap</div><p>Range Class: {regime['range_class']}</p></div><div class="metric-grid"><div class="metric-card"><div class="label">Gap ($)</div><div class="value">${regime['gap']:.2f}</div></div><div class="metric-card"><div class="label">Range %</div><div class="value">{regime['range_pct']:.2f}%</div></div><div class="metric-card" style="grid-column: span 2;"><div class="label">Session Low/High</div><div class="value">${today_data['today_low']:.2f} / ${regime['range'] + today_data['today_low']:.2f}</div></div></div>{gap_summary}"""
    regime_cards.append(build_info_card("Gap &amp; Range", "📏", gap_body, "#8ea0bc"))
    
    # IV context card
    def describe_iv(atm, level, rank, perc):
        if atm is None or level is None:
            return "Volatility context unavailable."
        vibe = "Calm" if (atm < 15 and level < 15) else "Elevated" if (atm > 20 or level > 20) else "Normal"
        detail = []
        if vibe == "Calm":
            detail.append("Market pricing muted moves; expect tighter ranges.")
        elif vibe == "Elevated":
            detail.append("Market pricing larger swings; expect faster directional moves and sharper reversals.")
        else:
            detail.append("Volatility near typical levels.")
        if rank is not None:
            if rank > 0.75:
                detail.append("VIX near yearly highs.")
            elif rank < 0.25:
                detail.append("VIX near yearly lows.")
        if perc is not None:
            perc_val = perc * 100
            if perc_val > 70:
                detail.append("Volatility higher than most of the past year.")
            elif perc_val < 30:
                detail.append("Volatility lower than most of the past year.")
        return f"<p><strong>{vibe} volatility:</strong> {' '.join(detail)}</p>"

    iv_body_parts = []
    
    # Show VIX first (more important)
    vix_level = iv_context.get('vix_level')
    vix_rank = iv_context.get('vix_rank')
    vix_percentile = iv_context.get('vix_percentile')
    vix_change_pct = iv_context.get('vix_change_pct')

    if vix_level is not None:
        # Add VIX change color indicator (green for +, red for -)
        vix_change_color = "#2bd47d" if vix_change_pct and vix_change_pct > 0 else "#ff5f6d" if vix_change_pct and vix_change_pct < 0 else "#8ea0bc"
        vix_change_display = f" <span style='color:{vix_change_color}; font-size: 0.85rem;'>({vix_change_pct:+.2f}%)</span>" if vix_change_pct is not None else ""
        
        iv_body_parts.append(f"<div class='primary-value'>{vix_level:.2f}{vix_change_display}</div><p>VIX Level (avg: 12-20)</p>")
        iv_body_parts.append(f"<div class='metric-grid'><div class='metric-card'><div class='label'>VIX Rank</div><div class='value'>{vix_rank*100:.0f}%</div></div>" if vix_rank is not None else "<div class='metric-grid'>")
        if vix_percentile is not None:
            iv_body_parts.append(f"<div class='metric-card'><div class='label'>VIX Percentile</div><div class='value'>{vix_percentile*100:.0f}%</div></div>")
    else:
        iv_body_parts.append("<p>VIX unavailable</p><div class='metric-grid'>")
    
    # Show ATM IV second
    atm_iv = iv_context.get('atm_iv')
    if atm_iv is not None:
        expiry = iv_context.get('expiry', 'N/A')
        iv_body_parts.append(f"<div class='metric-card'><div class='label'>ATM IV (exp {expiry})</div><div class='value'>{atm_iv:.2f}%</div></div>")
    
    iv_body_parts.append("</div>")

    summary_text = describe_iv(atm_iv, vix_level, vix_rank, vix_percentile)
    iv_body_parts.append(summary_text)

    iv_body = "".join(iv_body_parts)
    regime_cards.append(build_info_card("Volatility Context", "⚡", iv_body, "#8ea0bc"))
    
    status = regime['0dte_status']
    status_color = get_status_color(status)
    
    # Add context metrics for 0DTE Permission
    gap_abs = abs(regime['gap_pct'])
    
    # Generate 0DTE permission summary
    def describe_0dte_permission(status, gap_abs, range_pct):
        if status == "GREEN":
            return f"<p><strong>0DTE outlook:</strong> High volatility day with {range_pct:.2f}% range. Directional 0DTE trades have favorable conditions; expect larger moves and clearer trends.</p>"
        elif status == "RED":
            return f"<p><strong>0DTE outlook:</strong> Small gap ({gap_abs:.2f}%) and low range ({range_pct:.2f}%) suggest choppy conditions. Avoid aggressive 0DTE directional trades; consider neutral strategies or wait for clearer setup.</p>"
        else:
            return f"<p><strong>0DTE outlook:</strong> Mixed conditions with {gap_abs:.2f}% gap and {range_pct:.2f}% range. Use caution with 0DTE trades; wait for confirmation before taking directional positions.</p>"
    
    permission_summary = describe_0dte_permission(status, gap_abs, regime['range_pct'])
    permission_body = f"""<div><div class="permission-bar" style="background:{status_color}; font-size:1.4rem; padding:1.5rem;">{status}</div><p style="text-align:center; margin-bottom:1rem;">{regime['0dte_reason']}</p><div class="metric-grid"><div class="metric-card"><div class="label">Gap Size</div><div class="value">{gap_abs:.2f}%</div></div><div class="metric-card"><div class="label">Range</div><div class="value">{regime['range_pct']:.2f}%</div></div></div>{permission_summary}</div>"""
    regime_cards.append(build_info_card("0DTE Permission", "🚦", permission_body, status_color))
    
    st.markdown(f"<div class='card-strip'>{''.join(regime_cards)}</div>", unsafe_allow_html=True)
    
    
    # ========== INTRADAY SPY PANEL ==========
    st.markdown("""
        <h2 style="
            font-family: 'Inter', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 2rem 0 1rem 0;
            padding: 0;
            letter-spacing: -0.01em;
        ">Intraday SPY Analysis</h2>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([3, 1.3], gap="large")
    
    with col_left:

        fig = plot_intraday_candlestick(
            intraday_df,
            vwap=intraday_analysis.get('vwap_series'),
            ema_fast=intraday_analysis.get('ema_fast_series'),
            ema_slow=intraday_analysis.get('ema_slow_series'),
            ema_trend=intraday_analysis.get('ema_trend_series'),
            current_price=intraday_analysis.get('price'),
            signal_direction=signal.get('direction')
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_right:
        # Build the entire stats panel HTML in one go to ensure proper nesting
        stats_html = []
        stats_html.append("<div class='stats-panel' style='border-top: 4px solid #8ea0bc;'>")
        
        # Overview Group
        stats_html.append("<div class='stats-group'><h5>Overview</h5>")
        stats_html.append(f"""<div class="metric-grid"><div class="metric-card"><div class="label">Current Price</div><div class="value">${intraday_analysis['price']:.2f}</div></div><div class="metric-card"><div class="label">VWAP</div><div class="value">${intraday_analysis['vwap']:.2f}</div></div><div class="metric-card"><div class="label">VWAP Dist</div><div class="value">{intraday_analysis['vwap_distance']:.2f}%</div></div></div>""")
        stats_html.append("</div>")
        
        # Momentum Group
        stats_html.append("<div class='stats-group'><h5>Momentum</h5>")
        stats_html.append(f"""<div class="metric-grid"><div class="metric-card"><div class="label">1-Bar Return</div><div class="value">{intraday_analysis['return_1']:.2f}%</div></div><div class="metric-card"><div class="label">5-Bar Return</div><div class="value">{intraday_analysis['return_5']:.2f}%</div></div><div class="metric-card"><div class="label">Realized Vol</div><div class="value">{intraday_analysis['realized_vol']:.2f}%</div></div></div>""")
        stats_html.append("</div>")
        
        # Micro Trend Group
        micro_trend = intraday_analysis['micro_trend']
        trend_emoji = "📈" if micro_trend == "Up" else "📉" if micro_trend == "Down" else "➡️"
        trend_color = "#2bd47d" if micro_trend == "Up" else "#ff5f6d" if micro_trend == "Down" else "#8ea0bc"
        
        stats_html.append("<div class='stats-group' style='border-bottom:none; padding-bottom:0;'><h5>Micro Trend</h5>")
        
        # Get EMA values for context
        ema_fast_val = intraday_analysis.get('ema_fast', 0)
        ema_slow_val = intraday_analysis.get('ema_slow', 0)
        price = intraday_analysis.get('price', 0)
        
        # Determine EMA relationship
        if ema_fast_val > ema_slow_val:
            ema_status = f"EMA {config.EMA_FAST} > EMA {config.EMA_SLOW}"
        elif ema_fast_val < ema_slow_val:
            ema_status = f"EMA {config.EMA_FAST} < EMA {config.EMA_SLOW}"
        else:
            ema_status = f"EMA {config.EMA_FAST} ≈ EMA {config.EMA_SLOW}"
        
        stats_html.append(f"""
            <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
                <div style="font-size:2rem;">{trend_emoji}</div>
                <div>
                    <div style="font-size:1.5rem; font-weight:800; color:{trend_color};">{micro_trend}</div>
                    <div style="font-size:0.8rem; color:var(--text-secondary);">{ema_status}</div>
                </div>
            </div>
        """)
        stats_html.append("</div>")
        stats_html.append("</div>")
        
        st.markdown("".join(stats_html), unsafe_allow_html=True)
    
    
    # ========== BIAS / SIGNAL BOX ==========
    st.markdown("""
        <h2 style="
            font-family: 'Inter', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 2rem 0 1rem 0;
            padding: 0;
            letter-spacing: -0.01em;
        ">Trading Bias / Signal</h2>
    """, unsafe_allow_html=True)
    
    
    # Check if circuit breaker is tripped (file-based for global state)
    circuit_breaker_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "circuit_breaker_status.json")
    circuit_breaker_tripped = False
    
    if os.path.exists(circuit_breaker_file):
        try:
            import json
            with open(circuit_breaker_file, 'r') as f:
                data = json.load(f)
                file_date = datetime.fromisoformat(data['date']).date()
                current_date = datetime.now(ZoneInfo("America/New_York")).date()
                if file_date == current_date:
                    circuit_breaker_tripped = True
        except Exception:
            pass
    
    if circuit_breaker_tripped:
        # Show lockout message instead of signal
        lockout_html = """
        <div style="background: linear-gradient(135deg, #ff5f6d 0%, #ff3b4a 100%); border-radius: 12px; padding: 3rem 2rem; text-align: center; border: 2px solid #ff5f6d; box-shadow: 0 8px 24px rgba(255, 95, 109, 0.3);">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🛑</div>
            <h2 style="color: #fff; font-size: 1.8rem; font-weight: 800; margin: 0 0 1rem 0; letter-spacing: 0.05em;">CIRCUIT BREAKER ACTIVATED</h2>
            <p style="color: rgba(255,255,255,0.9); font-size: 1.1rem; margin: 0 0 1.5rem 0; line-height: 1.6;">
                You have reached the maximum of <strong>2 consecutive losses</strong> for today.
            </p>
            <p style="color: rgba(255,255,255,0.8); font-size: 0.95rem; margin: 0; line-height: 1.5;">
                Signal generation has been <strong>suspended</strong> to protect your capital.<br>
                Take a break, review your trades, and come back tomorrow.
            </p>
            <div style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.2);">
                <p style="color: rgba(255,255,255,0.7); font-size: 0.85rem; margin: 0;">
                    💡 <em>This rule saved you an average of $1,900 during the April 2025 drawdown.</em>
                </p>
            </div>
        </div>
        """
        st.markdown(lockout_html, unsafe_allow_html=True)
    else:
        # Normal signal display
        signal_direction = signal['direction']
        signal_confidence = signal['confidence']
        
        if signal_direction == "CALL":
            direction_color = "#2bd47d"
            direction_emoji = "🟢"
        elif signal_direction == "PUT":
            direction_color = "#ff5f6d"
            direction_emoji = "🔴"
        else:
            direction_color = "#8ea0bc"
            direction_emoji = "⚪"
        
        session_label = market_phase.get("label", "Unknown") if 'market_phase' in locals() else "Unknown"
        
        # Signal card
        signal_body = f"""
            <div style="text-align:center;">
                <div class="primary-value" style="color:{direction_color}; font-size:2rem; margin-bottom:1.5rem;">{direction_emoji} {signal_direction}</div>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="label">Confidence</div>
                        <div class="value" style="color:{direction_color};">{signal_confidence}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Session</div>
                        <div class="value">{session_label}</div>
                    </div>
                </div>
            </div>
        """
        
        # Rationale card - Check if market is open
        # market_status is defined earlier in the render_dashboard function
        if market_status == "CLOSED":
            # Show clean message during pre-market/after-hours
            if session_label == "Pre-Market":
                rationale_message = "Pre-market session. Signal analysis will resume at 9:45 AM ET."
                rationale_emoji = "🌅"
            elif session_label == "After Hours":
                rationale_message = "After-hours session. Signal analysis paused until next trading day."
                rationale_emoji = "🌙"
            else:
                rationale_message = "Market is currently closed. Signal analysis paused."
                rationale_emoji = "⏸️"
            
            rationale_body = f"""
                <div>
                    <div class="rationale-content" style="text-align:center; padding:2rem 1rem;">
                        <div style="font-size:3rem; margin-bottom:1rem;">{rationale_emoji}</div>
                        <div style="color:var(--text-secondary); font-size:0.95rem; line-height:1.6;">
                            {rationale_message}
                        </div>
                    </div>
                </div>
            """
        else:
            # Market is open - show full rationale
            rationale_body = f"""
                <div>
                    <div class="rationale-content">
                        <ul style="list-style:none; padding:0; margin:0;">
                            <li style="margin-bottom:0.75rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(255,255,255,0.05);">{signal['reason']}</li>
                            <li style="margin-bottom:0.75rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(255,255,255,0.05);">Trend Frame: {regime['trend']}</li>
                            <li style="margin-bottom:0.75rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(255,255,255,0.05);">Micro Trend: {intraday_analysis['micro_trend']} (EMA {config.EMA_FAST}/{config.EMA_SLOW})</li>
                            <li style="margin-bottom:0.75rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(255,255,255,0.05);">Price vs VWAP: {"Above" if intraday_analysis['price'] > intraday_analysis['vwap'] else "Below"}</li>
                            <li style="margin-bottom:0;">5-Bar Return: {intraday_analysis['return_5']:.2f}% | VWAP Dist: {intraday_analysis['vwap_distance']:.2f}%</li>
                        </ul>
                    </div>
                </div>
            """
        
        signal_cards = []
        signal_cards.append(build_info_card("Signal", "🎯", signal_body, direction_color))
        
        # Only show rationale if there is an active signal
        if signal.get('direction', 'NONE') != 'NONE':
            signal_cards.append(build_info_card("Rationale Breakdown", "📋", rationale_body, "#8ea0bc"))
            st.markdown(f"<div class='card-strip two-columns'>{''.join(signal_cards)}</div>", unsafe_allow_html=True)
        else:
            # Single column for just the signal card
            st.markdown(f"<div class='card-strip' style='grid-template-columns: 1fr;'>{''.join(signal_cards)}</div>", unsafe_allow_html=True)


def render_journal():
    """Render trade journal interface."""
    st.header("📝 Trade Journal")
    
    # Journal form
    with st.expander("➕ Log New Trade", expanded=True):
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.markdown("<div class='section-label'>Trade Context</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            trade_date = st.date_input("Date", value=datetime.now().date())
            trade_time = st.time_input("Time", value=datetime.now().time())
        with col2:
            ticker = st.text_input("Ticker", value="SPY 0DTE")
            direction = st.selectbox("Direction", ["Long", "Short"])
            bias_at_time = st.selectbox("Bias at Time", ["CALL", "PUT", "NONE"])
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.markdown("<div class='section-label'>Execution Detail</div>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        
        with col3:
            size = st.number_input("Size (contracts/notional)", min_value=0.0, value=1.0, step=0.1)
            entry_price = st.number_input("Entry Price", min_value=0.0, value=0.0, step=0.01)
        with col4:
            exit_price = st.number_input("Exit Price (optional)", min_value=0.0, value=0.0, step=0.01)
            notes = st.text_area("Notes", value="")
        st.markdown("</div>", unsafe_allow_html=True)
        
        timestamp = datetime.combine(trade_date, trade_time)
        if st.button("Save Trade"):
            try:
                save_trade(
                    timestamp=timestamp,
                    ticker=ticker,
                    direction=direction,
                    bias_at_time=bias_at_time,
                    size=size,
                    entry_price=entry_price,
                    exit_price=exit_price if exit_price > 0 else None,
                    notes=notes
                )
                st.success("Trade saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving trade: {str(e)}")
    
    # Today's trades
    st.subheader("Today's Trades")
    
    try:
        today_trades = get_today_trades()
        
        if today_trades.empty:
            st.info("No trades logged for today.")
        else:
            # Display stats
            stats = get_journal_stats(today_trades)
            
            col1, col2, col3, col4 = st.columns(4)
            st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
            stat_grid = textwrap.dedent(
                f"""
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="label">Total Trades</div>
                        <div class="value">{stats['total_trades']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Total P/L</div>
                        <div class="value">${stats['total_pnl']:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">With System P/L</div>
                        <div class="value">${stats['with_system_pnl']:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Against System P/L</div>
                        <div class="value">${stats['against_system_pnl']:.2f}</div>
                    </div>
                </div>
                """
            )
            st.markdown(stat_grid, unsafe_allow_html=True)
            st.markdown(
                f"<span class='journal-label-with'>With System</span>: {stats['with_system_count']} trades | "
                f"<span class='journal-label-against'>Against System</span>: {stats['against_system_count']} trades",
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Display table with delete functionality
            display_df = today_trades.copy()
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            display_df['with_system'] = display_df['with_system'].map({True: '✅', False: '❌'})
            
            # Add index column for deletion
            display_df['index'] = today_trades.index
            
            trades_html = display_df[['timestamp', 'ticker', 'direction', 'bias_at_time', 
                                      'size', 'entry_price', 'exit_price', 'with_system', 'notes']].to_html(
                classes="styled-table",
                index=False,
                border=0
            )
            st.markdown(trades_html, unsafe_allow_html=True)
            
            # Delete trade section
            st.subheader("Delete Trade")
            with st.expander("🗑️ Delete a Trade", expanded=False):
                all_trades_for_delete = load_journal()
                if not all_trades_for_delete.empty:
                    # Create a list of trade descriptions for selection
                    trade_options = []
                    for idx, row in all_trades_for_delete.iterrows():
                        timestamp = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M')
                        desc = f"{timestamp} - {row['ticker']} {row['direction']} @ ${row['entry_price']:.2f}"
                        trade_options.append((idx, desc))
                    
                    if trade_options:
                        selected_trade = st.selectbox(
                            "Select trade to delete:",
                            options=range(len(trade_options)),
                            format_func=lambda x: trade_options[x][1]
                        )
                        
                        if st.button("🗑️ Delete Selected Trade", type="secondary"):
                            try:
                                # Get the actual index from the dataframe
                                trade_idx = trade_options[selected_trade][0]
                                delete_trade(trade_idx)
                                st.success("Trade deleted successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting trade: {str(e)}")
                else:
                    st.info("No trades to delete.")
    
    except Exception as e:
        st.error(f"Error loading journal: {str(e)}")
    
    # All trades
    st.subheader("All Trades")
    
    try:
        all_trades = load_journal()
        
        if all_trades.empty:
            st.info("No trades in journal.")
        else:
            # Format for display
            display_all = all_trades.copy()
            if 'timestamp' in display_all.columns:
                display_all['timestamp'] = pd.to_datetime(display_all['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            if 'with_system' in display_all.columns:
                display_all['with_system'] = display_all['with_system'].map({True: '✅', False: '❌'})
            
            st.markdown(
                display_all.to_html(classes="styled-table", index=False, border=0),
                unsafe_allow_html=True
            )
    
    except Exception as e:
        st.error(f"Error loading all trades: {str(e)}")


def render_backtest():
    """Render backtest interface with multi-ticker support."""
    st.header("🔬 Backtest Engine")
    
    st.info("Run a backtest using the same signal logic as the dashboard. Select multiple tickers to test a combined portfolio.")
    
    # Ticker selection
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        selected_tickers = st.multiselect(
            "Select Tickers",
            options=["SPY", "IWM"],
            default=["SPY", "IWM"],
            help="Select one or more tickers to backtest. Results will be aggregated."
        )
    
    # Options mode toggle
    use_options = st.checkbox(
        "📊 Use Options Pricing (Black-Scholes)",
        value=False,
        help="If enabled, backtest uses options pricing with Greeks (Delta, Theta, Vega) instead of shares. Uses VIX as IV proxy."
    )
    
    col1, col2 = st.columns(2)
    
    # Initialize default dates in session state if not present
    if 'backtest_start_default' not in st.session_state:
        st.session_state.backtest_start_default = datetime.now().date() - timedelta(days=30)
    if 'backtest_end_default' not in st.session_state:
        st.session_state.backtest_end_default = datetime.now().date()
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=st.session_state.backtest_start_default,
            key="backtest_start_input"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.backtest_end_default,
            key="backtest_end_input"
        )
    
    # Update session state with user selections
    st.session_state.backtest_start_default = start_date
    st.session_state.backtest_end_default = end_date
    
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        run_backtest = st.button("🚀 Run Backtest", type="primary")
    
    with col_btn2:
        if st.button("🧹 Clear Results"):
            if 'backtest_results' in st.session_state:
                del st.session_state.backtest_results
            st.success("Results cleared!")
            st.rerun()
    
    if run_backtest:
        if not selected_tickers:
            st.error("Please select at least one ticker.")
            return
            
        if start_date >= end_date:
            st.error("Start date must be before end date.")
            return
        
        # Clear data caches to ensure fresh data
        get_cached_daily_data.clear()
        get_cached_intraday_data.clear()
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            print(f"🚀 APP DEBUG: Starting backtest with dates: {start_date} to {end_date}, options={use_options}, tickers={selected_tickers}")
            
            all_trades = []
            ticker_results = {}
            
            # Store original symbol to restore later
            original_symbol = config.SYMBOL
            
            for i, ticker in enumerate(selected_tickers):
                status_text.text(f"Running backtest for {ticker} ({i+1}/{len(selected_tickers)})...")
                progress_bar.progress((i) / len(selected_tickers))
                
                # Temporarily override config.SYMBOL
                config.SYMBOL = ticker
                
                # Initialize engine
                engine = BacktestEngine()
                
                # Run backtest
                results = engine.run_backtest(
                    datetime.combine(start_date, datetime.min.time()),
                    datetime.combine(end_date, datetime.max.time()),
                    use_options=use_options
                )
                
                # Process results
                trades_df = results.get('trades', pd.DataFrame())
                if not trades_df.empty:
                    trades_df['ticker'] = ticker
                    all_trades.append(trades_df)
                
                ticker_results[ticker] = {
                    'trades': results.get('num_trades', 0),
                    'win_rate': results.get('win_rate', 0),
                    'net_pnl': results.get('total_pnl', 0.0),
                    'avg_win': results.get('avg_win', 0.0),
                    'avg_loss': results.get('avg_loss', 0.0),
                    'profit_factor': abs(results.get('avg_win', 0) * results.get('win_rate', 0) / (results.get('avg_loss', 1) * (100 - results.get('win_rate', 0)))) if results.get('avg_loss', 0) != 0 else 0
                }
                
                print(f"[{ticker}] Completed: {results.get('num_trades', 0)} trades, ${results.get('total_pnl', 0):.2f}")

            # Restore original symbol
            config.SYMBOL = original_symbol
            
            # Aggregate results
            if all_trades:
                combined_trades = pd.concat(all_trades, ignore_index=True)
                combined_trades = combined_trades.sort_values('entry_time')
                
                total_trades = len(combined_trades)
                wins = combined_trades[combined_trades['pnl'] > 0]
                losses = combined_trades[combined_trades['pnl'] <= 0]
                
                win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
                net_pnl = combined_trades['pnl'].sum()
                avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
                avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
                profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0
                
                aggregate_results = {
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'net_pnl': net_pnl,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor,
                    'trades_df': combined_trades
                }
            else:
                aggregate_results = {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'net_pnl': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'profit_factor': 0.0,
                    'trades_df': pd.DataFrame()
                }
            
            # Store results in session state
            st.session_state.backtest_results = {
                'aggregate': aggregate_results,
                'by_ticker': ticker_results,
                'is_multi_ticker': True
            }
            st.session_state.backtest_start_date = start_date
            st.session_state.backtest_end_date = end_date
            st.session_state.backtest_use_options = use_options
            
            # Clear progress indicators
            progress_bar.progress(100)
            status_text.text("Backtest complete!")
            
            st.success(f"✅ Backtest complete! {aggregate_results['total_trades']} trades, {aggregate_results['win_rate']:.1f}% win rate")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error running backtest: {str(e)}")
            st.exception(e)
            import traceback
            st.code(traceback.format_exc())
            # Ensure config is restored even on error
            config.SYMBOL = original_symbol
    
    # Display results if they exist in session state
    if 'backtest_results' in st.session_state:
        results = st.session_state.backtest_results
        use_options_mode = st.session_state.get('backtest_use_options', False)
        
        # Handle legacy single-ticker results (if any exist in session state from before)
        if not results.get('is_multi_ticker'):
            # Convert legacy format to new format for display
            agg = {
                'total_trades': results.get('num_trades', 0),
                'win_rate': results.get('win_rate', 0),
                'net_pnl': results.get('total_pnl', 0),
                'avg_win': results.get('avg_win', 0),
                'avg_loss': results.get('avg_loss', 0),
                'profit_factor': 0, # Legacy didn't have this easily accessible here
                'trades_df': results.get('trades', pd.DataFrame())
            }
            results = {'aggregate': agg, 'by_ticker': {}, 'is_multi_ticker': False}

        agg = results['aggregate']
        by_ticker = results['by_ticker']
        
        # Show date range and mode
        mode_text = "Options Mode (Black-Scholes)" if use_options_mode else "Shares Mode"
        st.markdown(f"📅 **Backtest Period**: {st.session_state.backtest_start_date} to {st.session_state.backtest_end_date} | **Mode**: {mode_text}")
        
        
        # --- Aggregate Metrics ---
        st.subheader("📊 Aggregate Performance")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Trades", agg['total_trades'])
        m2.metric("Win Rate", f"{agg['win_rate']:.1f}%")
        m3.metric("Net P/L", f"${agg['net_pnl']:.2f}", delta_color="normal")
        m4.metric("Profit Factor", f"{agg['profit_factor']:.2f}")
        m5.metric("Avg Trade", f"${(agg['avg_win'] * (agg['win_rate']/100) + agg['avg_loss'] * (1 - agg['win_rate']/100)):.2f}")
        
        # --- Per-Ticker Breakdown ---
        if by_ticker:
            st.subheader("📈 Ticker Breakdown")
            ticker_data = []
            for t, stats in by_ticker.items():
                ticker_data.append({
                    "Ticker": t,
                    "Trades": stats['trades'],
                    "Win Rate": f"{stats['win_rate']:.1f}%",
                    "Net P/L": f"${stats['net_pnl']:.2f}",
                    "Profit Factor": f"{stats['profit_factor']:.2f}",
                    "Avg Win": f"${stats['avg_win']:.2f}",
                    "Avg Loss": f"${stats['avg_loss']:.2f}"
                })
            st.dataframe(pd.DataFrame(ticker_data), use_container_width=True, hide_index=True)

        # --- Trade List ---
        st.subheader("📝 Trade Log")
        trades_df = agg['trades_df']
        if not trades_df.empty:
            # Format for display
            display_df = trades_df.copy()
            
            # Ensure datetime objects
            display_df['entry_time'] = pd.to_datetime(display_df['entry_time'])
            display_df['exit_time'] = pd.to_datetime(display_df['exit_time'])
            
            # Select columns to display
            base_cols = ['ticker', 'entry_time', 'direction', 'entry_price', 'exit_price', 'pnl', 'exit_reason']
            
            # Add metadata columns if available
            meta_cols = []
            if 'confidence' in display_df.columns:
                meta_cols.append('confidence')
            if '0dte_permission' in display_df.columns:
                meta_cols.append('0dte_permission')
            if 'strike' in display_df.columns:
                meta_cols.append('strike')
            
            # Combine columns
            final_cols = ['ticker'] + ['entry_time', 'direction'] + meta_cols + ['entry_price', 'exit_price', 'pnl', 'exit_reason']
            
            # Handle single ticker case (no ticker column if not multi-ticker)
            if 'ticker' not in display_df.columns:
                final_cols.remove('ticker')
                
            # Filter dataframe
            display_df = display_df[final_cols]
            
            # Apply styling
            def color_pnl(val):
                color = '#00FF00' if val > 0 else '#FF4444'
                return f'color: {color}'

            # Create styled dataframe
            st.dataframe(
                display_df.style.map(color_pnl, subset=['pnl']).format({
                    'entry_time': '{:%Y-%m-%d %H:%M}',
                    'exit_time': '{:%Y-%m-%d %H:%M}',
                    'entry_price': '${:.2f}',
                    'exit_price': '${:.2f}',
                    'pnl': '${:+.2f}',
                    'strike': '${:.2f}'
                }),
                use_container_width=True,
                height=500,
                column_config={
                    "entry_time": st.column_config.DatetimeColumn("Entry", format="MM/DD HH:mm"),
                    "exit_time": st.column_config.DatetimeColumn("Exit", format="MM/DD HH:mm"),
                    "pnl": st.column_config.NumberColumn("P/L", format="$%.2f"),
                    "confidence": st.column_config.TextColumn("Conf"),
                    "0dte_permission": st.column_config.TextColumn("Perm"),
                }
            )
        else:
            st.info("No trades generated in this period.")

if __name__ == "__main__":
    main()


