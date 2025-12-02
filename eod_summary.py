"""
End-of-Day Summary Generator

Generates and sends comprehensive market summary to Discord at 4:00 PM ET.
Includes market stats, signal analysis, and AI-generated rationale.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict
from eod_tracker import get_tracker


def generate_market_rationale(summary: Dict) -> str:
    """
    Generate a natural language summary of the trading day.
    
    Args:
        summary: EOD summary data from tracker
        
    Returns:
        String containing market analysis
    """
    market = summary["market_data"]
    vix = summary["vix_data"]
    dte_perm = summary["dte_permission"]
    range_pct = summary["range_pct"]
    
    total_sigs = summary["total_signals"]
    actionable = summary["actionable_signals"]
    call_sigs = summary["call_signals"]
    put_sigs = summary["put_signals"]
    
    # Calculate change
    if market["open"] and market["close"]:
        change_pct = ((market["close"] - market["open"]) / market["open"]) * 100
        change_dollar = market["close"] - market["open"]
    else:
        change_pct = 0
        change_dollar = 0
    
    # Build rationale
    rationale_parts = []
    
    # Market direction
    if abs(change_pct) < 0.2:
        direction = "choppy and rangebound"
    elif change_pct > 0.5:
        direction = "strongly bullish"
    elif change_pct > 0:
        direction = "modestly bullish"
    elif change_pct < -0.5:
        direction = "strongly bearish"
    else:
        direction = "modestly bearish"
    
    rationale_parts.append(f"SPY was **{direction}** today, closing {'+' if change_dollar >= 0 else ''}{change_dollar:.2f} ({'+' if change_pct >= 0 else ''}{change_pct:.2f}%).")
    
    # 0DTE environment assessment
    if dte_perm == "FAVORABLE":
        env_desc = "**FAVORABLE** for 0DTE options trading, with sufficient volatility and range to support directional plays"
    elif dte_perm == "CAUTION":
        env_desc = "**CAUTION** for 0DTE options, indicating mixed conditions and lower directional conviction"
    else:
        env_desc = "**AVOID** for 0DTE options, with VIX too low or choppy price action making options trades unfavorable"
    
    if range_pct:
        rationale_parts.append(f"The 0DTE environment was {env_desc}. Daily range was {range_pct:.2f}% ({'above' if range_pct >= 1.5 else 'below'} the 1.5% FAVORABLE threshold).")
    else:
        rationale_parts.append(f"The 0DTE environment was {env_desc}.")
    
    # VIX context
    if vix.get("close") and vix.get("open"):
        vix_change = vix["close"] - vix["open"]
        if vix["close"] <= 15:
            vix_desc = f"VIX was at {vix['close']:.1f} (below the 15 hard deck), signaling very calm market conditions"
        elif vix["close"] >= 25:
            vix_desc = f"VIX spiked to {vix['close']:.1f}, indicating elevated fear and volatility"
        elif vix_change > 2:
            vix_desc = f"VIX rose {vix_change:.1f} points to {vix['close']:.1f}, showing increasing uncertainty"
        elif vix_change < -2:
            vix_desc = f"VIX dropped {abs(vix_change):.1f} points to {vix['close']:.1f}, showing calming conditions"
        else:
            vix_desc = f"VIX remained relatively stable at {vix['close']:.1f}"
        
        rationale_parts.append(vix_desc + ".")
    
    # Signal analysis
    if total_sigs == 0:
        rationale_parts.append("The system generated **no signals** today, correctly staying flat during unfavorable conditions.")
    elif actionable == 0:
        flip_flop = call_sigs > 0 and put_sigs > 0
        if flip_flop:
            rationale_parts.append(f"The system generated {total_sigs} awareness signals ({call_sigs} CALL, {put_sigs} PUT) but **0 actionable trades**. The CALL→PUT flip-flop pattern confirms this was a low-quality, choppy day that should be avoided.")
        else:
            sig_type = "CALL" if call_sigs > put_sigs else "PUT"
            rationale_parts.append(f"The system generated {total_sigs} {sig_type}-biased awareness signals but **0 actionable trades**, correctly identifying that conditions didn't meet the strict HIGH + FAVORABLE criteria.")
    else:
        rationale_parts.append(f"The system generated {total_sigs} total signals, with **{actionable} actionable** (HIGH + FAVORABLE) trades. This was a high-quality trading environment.")
    
    # Trading recommendation
    if actionable > 0:
        rationale_parts.append("✅ **Paper trading should have been executed** on actionable signals.")
    else:
        rationale_parts.append("✅ **Correctly stayed flat** - no trades should have been taken.")
    
    return " ".join(rationale_parts)


def create_eod_embed(summary: Dict, current_date: str) -> Dict:
    """
    Create Discord embed for EOD summary.
    
    Args:
        summary: EOD summary data
        current_date: Date string (YYYY-MM-DD)
        
    Returns:
        Discord embed dictionary
    """
    market = summary["market_data"]
    vix = summary["vix_data"]
    iv = summary["iv_data"]
    
    # Calculate change
    if market["open"] and market["close"]:
        change_pct = ((market["close"] - market["open"]) / market["open"]) * 100
        change_dollar = market["close"] - market["open"]
        change_str = f"{'+' if change_dollar >= 0 else ''}{change_dollar:.2f} ({'+' if change_pct >= 0 else ''}{change_pct:.2f}%)"
    else:
        change_str = "N/A"
    
    # Format volume
    vol = market.get("volume", 0)
    if vol:
        if vol >= 1_000_000:
            vol_str = f"{vol/1_000_000:.2f}M"
        elif vol >= 1_000:
            vol_str = f"{vol/1_000:.0f}K"
        else:
            vol_str = f"{vol:,}"
    else:
        vol_str = "N/A"
    
    # VIX change
    vix_change_str = "N/A"
    if vix.get("open") and vix.get("close"):
        vix_chg = vix["close"] - vix["open"]
        vix_change_str = f"{vix['close']:.1f} ({'+' if vix_chg >= 0 else ''}{vix_chg:.1f})"
    elif vix.get("close"):
        vix_change_str = f"{vix['close']:.1f}"
    
    # IV range
    iv_range_str = "N/A"
    if iv.get("low") is not None and iv.get("high") is not None:
        iv_range_str = f"{iv['low']:.1f}% - {iv['high']:.1f}%"
    
    # Range percentage
    range_str = "N/A"
    if summary.get("range_pct"):
        range_pct = summary["range_pct"]
        range_str = f"{range_pct:.2f}% ({'✅' if range_pct >= 1.5 else '⚠️'} {'>=' if range_pct >= 1.5 else '<'} 1.5% threshold)"
    
    # Permission emoji
    perm_emoji = {
        "FAVORABLE": "✅",
        "CAUTION": "⚠️",
        "AVOID": "❌"
    }
    perm = summary.get("dte_permission", "UNKNOWN")
    perm_str = f"{perm} {perm_emoji.get(perm, '')}"
    
    # Actionable status
    actionable = summary["actionable_signals"]
    action_str = f"{actionable} {'✅' if actionable > 0 else '❌'}"
    
    # Session breakdown - only show active sessions
    session_text = []
    for session, counts in summary["session_breakdown"].items():
        total = counts["call"] + counts["put"]
        if total > 0:
            session_text.append(f"• **{session}:** {total} ({counts['call']} CALL, {counts['put']} PUT)")
    
    if not session_text:
        session_text.append("• No signals generated")
    
    # Generate rationale
    rationale = generate_market_rationale(summary)
    
    # Build embed
    embed = {
        "title": f"📊 End-of-Day Report",
        "description": f"**{datetime.fromisoformat(current_date).strftime('%A, %B %d, %Y')}**",
        "color": 0x5865F2,  # Blurple
        "fields": [
            {
                "name": "📈 SPY Performance",
                "value": f"**Open:** ${market['open']:.2f}  →  **Close:** ${market['close']:.2f}\n**Change:** {change_str}\n**Range:** ${market['low']:.2f} - ${market['high']:.2f} ({range_str})\n**Volume:** {vol_str}",
                "inline": False
            },
            {
                "name": "🎯 0DTE Environment",
                "value": f"**Permission:** {perm_str}\n**VIX:** {vix_change_str}\n**ATM IV Range:** {iv_range_str}",
                "inline": False
            },
            {
                "name": "📊 Signal Summary",
                "value": f"**Total Signals:** {summary['total_signals']}\n**CALL:** {summary['call_signals']} | **PUT:** {summary['put_signals']}\n**HIGH:** {summary['high_signals']} | **MEDIUM:** {summary['medium_signals']}\n**Actionable (HIGH + FAVORABLE):** {action_str}",
                "inline": False
            },
            {
                "name": "⏰ Session Breakdown",
                "value": "\n".join(session_text),
                "inline": False
            },
            {
                "name": "💡 Market Rationale",
                "value": rationale,
                "inline": False
            }
        ],
        "footer": {
            "text": f"Report generated at {datetime.now(ZoneInfo('America/New_York')).strftime('%I:%M %p ET')}"
        }
    }
    
    return embed


def should_send_eod_summary() -> bool:
    """
    Check if EOD summary should be sent (weekday only).
    
    Returns:
        True if it's a weekday, False if weekend
    """
    et_time = datetime.now(ZoneInfo("America/New_York"))
    # Monday = 0, Sunday = 6
    return et_time.weekday() < 5  # Monday-Friday only


def send_eod_summary():
    """Generate and send EOD summary to Discord."""
    from app import send_discord_notification
    
    # Check if it's a trading day
    if not should_send_eod_summary():
        print("📅 Weekend detected - skipping EOD summary")
        return
    
    # Get tracker and summary
    tracker = get_tracker()
    summary = tracker.get_summary()
    
    current_date = tracker.data.get("date")
    if not current_date:
        print("⚠️ No data available for EOD summary")
        return
    
    # Create embed
    embed = create_eod_embed(summary, current_date)
    
    # Send to Discord
    send_discord_notification(
        message="📊 **Daily Market Summary**",
        embed=embed
    )
    
    print(f"✅ EOD summary sent for {current_date}")
