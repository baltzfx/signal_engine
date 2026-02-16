"""
One-off script to send existing signals from database to Telegram.
Used to sync historical signals that were generated before Telegram worker was running.
"""

import asyncio
import httpx
import sys
from app.storage.database import init_db, get_signals
from app.core.config import settings


def format_signal(signal: dict) -> str:
    """Format signal for Telegram (HTML)."""
    direction = signal.get("direction", "?").upper()
    symbol = signal.get("symbol", "?")
    score = signal.get("score", 0)
    entry = signal.get("entry_price")
    tp = signal.get("tp_price")
    sl = signal.get("sl_price")
    outcome = signal.get("outcome")
    
    arrow = "🟢" if direction == "LONG" else "🔴"
    
    # Title with outcome status if closed
    title = f"{arrow} <b>{direction} {symbol}</b>"
    if outcome:
        outcome_emoji = {
            'tp_hit': '✅',
            'sl_hit': '❌',
            'expired': '⏱️',
            'manual': '🔧',
            'reversed': '🔄'
        }.get(outcome, '📊')
        title += f" {outcome_emoji} {outcome.upper().replace('_', ' ')}"
    
    lines = [
        title,
        f"Score: {score * 100:.1f}%",
    ]
    
    if entry:
        lines.append(f"Entry: ${entry:.6f}")
    if tp:
        lines.append(f"TP: ${tp:.6f}")
    if sl:
        lines.append(f"SL: ${sl:.6f}")
    
    # Performance metrics for closed signals
    if outcome:
        duration_sec = signal.get("duration_sec")
        return_pct = signal.get("return_pct")
        
        metrics = []
        if duration_sec is not None:
            # Format duration nicely
            if duration_sec < 60:
                duration_str = f"{duration_sec:.0f}s"
            elif duration_sec < 3600:
                duration_str = f"{duration_sec/60:.1f}m"
            else:
                duration_str = f"{duration_sec/3600:.1f}h"
            metrics.append(f"⏱️ Duration: {duration_str}")
        
        if return_pct is not None:
            return_emoji = "📈" if return_pct > 0 else "📉"
            metrics.append(f"{return_emoji} Return: {return_pct:+.2f}%")
        
        if metrics:
            lines.append("")
            lines.extend(metrics)
    
    return "\n".join(lines)


async def send_to_telegram(signal: dict) -> bool:
    """Send signal to Telegram."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("❌ Telegram not configured (missing bot token or chat ID)")
        return False
    
    text = format_signal(signal)
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                print(f"✅ Sent: {signal['direction'].upper()} {signal['symbol']}")
                return True
            else:
                print(f"❌ Failed (HTTP {resp.status_code}): {resp.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Send all signals from database to Telegram."""
    print("📡 Initializing database...")
    await init_db()
    
    # Get all signals (or limit to recent ones)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"📊 Fetching last {limit} signals from database...")
    
    signals = await get_signals(limit=limit)
    
    if not signals:
        print("⚠️  No signals found in database")
        return
    
    print(f"📤 Found {len(signals)} signals. Sending to Telegram...")
    print(f"Bot Token: {'✅ Configured' if settings.telegram_bot_token else '❌ Missing'}")
    print(f"Chat ID: {settings.telegram_chat_id or '❌ Missing'}\n")
    
    sent = 0
    failed = 0
    
    for signal in signals:
        success = await send_to_telegram(signal)
        if success:
            sent += 1
        else:
            failed += 1
        
        # Rate limiting - wait 1 second between messages
        await asyncio.sleep(1)
    
    print(f"\n✅ Sent: {sent}")
    print(f"❌ Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
