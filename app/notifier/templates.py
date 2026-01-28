"""
Message Templates
Format signals and alerts for notifications
"""
from datetime import datetime
from config.constants import SIGNAL_LONG, SIGNAL_SHORT


def confidence_to_stars(confidence: float) -> str:
    """Convert confidence score to star rating"""
    if confidence >= 90:
        return "⭐⭐⭐⭐⭐"
    elif confidence >= 80:
        return "⭐⭐⭐⭐"
    elif confidence >= 70:
        return "⭐⭐⭐"
    elif confidence >= 60:
        return "⭐⭐"
    else:
        return "⭐"


def format_signal_message(signal: dict) -> str:
    """
    Format a trading signal for Telegram notification
    
    Returns HTML-formatted message
    """
    symbol = signal['symbol']
    signal_type = signal['type']
    price = signal['price']
    confidence = signal['confidence']
    
    # Emoji based on signal type
    emoji = "🟢" if signal_type == SIGNAL_LONG else "🔴"
    
    # Star rating
    stars = confidence_to_stars(confidence)
    
    # Format timestamp
    timestamp = signal.get('timestamp', datetime.utcnow().isoformat())
    try:
        dt = datetime.fromisoformat(timestamp)
        time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    except:
        time_str = timestamp
    
    # Extract key indicators
    tf_1h = signal.get('timeframe_1h', {})
    tf_4h = signal.get('timeframe_4h', {})
    
    rsi_1h = tf_1h.get('rsi', {}).get('rsi', 'N/A')
    rsi_4h = tf_4h.get('rsi', {}).get('rsi', 'N/A')
    
    vol_1h = tf_1h.get('volume', {})
    vol_ratio = vol_1h.get('volume_ratio', 1.0)
    
    # Get stop and target if available
    stop_loss = signal.get('stop_loss')
    take_profit = signal.get('take_profit')
    rr_ratio = signal.get('risk_reward_ratio', 0)
    
    # TradingView link
    tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
    
    # Calculate percentages
    sl_percent = abs((stop_loss - price) / price * 100) if stop_loss else 0
    tp_percent = abs((take_profit - price) / price * 100) if take_profit else 0
    
    # Format timing info
    holding_hours = signal.get('holding_time_hours', 12)
    expiry_time = signal.get('expiry_time', '')
    
    try:
        expiry_dt = datetime.fromisoformat(expiry_time)
        expiry_str = expiry_dt.strftime("%H:%M UTC")
    except:
        expiry_str = "1 hour"
    
    # Build message with clear trading levels
    levels_section = f"""<b>💰 TRADING LEVELS</b>
📍 Entry Price: ${price:,.2f}
🛑 Stop Loss (SL): ${stop_loss:,.2f} ({'-' if signal_type == SIGNAL_LONG else '+'}{sl_percent:.2f}%)
🎯 Take Profit (TP): ${take_profit:,.2f} ({'+' if signal_type == SIGNAL_LONG else '-'}{tp_percent:.2f}%)
⚖️ Risk:Reward = 1:{rr_ratio:.2f}

<b>⏱️ TIMING</b>
⏳ Expected Hold: ~{holding_hours} hours
⌛ Signal Valid Until: {expiry_str}
"""
    
    message = f"""
{emoji} <b>{signal_type} SIGNAL</b> {emoji}

<b>📊 {symbol}</b>
<b>Confidence:</b> {stars} ({confidence:.1f}%)

{levels_section}

<b>📉 Technical Indicators</b>
• RSI (1H): {rsi_1h if isinstance(rsi_1h, str) else f'{rsi_1h:.1f}'}
• RSI (4H): {rsi_4h if isinstance(rsi_4h, str) else f'{rsi_4h:.1f}'}
• Volume: {vol_ratio:.2f}x average

<b>📈 Chart:</b> <a href="{tv_link}">View on TradingView</a>

<b>🕐 Generated:</b> {time_str}

<b>⚠️ Risk Warning:</b> <i>Educational purpose only. Not financial advice. Always use proper risk management and do your own research.</i>
""".strip()
    
    return message


def format_outcome_update(signal: dict, outcome: dict) -> str:
    """
    Format signal outcome update
    
    Args:
        signal: Original signal dict
        outcome: Outcome data dict
        
    Returns:
        HTML-formatted message
    """
    symbol = signal['symbol']
    signal_type = signal['type']
    entry_price = signal['price']
    
    current_price = outcome.get('current_price', entry_price)
    pnl_percent = outcome.get('pnl_percent', 0)
    outcome_type = outcome.get('outcome', 'PENDING')
    
    # Emoji based on outcome
    if outcome_type == 'WIN':
        emoji = "✅"
    elif outcome_type == 'LOSS':
        emoji = "❌"
    else:
        emoji = "⏳"
    
    # Color for PnL
    pnl_sign = "+" if pnl_percent >= 0 else ""
    
    message = f"""
{emoji} <b>Signal Update</b>

<b>Symbol:</b> {symbol}
<b>Type:</b> {signal_type}
<b>Entry:</b> ${entry_price:,.2f}
<b>Current:</b> ${current_price:,.2f}
<b>PnL:</b> {pnl_sign}{pnl_percent:.2f}%

<b>Status:</b> {outcome_type}
""".strip()
    
    return message
