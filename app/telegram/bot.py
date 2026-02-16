"""
Telegram Bot for handling user queries.

Replaced the old sender with a bot that receives and responds to user queries.
"""

from __future__ import annotations

import asyncio
import hashlib
import httpx
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

# Try to import telegram, make it optional
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Create dummy classes for type hints
    class Update:
        pass
    class ContextTypes:
        DEFAULT_TYPE = None

from app.core.config import settings
from app.core.monitoring import inc
from app.telegram.query_handler import query_handler
from app.signals.engine import get_signal_queue

logger = logging.getLogger(__name__)

# Bot for queries
_application: Optional[Application] = None
_running = False

# Worker for signal notifications
_main_task: Optional[asyncio.Task] = None
_retry_task: Optional[asyncio.Task] = None
_retry_queue: Optional[asyncio.Queue] = None
_last_send_ts: float = 0.0
_sent_hashes: OrderedDict[str, float] = OrderedDict()
_sent_hashes_max = 1000  # Keep last 1000 signal hashes
_MAX_RETRY_ATTEMPTS = 3


def _get_retry_queue() -> asyncio.Queue:
    """Lazy init retry queue."""
    global _retry_queue
    if _retry_queue is None:
        _retry_queue = asyncio.Queue(maxsize=100)
    return _retry_queue


async def start_telegram_bot() -> None:
    """Start the Telegram bot for handling queries."""
    global _application, _running

    if not TELEGRAM_AVAILABLE:
        logger.warning("Telegram library not available — bot disabled")
        return

    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token not configured — bot disabled")
        return

    _running = True

    # Create application
    _application = Application.builder().token(settings.telegram_bot_token).build()

    # Add handlers
    _application.add_handler(CommandHandler("start", _start_command))
    _application.add_handler(CommandHandler("help", _help_command))
    _application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    # Start the bot
    logger.info("Starting Telegram bot...")
    await _application.initialize()
    await _application.start()

    # Start polling
    await _application.updater.start_polling()

    logger.info("Telegram bot started successfully")


async def stop_telegram_bot() -> None:
    """Stop the Telegram bot."""
    global _application, _running

    if not _running or not _application:
        return

    _running = False

    logger.info("Stopping Telegram bot...")
    await _application.updater.stop()
    await _application.stop()
    await _application.shutdown()

    logger.info("Telegram bot stopped")


async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not _is_allowed_chat(update):
        return

    welcome_text = """🤖 Welcome to SignalEngine Bot!

I analyze real-time futures market data to find the top performing symbols.

Try asking: "What's the top symbols for futures now?"

Use /help for more commands."""

    await update.message.reply_text(welcome_text)
    inc("telegram_start_command")


