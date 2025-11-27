"""
Main Streamlit app for SPY small-DTE trading dashboard.
"""

import os
from datetime import datetime, timedelta, time
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
from logic.regime import analyze_regime
from logic.intraday import analyze_intraday
from logic.signals import generate_signal
from logic.iv import fetch_iv_context
from utils.plots import plot_intraday_candlestick, plot_equity_curve
from utils.journal import (
    load_journal, save_trade, get_today_trades, get_journal_stats, delete_trade
)
from backtest.backtest_engine import BacktestEngine
import config

# Page config
st.set_page_config(
    page_title="SPY Trading Dashboard",
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
            padding-bottom: 1.5rem;
        }

        .stats-group h5 {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
            margin-bottom: 1rem;
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
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .info-card {
            flex: 1 1 0;
            min-width: 280px;
            background: var(--panel-light);
            border-radius: 12px;
            padding: 1.25rem;
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .stats-panel {
            background: var(--panel-light);
            border-radius: 12px;
            padding: 1.25rem;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-soft);
            height: 100%;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            position: relative;
            overflow: hidden;
        }

        .info-card h4 {
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
            margin-bottom: 1.2rem;
            line-height: 1.4;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            margin-top: auto;
        }

        .metric-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 0.75rem;
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
        'RED': '#FF4444',
        'YELLOW': '#FFAA00',
        'GREEN': '#00AA00'
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
    if "DISCORD_WEBHOOK_URL" in st.secrets:
        return st.secrets["DISCORD_WEBHOOK_URL"]
    return os.getenv("DISCORD_WEBHOOK_URL", "")


def send_discord_notification(message: str) -> None:
    """Post a message to Discord if webhook is configured."""
    url = get_discord_webhook_url()
    if not url:
        return
    try:
        requests.post(url, json={"content": message}, timeout=5)
    except Exception as exc:
        print(f"Discord notification failed: {exc}")


@st.cache_resource
def get_signal_cache() -> Dict[str, Optional[str]]:
    return {"snapshot": None}


def maybe_notify_signal(signal: Dict[str, str], regime: Dict, intraday: Dict,
                        iv_context: Dict, current_time: datetime,
                        market_phase: Dict) -> None:
    """Send Discord alert when signal direction/confidence changes."""
    direction = signal.get("direction", "NONE")
    confidence = signal.get("confidence", "LOW")
    snapshot = f"{direction}:{confidence}"

    cache = get_signal_cache()
    last_snapshot = cache.get("snapshot")
    if snapshot == last_snapshot:
        return

    cache["snapshot"] = snapshot

    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S ET")
    reason = signal.get("reason", "")
    price = intraday.get("price")
    micro_trend = intraday.get("micro_trend")
    iv_summary = iv_context.get("atm_iv")
    permission = regime.get("0dte_status")

    price_str = f"${price:.2f}" if price is not None else "n/a"
    iv_str = f"{iv_summary:.2f}%" if iv_summary is not None else "n/a"

    message = (
        f"📈 **Signal Update**\n"
        f"- Direction: **{direction}**\n"
        f"- Confidence: **{confidence}**\n"
        f"- 0DTE Permission: {permission}\n"
        f"- Price: {price_str} | Micro trend: {micro_trend}\n"
        f"- ATM IV: {iv_str}\n"
        f"- Reason: {reason}\n"
        f"- Time: {timestamp}"
    )

    send_discord_notification(message)


def get_market_phase(current_time: datetime) -> Dict[str, Optional[str]]:
    """Return session label and whether regular trading is active."""
    et_time = current_time.astimezone(ZoneInfo("America/New_York"))
    minutes = et_time.hour * 60 + et_time.minute

    def within(start_h, start_m, end_h, end_m):
        return (start_h * 60 + start_m) <= minutes < (end_h * 60 + end_m)

    if minutes < 9 * 60 + 30:
        return {"label": "Pre-Market", "is_open": False}
    if within(9, 30, 11, 0):
        return {"label": "Open Drive", "is_open": True}
    if within(11, 0, 13, 30):
        return {"label": "Midday", "is_open": True}
    if within(13, 30, 14, 30):
        return {"label": "Afternoon Drift", "is_open": True}
    if within(14, 30, 15, 30):
        return {"label": "Power Hour", "is_open": True}
    return {"label": "After Hours", "is_open": False}


def main():
    st.title("📈 SPY Small-DTE Trading Dashboard")
    
    # Auto-refresh control in sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
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
        
        # Show last update time
        if st.session_state.last_update:
            st.caption(f"Last updated: {st.session_state.last_update.strftime('%H:%M:%S')}")
        
        st.markdown("---")
    
    refresh_counter = 0
    if st.session_state.auto_refresh:
        refresh_counter = st_autorefresh(interval=config.AUTO_REFRESH_INTERVAL, key="data_refresh")
        last_counter = st.session_state.get("last_refresh_counter", -1)
        if refresh_counter > last_counter:
            # Force cache invalidation to ensure fresh data
            get_cached_intraday_data.clear()
            get_cached_daily_data.clear()
            get_cached_iv_context.clear()
            st.session_state.last_refresh_counter = refresh_counter
    
    st.markdown("---")
    
    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Trade Journal", "Backtest"]
    )
    
    if page == "Dashboard":
        render_dashboard()
    elif page == "Trade Journal":
        render_journal()
    elif page == "Backtest":
        render_backtest()


