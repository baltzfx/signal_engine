"""
SignalEngine — FastAPI entry-point for AI-powered futures analysis.

Startup:
    1. Logging
    2. Redis pool
    3. Background workers (collectors → features → events → signals → telegram bot)

Shutdown:
    Graceful teardown of all background tasks and connections.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import setup_logging
from app.core.redis_pool import init_redis, close_redis, get_redis
from app.core.event_queue import queue_size
from app.core.monitoring import (
    start_monitor, stop_monitor, get_counters, get_gauges, get_system_metrics,
)
from app.core import prometheus_metrics as prom
from app.core.websocket_broadcast import (
    start_websocket_broadcaster, stop_websocket_broadcaster, handle_websocket_connection,
)
from app.storage.database import (
    init_db, close_db, get_signals, get_events, get_signal_stats, get_event_stats,
    get_performance_stats, get_latest_feature_importance, expire_old_signals,
)
from app.storage.chat_history import (
    init_chat_db, save_message, get_session_history, get_all_sessions, delete_session
)

# Workers
from app.collectors.manager import start_collectors, stop_collectors
from app.features.engine import start_feature_engine, stop_feature_engine
from app.events.engine import start_event_engine, stop_event_engine
from app.signals.engine import start_signal_engine, stop_signal_engine

# Telegram bot (optional)
try:
    from app.telegram.bot import start_telegram_bot, stop_telegram_bot, start_telegram_worker, stop_telegram_worker
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    async def start_telegram_bot():
        logger.warning("Telegram bot not available - queries disabled")
    async def stop_telegram_bot():
        pass
    async def start_telegram_worker():
        logger.warning("Telegram worker not available - signal notifications disabled")
    async def stop_telegram_worker():
        pass

logger = logging.getLogger(__name__)

# ── Background cleanup task ──────────────────────────────────────
_cleanup_task: asyncio.Task | None = None
_cleanup_running = False


async def _periodic_signal_cleanup():
    """Periodically expire old signals in database."""
    global _cleanup_running
    _cleanup_running = True
    
    while _cleanup_running:
        try:
            await asyncio.sleep(600)  # Run every 10 minutes
            expired = await expire_old_signals(ttl_seconds=3600)
            if expired > 0:
                logger.info(f"Periodic cleanup: expired {expired} old signals")
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in periodic signal cleanup")


async def start_cleanup_task():
    """Start the periodic cleanup background task."""
    global _cleanup_task
    _cleanup_task = asyncio.create_task(_periodic_signal_cleanup())
    logger.info("Periodic signal cleanup task started (runs every 10 minutes)")


async def stop_cleanup_task():
    """Stop the periodic cleanup task."""
    global _cleanup_task, _cleanup_running
    _cleanup_running = False
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        _cleanup_task = None
        logger.info("Periodic signal cleanup task stopped")


# ── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Async startup / shutdown hook."""
    setup_logging()
    logger.info("SignalEngine starting up …")

    # 1. Redis + SQLite
    await init_redis()
    await init_db()
    await init_chat_db()
    
    # Clean up expired signals from previous runs
    expired_count = await expire_old_signals(ttl_seconds=3600)
    if expired_count > 0:
        logger.info(f"Cleaned up {expired_count} expired signals from database")

    # 2. Background workers (order matters) - testing one by one
    await start_collectors()
    await start_feature_engine()
    await start_event_engine()
    await start_signal_engine()
    await start_telegram_bot()  # Bot for user queries/commands
    await start_telegram_worker()  # Worker for signal notifications
    await start_monitor()
    await start_websocket_broadcaster()  # NEW: WebSocket broadcaster
    await start_cleanup_task()  # Periodic signal cleanup

    logger.info("All workers started — engine is live")
    yield

    # Shutdown in reverse order
    logger.info("Shutting down …")
    await stop_cleanup_task()  # Stop cleanup task
    await stop_websocket_broadcaster()  # NEW
    await stop_monitor()
    await stop_telegram_worker()  # Signal sender
    await stop_telegram_bot()  # Bot for queries
    await stop_signal_engine()
    await stop_event_engine()
    await stop_feature_engine()
    await stop_collectors()
    await close_db()
    await close_redis()
    logger.info("Shutdown complete")


# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS middleware ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health endpoint ──────────────────────────────────────────────
@app.get("/health")
async def health():
    """Liveness / readiness probe."""
    try:
        r = get_redis()
        redis_ok = await r.ping()
    except Exception:
        redis_ok = False

    return JSONResponse(
        status_code=200 if redis_ok else 503,
        content={
            "status": "ok" if redis_ok else "degraded",
            "redis": redis_ok,
            "event_queue_size": queue_size(),
            "symbols_tracked": len(settings.symbols),
        },
    )


@app.get("/symbols")
async def list_symbols():
    """Return the list of tracked symbols."""
    return {"symbols": settings.symbols, "count": len(settings.symbols)}


@app.get("/events/queue")
async def event_queue_status():
    """Return the current event queue depth."""
    return {"queue_size": queue_size(), "max_size": settings.event_queue_maxsize}


# ── Metrics endpoint ─────────────────────────────────────────────
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=prom.get_metrics(),
        media_type=prom.get_content_type(),
    )


@app.get("/metrics/legacy")
async def metrics_legacy():
    """Legacy JSON metrics (backward compatibility)."""
    return {
        "system": get_system_metrics(),
        "counters": get_counters(),
        "gauges": get_gauges(),
    }