async def _help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not _is_allowed_chat(update):
        return

    help_text = await query_handler.process_query("help")
    await update.message.reply_text(help_text)
    inc("telegram_help_command")


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages."""
    if not _is_allowed_chat(update):
        return

    try:
        # Process the query
        user_message = update.message.text
        response = await query_handler.process_query(user_message)

        # Send response
        await update.message.reply_text(response, parse_mode='Markdown')

        inc("telegram_query_processed")

    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        error_text = "❌ Sorry, there was an error processing your request. Please try again."
        await update.message.reply_text(error_text)
        inc("telegram_query_error")


def _is_allowed_chat(update: Update) -> bool:
    """Check if the chat is allowed to interact with the bot."""
    if not settings.telegram_allowed_chat_ids:
        # If no restrictions, allow all
        return True

    chat_id = str(update.effective_chat.id)
    allowed = chat_id in settings.telegram_allowed_chat_ids

    if not allowed:
        logger.warning(f"Unauthorized chat attempt from {chat_id}")
        inc("telegram_unauthorized_chat")

    return allowed


async def start_telegram_worker() -> None:
    global _main_task, _retry_task, _running
    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token not configured — sender disabled")
        _running = False
        return
    _running = True
    _main_task = asyncio.create_task(_telegram_loop())
    _retry_task = asyncio.create_task(_retry_loop())
    logger.info("Telegram worker started (main + retry)")


async def stop_telegram_worker() -> None:
    global _main_task, _retry_task, _running
    _running = False
    for t in (_main_task, _retry_task):
        if t:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
    _main_task = None
    _retry_task = None
    logger.info("Telegram worker stopped")


# ── Main loop (never blocks on retries) ──────────────────────────

async def _telegram_loop() -> None:
    sq = get_signal_queue()
    while _running:
        try:
            signal = await asyncio.wait_for(sq.get(), timeout=2.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            return

        # Deduplication
        sig_hash = _hash_signal(signal)
        if sig_hash in _sent_hashes:
            logger.debug("Duplicate signal skipped for %s", signal.get("symbol"))
            continue

        # Rate-limiting
        await _rate_limit()

        # Fire-and-forget first attempt — success updates dedup, failure goes to retry queue
        success = await _try_send(signal)
        if success:
            _mark_sent(sig_hash)
            inc("telegram_sent")
            logger.debug(f"Sent to Telegram: {signal.get('symbol')} (queue: {sq.qsize()})")
        else:
            # Enqueue for retry — do NOT block the main loop
            rq = _get_retry_queue()
            try:
                rq.put_nowait((signal, 1, sig_hash))
            except asyncio.QueueFull:
                logger.warning("Retry queue full — dropping failed signal for %s", signal.get("symbol"))
                inc("telegram_dropped")


# ── Retry loop (separate task) ───────────────────────────────────

async def _retry_loop() -> None:
    """Process the retry queue with exponential backoff, independent of the main loop."""
    rq = _get_retry_queue()
    while _running:
        try:
            signal, attempt, sig_hash = await asyncio.wait_for(rq.get(), timeout=2.0)
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            return

        # Exponential backoff delay
        delay = settings.telegram_retry_delay * (2 ** (attempt - 1))
        await asyncio.sleep(delay)

        success = await _try_send(signal)
        if success:
            _mark_sent(sig_hash)
            inc("telegram_sent")
            inc("telegram_retried")
        elif attempt < _MAX_RETRY_ATTEMPTS:
            try:
                rq.put_nowait((signal, attempt + 1, sig_hash))
            except asyncio.QueueFull:
                logger.warning("Retry queue full — dropping signal after %d attempts", attempt)
                inc("telegram_dropped")
        else:
            logger.error(
                "Telegram send failed permanently after %d attempts for %s",
                _MAX_RETRY_ATTEMPTS,
                signal.get("symbol"),
            )
            inc("telegram_failed")


# ── Helpers ───────────────────────────────────────────────────────

def _mark_sent(sig_hash: str) -> None:
    _sent_hashes[sig_hash] = time.time()
    while len(_sent_hashes) > _sent_hashes_max:
        _sent_hashes.popitem(last=False)


async def _try_send(signal: Dict[str, Any]) -> bool:
    """Single send attempt — returns True on success, False on failure. Never raises."""
    text = _format_signal(signal)
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
                logger.info(
                    "Telegram signal sent: %s %s",
                    signal.get("direction"),
                    signal.get("symbol"),
                )
                return True
            elif resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
                logger.warning("Telegram rate-limited — waiting %ds", retry_after)
                await asyncio.sleep(retry_after)
                return False
            else:
                logger.warning(
                    "Telegram send failed (HTTP %d): %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
    except Exception:
        logger.warning("Telegram send exception", exc_info=True)
        return False


# ── Message formatting ────────────────────────────────────────────

def _format_signal(signal: Dict[str, Any]) -> str:
    """Build a Telegram-friendly message from a signal dict."""
    direction = signal.get("direction", "?").upper()
    symbol = signal.get("symbol", "?")
    score = signal.get("score", 0)
    triggers = ", ".join(signal.get("trigger_events", []))
    outcome = signal.get("outcome")

    arrow = "🟢" if direction == "LONG" else "🔴"

    # Title with outcome status if closed
    title = f"{arrow} <b>{direction} Signal — {symbol}</b>"
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
        f"Score: <b>{score:.2f}</b>",
        f"Triggers: {triggers}",
    ]

    # TP / SL / Entry levels from tracker
    entry = signal.get("entry_price")
    tp = signal.get("tp_price")
    sl = signal.get("sl_price")
    if entry and tp and sl:
        lines.append(f"")
        lines.append(f"🎯 Entry: <b>{entry:.4f}</b>")
        lines.append(f"✅ TP: <b>{tp:.4f}</b>")
        lines.append(f"❌ SL: <b>{sl:.4f}</b>")
        atr = signal.get("atr", 0)
        if atr:
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
            lines.append(f"ATR: {atr:.4f}  |  R:R = {rr:.1f}")

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

    # AI overlay info
    ai = signal.get("ai")
    if ai:
        lines.append(
            f"AI Confidence: {ai.get('confidence', 0):.2f} "
            f"(P_long={ai.get('probability_long', 0):.2f} "
            f"P_short={ai.get('probability_short', 0):.2f})"
        )

    snap = signal.get("features_snapshot", {})
    if snap:
        lines.append(
            f"EMA slope: {snap.get('ema_slope', '—')}  |  "
            f"VWAP dist: {snap.get('vwap_distance', '—')}"
        )
        lines.append(
            f"OI Δ: {snap.get('oi_delta', '—')}  |  "
            f"Funding z: {snap.get('funding_zscore', '—')}"
        )

    return "\n".join(lines)


def _hash_signal(signal: Dict[str, Any]) -> str:
    """Deterministic hash to detect duplicate signals."""
    # Use exact timestamp and score to differentiate unique signals
    # This prevents legitimate signals from being marked as duplicates
    key = f"{signal.get('symbol')}:{signal.get('direction')}:{signal.get('timestamp')}:{signal.get('score')}"
    return hashlib.md5(key.encode()).hexdigest()


async def _rate_limit() -> None:
    """Enforce minimum interval between sends."""
    global _last_send_ts
    now = time.time()
    min_interval = 1.0 / settings.telegram_rate_limit
    wait = min_interval - (now - _last_send_ts)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_send_ts = time.time()