@st.cache_data(ttl=300)  # Cache daily data for 5 minutes (changes once per day)
def get_cached_daily_data(symbol: str, days: int):
    """Cached daily data fetch."""
    return get_daily_data(symbol, days)

@st.cache_data(ttl=30)  # Cache intraday data for 30 seconds
def get_cached_intraday_data(symbol: str, interval: str, days: int = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """Cached intraday data fetch."""
    if start_date is not None and end_date is not None:
        return get_intraday_data(symbol, interval, start_date=start_date, end_date=end_date)
    return get_intraday_data(symbol, interval, days=days if days is not None else 1)


@st.cache_data(ttl=3600)
def get_cached_iv_context(symbol: str, reference_price: float):
    """Cached IV context fetch."""
    return fetch_iv_context(symbol, reference_price)

def render_dashboard():
    """Render main dashboard with regime, intraday, and signals."""
    iv_context = {}

    # Load data with caching
    try:
        with st.spinner("Loading market data..."):
            # Use cached functions
            daily_df = get_cached_daily_data(config.SYMBOL, config.DAILY_LOOKBACK_DAYS)
            
            # Request last 2 days to ensure we get today's data if available
            intraday_raw = get_cached_intraday_data(
                config.SYMBOL,
                config.INTRADAY_INTERVAL,
                days=2
            )
            
            # Update last refresh time
            st.session_state.last_update = datetime.now()
            
            # Filter to today only
            intraday_raw.index = pd.to_datetime(intraday_raw.index)
            et_tz = ZoneInfo("America/New_York")
            
            # Debug: show which data source is being used and market status
            try:
                from data.alpaca_client import get_alpaca_api
                alpaca_api = get_alpaca_api()
                data_source = "Alpaca" if alpaca_api is not None else "yfinance (fallback)"
                
                # Check if market is open by getting latest trade
                if alpaca_api is not None:
                    try:
                        latest_trade = alpaca_api.get_latest_trade("SPY")
                        if latest_trade:
                            trade_time = latest_trade.t
                            if hasattr(trade_time, 'astimezone'):
                                trade_time_et = trade_time.astimezone(et_tz)
                                trade_date = trade_time_et.date()
                                trade_time_str = trade_time_et.strftime('%Y-%m-%d %H:%M:%S ET')
                                is_today = trade_date == datetime.now(et_tz).date()
                                market_status = "OPEN (today)" if is_today else f"CLOSED (last: {trade_time_str})"
                                st.caption(f"Data source: {data_source} | Market: {market_status}")
                            else:
                                st.caption(f"Data source: {data_source}")
                        else:
                            st.caption(f"Data source: {data_source} | Market: No trade data")
                    except Exception as e:
                        st.caption(f"Data source: {data_source} | Market check failed: {str(e)}")
                else:
                    st.caption(f"Data source: {data_source}")
            except:
                data_source = "yfinance"
                st.caption(f"Data source: {data_source}")
            today = datetime.now(et_tz).date()
            intraday_df = intraday_raw[intraday_raw.index.date == today].copy()
            
            # Filter to regular trading hours only (9:30 AM - 4:00 PM ET)
            # VWAP and EMAs should only use regular session data
            if not intraday_df.empty:
                # Convert index to timezone-aware if needed
                if intraday_df.index.tz is None:
                    intraday_df.index = pd.to_datetime(intraday_df.index).tz_localize('UTC').tz_convert(et_tz)
                elif intraday_df.index.tz != et_tz:
                    intraday_df.index = intraday_df.index.tz_convert(et_tz)
                
                # Filter to regular trading hours (9:30 AM - 4:00 PM ET)
                market_open_time = time(9, 30)
                market_close_time = time(16, 0)
                
                # Get time component of index
                intraday_df['time_only'] = intraday_df.index.time
                
                # Filter to regular hours only
                intraday_df = intraday_df[
                    (intraday_df['time_only'] >= market_open_time) & 
                    (intraday_df['time_only'] <= market_close_time)
                ].copy()
                
                # Drop the temporary time column
                intraday_df = intraday_df.drop(columns=['time_only'], errors='ignore')
            
            # Debug: show latest bar timestamp and date
            if not intraday_raw.empty:
                latest_bar_time = intraday_raw.index[-1]
                latest_bar_date = latest_bar_time.date()
                current_time = datetime.now(et_tz)
                # Show unique dates in the data
                unique_dates = sorted(set(intraday_raw.index.date))
                dates_str = ", ".join([d.strftime('%m-%d') for d in unique_dates[-5:]])  # Last 5 dates
                st.caption(f"Latest bar: {latest_bar_time.strftime('%Y-%m-%d %H:%M:%S ET')} | Today: {today} | Current: {current_time.strftime('%H:%M:%S ET')} | Today's bars: {len(intraday_df)} | Dates in data: {dates_str}")
            
            if intraday_df.empty:
                # Fallback: use last available session so dashboard still renders
                last_available_date = intraday_raw.index[-1].date()
                intraday_df = intraday_raw[intraday_raw.index.date == last_available_date].copy()
                
                # Filter fallback data to regular trading hours too
                if not intraday_df.empty:
                    if intraday_df.index.tz is None:
                        intraday_df.index = pd.to_datetime(intraday_df.index).tz_localize('UTC').tz_convert(et_tz)
                    elif intraday_df.index.tz != et_tz:
                        intraday_df.index = intraday_df.index.tz_convert(et_tz)
                    
                    market_open_time = time(9, 30)
                    market_close_time = time(16, 0)
                    intraday_df['time_only'] = intraday_df.index.time
                    intraday_df = intraday_df[
                        (intraday_df['time_only'] >= market_open_time) & 
                        (intraday_df['time_only'] <= market_close_time)
                    ].copy()
                    intraday_df = intraday_df.drop(columns=['time_only'], errors='ignore')
                
                st.info(f"No intraday data for today yet. Showing last available session ({last_available_date}).")
                if intraday_df.empty:
                    st.warning("No intraday data available.")
                    return
            
            today_data = get_today_data(daily_df, intraday_df)
            
            # Analyze regime
            regime = analyze_regime(daily_df, today_data)
            
            # Calculate previous day's EMA values for continuity
            previous_ema_fast = None
            previous_ema_slow = None
            
            # Get yesterday's data to calculate last EMA values
            yesterday_date = today - timedelta(days=1)
            yesterday_df = intraday_raw[intraday_raw.index.date == yesterday_date].copy()
            
            if not yesterday_df.empty:
                # Filter yesterday's data to regular trading hours
                if yesterday_df.index.tz is None:
                    yesterday_df.index = pd.to_datetime(yesterday_df.index).tz_localize('UTC').tz_convert(et_tz)
                elif yesterday_df.index.tz != et_tz:
                    yesterday_df.index = yesterday_df.index.tz_convert(et_tz)
                
                market_open_time = time(9, 30)
                market_close_time = time(16, 0)
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

            signal = generate_signal(
                regime, 
                intraday_analysis, 
                current_time=current_time,
                intraday_df=intraday_df,
                iv_context=iv_context,
                market_phase=market_phase
            )

            maybe_notify_signal(signal, regime, intraday_analysis, iv_context, current_time, market_phase)
            
            # Fetch IV context
            try:
                iv_context = get_cached_iv_context(config.SYMBOL, intraday_analysis['price'])
            except Exception:
                iv_context = {}
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.exception(e)
        return
    
    # ========== TODAY'S REGIME HEADER ==========
    st.header("Today's Regime")
    
    trend_color = "#2bd47d" if regime['trend'] == "Bullish" else "#ff5f6d" if regime['trend'] == "Bearish" else "#f7b500"
    regime_cards = []
    
    trend_body = f"""<div><div class="primary-value" style="color:{trend_color}">{regime['trend']}</div><p>{regime['trend_description']}</p></div><div class="metric-grid"><div class="metric-card"><div class="label">Latest Close</div><div class="value">${regime['latest_close']:.2f}</div></div><div class="metric-card"><div class="label">20D / 50D</div><div class="value">${regime['ma_short']:.0f} / ${regime['ma_long']:.0f}</div></div></div>"""
    regime_cards.append(build_info_card("Trend Bias", "📊", trend_body, trend_color))
    
    gap_sign = "+" if regime['gap'] > 0 else ""
    gap_body = f"""<div><div class="primary-value">{gap_sign}{regime['gap_pct']:.2f}% Gap</div><p>Range Class: {regime['range_class']}</p></div><div class="metric-grid"><div class="metric-card"><div class="label">Gap ($)</div><div class="value">${regime['gap']:.2f}</div></div><div class="metric-card"><div class="label">Range %</div><div class="value">{regime['range_pct']:.2f}%</div></div><div class="metric-card" style="grid-column: span 2;"><div class="label">Session Low/High</div><div class="value">${today_data['today_low']:.2f} / ${regime['range'] + today_data['today_low']:.2f}</div></div></div>"""
    regime_cards.append(build_info_card("Gap &amp; Range", "📏", gap_body, "#2e7bff"))
    
    status = regime['0dte_status']
    status_color = get_status_color(status)
    permission_body = f"""<div><div class="permission-bar" style="background:{status_color};">{status}</div><p style="text-align:center;">{regime['0dte_reason']}</p></div>"""
    regime_cards.append(build_info_card("0DTE Permission", "🚦", permission_body, status_color))

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
    atm_iv = iv_context.get('atm_iv')
    if atm_iv is not None:
        expiry = iv_context.get('expiry', 'N/A')
        iv_body_parts.append(f"<div class='primary-value'>{atm_iv:.2f}%</div><p>ATM IV (exp {expiry})</p>")
    else:
        iv_body_parts.append("<p>ATM IV unavailable</p>")

    vix_level = iv_context.get('vix_level')
    vix_rank = iv_context.get('vix_rank')
    vix_percentile = iv_context.get('vix_percentile')

    if vix_level is not None:
        iv_body_parts.append(f"<div class='metric-grid'><div class='metric-card'><div class='label'>VIX Level</div><div class='value'>{vix_level:.2f}</div></div>")
        if vix_rank is not None:
            iv_body_parts.append(f"<div class='metric-card'><div class='label'>VIX Rank</div><div class='value'>{vix_rank*100:.0f}%</div></div>")
        if vix_percentile is not None:
            iv_body_parts.append(f"<div class='metric-card'><div class='label'>VIX Percentile</div><div class='value'>{vix_percentile*100:.0f}%</div></div>")
        iv_body_parts.append("</div>")

    summary_text = describe_iv(atm_iv, vix_level, vix_rank, vix_percentile)
    iv_body_parts.append(summary_text)

    iv_body = "".join(iv_body_parts)
    regime_cards.append(build_info_card("Volatility Context", "⚡", iv_body, "#a855f7"))
    
    st.markdown(f"<div class='card-strip'>{''.join(regime_cards)}</div>", unsafe_allow_html=True)
    
    
    # ========== INTRADAY SPY PANEL ==========
    st.header("Intraday SPY Analysis")
    
    col_left, col_right = st.columns([3, 1.3], gap="large")
    
    with col_left:

        fig = plot_intraday_candlestick(
            intraday_df,
            vwap=intraday_analysis.get('vwap_series'),
            ema_fast=intraday_analysis.get('ema_fast_series'),
            ema_slow=intraday_analysis.get('ema_slow_series'),
            current_price=intraday_analysis.get('price'),
            signal_direction=signal.get('direction')
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_right:
        # Build the entire stats panel HTML in one go to ensure proper nesting
        stats_html = []
        stats_html.append("<div class='stats-panel' style='border-top: 4px solid #;'>")
        
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
        stats_html.append(f"""
            <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1rem;">
                <div style="font-size:2rem;">{trend_emoji}</div>
                <div>
                    <div style="font-size:1.5rem; font-weight:800; color:{trend_color};">{micro_trend}</div>
                    <div style="font-size:0.8rem; color:var(--text-secondary);">EMA {config.EMA_FAST} / {config.EMA_SLOW}</div>
                </div>
            </div>
        """)
        stats_html.append("</div>")
        stats_html.append("</div>")
        
        st.markdown("".join(stats_html), unsafe_allow_html=True)
    
    
    # ========== BIAS / SIGNAL BOX ==========
    st.header("Trading Bias / Signal")
    
    signal_direction = signal['direction']
    signal_confidence = signal['confidence']
    
    if signal_direction == "CALL":
        direction_color = "linear-gradient(135deg, #1d9a6c, #2bd47d)"
        direction_emoji = "🟢"
    elif signal_direction == "PUT":
        direction_color = "linear-gradient(135deg, #c23b4a, #ff5f6d)"
        direction_emoji = "🔴"
    else:
        direction_color = "linear-gradient(135deg, #3e4c66, #6b7c93)"
        direction_emoji = "⚪"
    
    col_signal1, col_signal2 = st.columns([1.2, 2], gap="large")
    
    session_label = market_phase.get("label", "Unknown") if 'market_phase' in locals() else "Unknown"

    with col_signal1:
        st.markdown(
            f"""
            <div class='dashboard-section' style='text-align:center; border-top: 4px solid #00000; background: linear-gradient(to bottom, rgba(46,123,255,0.08), rgba(46,123,255,0));'>
                <h4 style='margin-bottom:1.2rem; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:0.8rem;'>🎯 Signal</h4>
                <div class="badge-pill" style="background: {direction_color}; box-shadow: 0 0 20px rgba(0,0,0,0.3); margin-bottom: 1rem; border: 1px solid rgba(255,255,255,0.15);">
                    {direction_emoji} {signal_direction}
                </div>
                <div class="confidence-badge" style="{confidence_class(signal_confidence)}">
                    Confidence: {signal_confidence}
                </div>
                <p style="margin-top:1rem; color: var(--text-secondary); font-size:0.85rem;">Session: {session_label}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col_signal2:
        rationale_html = f"""
        <div class='dashboard-section' style='border-top: 4px solid #00000;'>
            <h4>📋 Rationale Breakdown</h4>
            <div class="rationale-content">
                <ul>
                    <li>{signal['reason']}</li>
                    <li>Trend Frame: {regime['trend']}</li>
                    <li>Micro Trend: {intraday_analysis['micro_trend']} (EMA {config.EMA_FAST}/{config.EMA_SLOW})</li>
                    <li>Price vs VWAP: {"Above" if intraday_analysis['price'] > intraday_analysis['vwap'] else "Below"}</li>
                    <li>5-Bar Return: {intraday_analysis['return_5']:.2f}% | VWAP Dist: {intraday_analysis['vwap_distance']:.2f}%</li>
                </ul>
            </div>
        </div>
        """
        st.markdown(rationale_html, unsafe_allow_html=True)


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
    """Render backtest interface."""
    st.header("🔬 Backtest Engine")
    
    st.info("Run a backtest using the same signal logic as the dashboard.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now().date() - timedelta(days=30)
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now().date()
        )
    
    if st.button("🚀 Run Backtest", type="primary"):
        if start_date >= end_date:
            st.error("Start date must be before end date.")
            return
        
        with st.spinner("Running backtest... This may take a few minutes."):
            try:
                engine = BacktestEngine()
                results = engine.run_backtest(
                    datetime.combine(start_date, datetime.min.time()),
                    datetime.combine(end_date, datetime.max.time())
                )
                
                # Store results in session state to persist across reruns
                st.session_state.backtest_results = results
                st.session_state.backtest_start_date = start_date
                st.session_state.backtest_end_date = end_date
                st.rerun()
            
            except Exception as e:
                st.error(f"Error running backtest: {str(e)}")
                st.exception(e)
    
    # Display results if they exist in session state
    if 'backtest_results' in st.session_state:
        results = st.session_state.backtest_results
        
        # Show date range
        st.info(f"📅 Backtest Period: {st.session_state.backtest_start_date} to {st.session_state.backtest_end_date}")
        
        # Display results
        st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
        st.subheader("Backtest Results")
        metrics_html = textwrap.dedent(
            f"""
            <div class="metric-grid" style="margin-top:1rem;">
                <div class="metric-card">
                    <div class="label">Total Trades</div>
                    <div class="value">{results['num_trades']}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Win Rate</div>
                    <div class="value">{results['win_rate']*100:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="label">Avg R Multiple</div>
                    <div class="value">{results['avg_r_multiple']:.2f}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Max Drawdown</div>
                    <div class="value">{results['max_drawdown']*100:.2f}%</div>
                </div>
                <div class="metric-card">
                    <div class="label">Total P/L</div>
                    <div class="value">${results['total_pnl']:.2f}</div>
                </div>
            </div>
            """
        )
        st.markdown(metrics_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if not results['equity_curve'].empty:
            st.markdown("<div class='dashboard-section' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
            st.subheader("Equity Curve")
            fig = plot_equity_curve(results['equity_curve'])
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Trades table
        if not results['trades'].empty:
            st.markdown("<div class='dashboard-section' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
            st.subheader("Trades")
            trades_html = results['trades'].to_html(
                classes="styled-table",
                index=False,
                border=0,
                justify="center"
            )
            st.markdown(trades_html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