# ── Signal / Event history (SQLite) ─────────────────────────────
@app.get("/signals")
async def signals_history(symbol: str | None = None, limit: int = 50):
    """Query stored signals."""
    rows = await get_signals(symbol=symbol, limit=limit)
    return {"signals": rows, "count": len(rows)}


@app.get("/signals/stats")
async def signals_stats():
    return await get_signal_stats()


@app.get("/events")
async def events_history(symbol: str | None = None, event_type: str | None = None, limit: int = 100):
    rows = await get_events(symbol=symbol, event_type=event_type, limit=limit)
    return {"events": rows, "count": len(rows)}


@app.get("/events/stats")
async def events_stats():
    return await get_event_stats()


@app.get("/performance/stats")
async def performance_stats(symbol: str | None = None, timeframe: str = "5m", lookback_days: int = 30):
    """Get signal performance statistics by symbol."""
    return await get_performance_stats(symbol=symbol, timeframe=timeframe, lookback_days=lookback_days)


@app.get("/performance/feature-importance")
async def feature_importance(model_type: str = "lightgbm"):
    """Get latest feature importance scores."""
    importances = await get_latest_feature_importance(model_type)
    return {"model_type": model_type, "importances": importances}


@app.get("/query/top-symbols")
async def query_top_symbols(count: int = 5):
    """Get top performing symbols with AI analysis."""
    from app.signals.on_demand_scorer import get_top_symbols
    from app.ai.ollama_client import generate_query_response

    try:
        logger.info(f"Query endpoint called with count={count}")
        top_symbols = await get_top_symbols(count)
        logger.info(f"get_top_symbols returned {len(top_symbols)} symbols")
        if not top_symbols:
            logger.warning("No symbols available for analysis")
            return JSONResponse(status_code=503, content={"error": "No symbols available for analysis"})

        # Generate AI response
        query = f"Show me the top {count} futures symbols"
        logger.info("Generating AI response...")
        ai_response = await generate_query_response(query, top_symbols)
        logger.info(f"AI response generated: {len(ai_response)} chars")

        return {
            "query": query,
            "top_symbols": top_symbols,
            "ai_analysis": ai_response,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Query endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "Analysis failed"})


@app.get("/query/custom")
async def query_custom(query: str):
    """Process a custom AI query about the market."""
    from app.signals.on_demand_scorer import get_top_symbols
    from app.ai.ollama_client import generate_custom_query_response

    try:
        logger.info(f"Custom query endpoint called with: {query}")
        
        # Get some market context (top 10 symbols for analysis)
        top_symbols = await get_top_symbols(10)
        logger.info(f"Retrieved {len(top_symbols)} symbols for context")
        
        # Generate AI response for custom query
        logger.info("Generating AI response for custom query...")
        ai_response = await generate_custom_query_response(query, top_symbols)
        logger.info(f"AI response generated: {len(ai_response)} chars")

        return {
            "query": query,
            "ai_response": ai_response,
            "context_symbols": len(top_symbols),
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Custom query endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "Query processing failed"})


# ── Chat endpoints ──────────────────────────────────────────────
@app.post("/chat")
async def chat_message(request: dict):
    """Process a chat message and return AI response with history saved."""
    from app.signals.on_demand_scorer import get_top_symbols
    from app.signals.tracker import get_all_open_signals
    from app.ai.response_generator import generate_custom_query_response
    
    try:
        session_id = request.get("session_id", "default")
        message = request.get("message", "")
        
        if not message:
            return JSONResponse(status_code=400, content={"error": "Message is required"})
        
        # Save user message
        await save_message(session_id, "user", message)
        
        # Get recent context (last 10 messages for context)
        history = await get_session_history(session_id, limit=10)
        
        # Get market context - both top scores and active signals with entry/TP/SL
        top_symbols = await get_top_symbols(10)
        active_signals = get_all_open_signals()  # Get signals with trading levels
        
        # DEBUG: Print what we're passing to AI
        print(f"\n{'='*50}")
        print(f"CHAT DEBUG - Query: {message}")
        print(f"Active signals count: {len(active_signals)}")
        print(f"Top symbols count: {len(top_symbols)}")
        if active_signals:
            print(f"First active signal: {active_signals[0]}")
        print(f"{'='*50}\n")
        
        # Generate AI response with full context
        ai_response = await generate_custom_query_response(message, top_symbols, active_signals)
        
        # Save AI response
        await save_message(session_id, "assistant", ai_response)
        
        return {
            "session_id": session_id,
            "user_message": message,
            "ai_response": ai_response,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session."""
    try:
        history = await get_session_history(session_id, limit)
        return {"session_id": session_id, "messages": history}
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/chat/sessions")
async def list_chat_sessions(limit: int = 20):
    """Get list of recent chat sessions."""
    try:
        sessions = await get_all_sessions(limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/chat/session/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    try:
        await delete_session(session_id)
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/dashboard")
async def dashboard(limit: int = 20):
    """Frontend dashboard summary: recent signals, stats, system metrics."""
    recent_sigs = await get_signals(limit=limit)
    sig_stats = await get_signal_stats()
    system = get_system_metrics()
    return {
        "recent_signals": recent_sigs,
        "signal_stats": sig_stats,
        "system_metrics": system,
    }


# ── WebSocket real-time feed ─────────────────────────────────────
@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    """Real-time WebSocket feed for signals, events, and metrics."""
    await handle_websocket_connection(websocket)
