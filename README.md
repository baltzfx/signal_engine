# SignalEngine v3 — Real-Time Futures Trading Signal System

AI-powered cryptocurrency futures signal generator with **real-time WebSocket dashboard** and **automatic Telegram notifications**. Features database-first architecture ensuring zero signal loss, multi-timeframe technical analysis, and intelligent trade management with TP/SL tracking.

> **🚀 Latest:** Real-time UI updates via WebSocket, database-first signal flow, professional signals table with live sorting/filtering, enhanced Telegram formatting, and 10k signal queue capacity.

## Architecture

```
┌──────────────┐   WebSocket    ┌───────────┐   Redis    ┌───────────┐
│   Binance    │ ─────────────► │ Collectors │ ────────► │  Feature  │
│   Futures    │                └───────────┘            │  Engine   │
└──────────────┘                                         └─────┬─────┘
                                                               │
                                                         ┌─────▼─────┐
                                                         │   Event   │
                                                         │  Engine   │
                                                         └─────┬─────┘
                                                               │ async queue
                                                         ┌─────▼─────┐
                                                         │  Signal   │
                                                         │  Engine   │
                                                         └─────┬─────┘
                                                               │
                                                        1. Database First
                                                               │
                                                         ┌─────▼─────┐
                                                         │  SQLite   │
                                                         │  Storage  │
                                                         └───────────┘
                                                               │
                                            2. Multicast to UI + Telegram
                                                  ┌────────────┴────────────┐
                                                  │                         │
                                            ┌─────▼─────┐             ┌─────▼─────┐
                                            │ WebSocket │             │ Telegram  │
                                            │ Broadcast │             │  Queue    │
                                            │ (Direct)  │             │ (10k cap) │
                                            └─────┬─────┘             └─────┬─────┘
                                                  │                         │
                                            ┌─────▼─────┐             ┌─────▼─────┐
                                            │  Next.js  │             │ Telegram  │
                                            │    UI     │             │    Bot    │
                                            └───────────┘             └─────┬─────┘
                                                                            │
                                                                      ┌─────▼─────┐
                                                                      │   Ollama  │
                                                                      │     AI    │
                                                                      └───────────┘
```

**Key Design Principles:**
1. **Database-First**: All signals persisted before delivery (zero data loss)
2. **Multicast Pattern**: Signals broadcast to both UI and Telegram (no queue competition)
3. **High Capacity**: 10,000 signal queue prevents drops during high-volume periods
4. **Real-Time Updates**: WebSocket streaming for instant UI updates (no refresh needed)
5. **Deduplication**: MD5 hash of `symbol:direction:timestamp:score` prevents exact duplicates

## Features

### 🎯 Core Trading Features
- **Real-Time Signal Generation**: Rule-based scoring across 9+ technical indicators
- **Multi-Timeframe Analysis**: 1m, 5m, 15m, 1h confluence for high-confidence signals
- **Automated TP/SL Management**: ATR-based targets (2.0× ATR for TP, 1.0× ATR for SL)
- **Signal Lifecycle Tracking**: Monitors signals until TP hit, SL hit, or 1-hour expiration
- **Outcome Recording**: Tracks win/loss with return percentages and duration
- **Signal Threshold**: Configurable minimum score (default: 50%) for signal emission

### 📊 Modern UI Features
- **Professional Signals Table**: 8-column table with real-time sorting (newest first)
- **Live Updates**: WebSocket-powered auto-refresh (no page reload needed)
- **Tab Filtering**: Filter by All, Open, Closed, TP Hit, SL Hit, Expired
- **Color-Coded Status**: 🟢 Green (TP hit), 🔴 Red (SL hit), 🔵 Blue (open), ⚪ Gray (expired)
- **Price Display**: Entry, TP, SL with 4-decimal precision
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Mode**: Modern gradient design with smooth animations

### 🤖 Telegram Integration
- **Auto-Send on Signal**: All signals ≥50% score sent automatically
- **Enhanced Formatting**: Emojis (🟢/🔴), outcome status, duration, return %
- **Rate Limiting**: 1 msg/sec to comply with Telegram API limits
- **Deduplication**: Prevents duplicate sends of exact same signal
- **Retry Queue**: Unlimited capacity for failed sends with exponential backoff
- **Manual Sync Script**: `send_signal_to_telegram.py` for historical signals

### 🔧 System Reliability
- **Database-First Architecture**: Signals saved to SQLite before delivery
- **10,000 Signal Queue**: High capacity prevents drops during market volatility
- **WebSocket Multicast**: Direct broadcast to UI clients (doesn't consume queue)
- **Queue Monitoring**: Debug logs show queue size and capacity
- **Zero Signal Loss**: Database persistence ensures no data lost on crashes
- **Health Checks**: `/health` endpoint with uptime and component status

### 📈 Analytics & Performance
- **Win Rate Tracking**: Per-symbol performance statistics
- **Return Analysis**: Average returns, best/worst trades
- **Sharpe Ratio**: Risk-adjusted performance metrics
- **Feature Importance**: Track which indicators drive signal quality
- **Prometheus Metrics**: Production-grade monitoring integration
- **Event Statistics**: Aggregate stats on market events by type/symbol

## Quick Start

### Prerequisites
- **Python 3.11+** (backend)
- **Node.js 18+** and **npm** (frontend)
- **Redis** server running on `localhost:6379`
- **Ollama** (optional, for AI chat features) - [Download here](https://ollama.ai/)
- **Telegram Bot Token** (optional, for auto-notifications) - Get from [@BotFather](https://t.me/botfather)

### 1. Backend Setup

```bash
# Navigate to project
cd SignalEngine.v3

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from template if available)
# Add your configuration:
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=telegram_chat_id_here
SIGNAL_SCORE_THRESHOLD=0.50

# Start Redis (if not already running)
# Windows: Download and run Redis from GitHub releases
# Linux: sudo systemctl start redis
# Mac: brew services start redis

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# OR use Python module syntax
python -m app
```

**Expected Backend Logs:**
```
✅ Feature engine started
✅ Event engine started
✅ Signal engine (V1 rule-based) started
✅ Telegram worker started (main + retry)
✅ WebSocket broadcaster started
```

### 2. Frontend Setup

```bash
# Open new terminal and navigate to frontend
cd SignalEngine.v3/frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Frontend will be available at:
# http://localhost:3000
```

### 3. Verify Everything Works

**Check Backend Health:**
```bash
curl http://localhost:8000/health
```

**View Signals in UI:**
- Open http://localhost:3000/signals
- Watch for signals appearing in real-time (auto-updates via WebSocket)
- Check different tabs: All, Open, Closed, TP Hit, SL Hit, Expired

**Check Telegram:**
- If configured, signals ≥50% score auto-send to your Telegram chat
- Format: Direction, Symbol, Score, Entry, TP, SL, Timestamp

### 4. Telegram Bot Setup (Optional)

**Create Your Bot:**
1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow prompts
3. Copy your bot token (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Get your chat ID:
   - Start chat with [@userinfobot](https://t.me/userinfobot)
   - Copy the ID (looks like: `123456789` or `-1003497403947` for channels)

**Configure in .env:**
```bash
TELEGRAM_BOT_TOKEN=telegram_bot_token
TELEGRAM_CHAT_ID=telegram_chat_id
```

**Restart Backend:**
```bash
# Stop current backend (Ctrl+C)
# Start again
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Test Telegram Integration:**
- Wait for a signal to be generated (watch backend logs)
- Check your Telegram chat for automatic notification
- Or manually send historical signals:
  ```bash
  python send_signal_to_telegram.py 5  # Sends last 5 signals
  ```

---

## User Interface

### 🎯 Next.js Real-Time Dashboard (Recommended)

**Modern React-based UI with live WebSocket updates:**

```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

**Available Pages:**

| Route | Description |
|-------|-------------|
| `/` | Home dashboard with system overview |
| `/signals` | **Professional signals table** with real-time updates |
| `/chat` | AI chat interface (requires Ollama) |
| `/dashboard` | System metrics and performance stats |

**Signals Table Features:**
- ✅ **Real-time updates** - Signals appear instantly via WebSocket
- ✅ **Auto-sorting** - Newest signals always on top
- ✅ **Tab filtering** - All / Open / Closed / TP Hit / SL Hit / Expired
- ✅ **8 columns** - Time, Symbol, Direction, Score, Entry, TP, SL, Status
- ✅ **Color coding** - Green (TP), Red (SL), Blue (open), Gray (expired)
- ✅ **Price precision** - 4-decimal display for accurate entry/TP/SL
- ✅ **Footer info** - Shows auto-send threshold (≥50%)

**WebSocket Connection:**
- Auto-connects to `ws://localhost:8000/ws/feed`
- Reconnects automatically if connection drops
- Silent in production (no console spam)
- Dev mode shows connection status

### 📊 Classic Dashboard

**Static HTML dashboard with manual refresh:**

```bash
# Start backend first
python -m app

# Open dashboard
python open_dashboard.py
# OR open dashboard.html in your browser
```

Features:
- System health monitoring
- Top symbols analysis
- Recent signals history
- System metrics

### 🖥️ Command Line Interface

**Powerful CLI for automation and scripting:**

```bash
# Check server status
python cli.py status

# Get top 5 symbols analysis
python cli.py top 5

# List all tracked symbols
python cli.py symbols

# View recent signals
python cli.py signals

# Show system metrics
python cli.py metrics
```

### 🐳 Docker Deployment

```bash
# Start both Redis and SignalEngine
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Docker Health Checks:**
- Backend health endpoint checked every 30s
- Redis ping checked every 10s
- Auto-restart on failure

---

## API Reference

### Core Endpoints

| Method | Path | Description | Query Params |
|--------|------|-------------|--------------|
| `GET` | `/health` | Service health + uptime | - |
| `GET` | `/metrics` | Prometheus metrics | - |
| `GET` | `/metrics/legacy` | JSON metrics (legacy) | - |
| `GET` | `/symbols` | List tracked symbols | - |
| `GET` | `/signals` | Recent signals | `?symbol=BTCUSDT&limit=50` |
| `GET` | `/signals/stats` | Signal statistics | - |
| `GET` | `/events` | Recent events | `?symbol=BTCUSDT&type=oi_expansion&limit=100` |
| `GET` | `/events/stats` | Event statistics | - |

### Signal Endpoints

**GET /signals** - Retrieve recent signals
```bash
# Get last 50 signals
curl http://localhost:8000/signals?limit=50

# Get signals for specific symbol
curl http://localhost:8000/signals?symbol=BTCUSDT&limit=20
```

**Response:**
```json
{
  "signals": [
    {
      "id": 123,
      "symbol": "BTCUSDT",
      "direction": "long",
      "score": 0.6542,
      "timestamp": 1771244110.69,
      "entry_price": 50123.45,
      "tp_price": 51234.56,
      "sl_price": 49876.54,
      "atr": 234.56,
      "outcome": "tp_hit",
      "closed_at": 1771245678.12,
      "return_pct": 2.21
    }
  ],
  "count": 1
}
```

**GET /signals/stats** - Aggregate statistics
```json
{
  "total_signals": 482,
  "win_rate": 0.68,
  "avg_return": 1.45,
  "best_symbol": "BTCUSDT",
  "worst_symbol": "XRPUSDT"
}
```

### Performance Endpoints

**GET /performance/stats** - Per-symbol performance
```bash
curl http://localhost:8000/performance/stats
```

**Response:**
```json
{
  "BTCUSDT": {
    "total_signals": 45,
    "wins": 31,
    "losses": 14,
    "win_rate": 0.689,
    "avg_return": 1.82,
    "best_return": 5.43,
    "worst_return": -1.12,
    "sharpe_ratio": 1.54
  }
}
```

### WebSocket API

**Connect:** `ws://localhost:8000/ws/feed`

**Message Types:**

```javascript
// New signal
{
  "type": "signal",
  "data": {
    "symbol": "BTCUSDT",
    "direction": "long",
    "score": 0.6542,
    "entry_price": 50123.45,
    "tp_price": 51234.56,
    "sl_price": 49876.54,
    "timestamp": 1771244110.69
  }
}

// System status (every 10 seconds)
{
  "type": "status",
  "data": {
    "metrics": {
      "cpu_percent": 12.3,
      "signals_count": 482,
      "events_count": 1247
    }
  }
}

// Connection confirmed
{
  "type": "connected",
  "data": {
    "message": "Connected to signal feed",
    "timestamp": 1771244110.69
  }
}

// Keepalive (prevents timeout)
{
  "type": "keepalive"
}
```

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/feed');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'signal') {
    console.log('New signal:', msg.data);
  } else if (msg.type === 'status') {
    console.log('Status update:', msg.data.metrics);
  }
};
```

---

## Telegram Bot

### Automatic Signal Notifications

**All signals with score ≥50% are automatically sent to your configured Telegram chat.**

**Message Format:**
```
🟢 LONG BTCUSDT

📊 Score: 65.4%
💰 Entry: $50,123.45
🎯 TP: $51,234.56 (+2.21%)
🛡️ SL: $49,876.54 (-0.49%)

⏰ 2026-02-16 14:30:15 UTC
```

**When Signal Closes:**
```
✅ TP HIT - LONG BTCUSDT
Return: +2.21% | Duration: 45m

⏰ Closed: 2026-02-16 15:15:22 UTC
```

### Telegram Commands

Send these messages to your bot:

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and bot info |
| `/help` | List of available commands |
| `What's trending?` | AI analysis of top symbols (requires Ollama) |
| `Show me best futures tokens` | Alternative top symbols query |

### Manual Signal Sync

**Send historical signals to Telegram:**

```bash
# Send last 10 signals
python send_signal_to_telegram.py 10

# Send last 50 signals
python send_signal_to_telegram.py 50
```

This script:
- Fetches signals from database
- Formats them with enhanced template
- Sends to Telegram with 1-second rate limiting
- Shows success/failure count

---

## Project Structure

```
SignalEngine.v3/
├── app/                          # Backend (FastAPI + Python)
│   ├── main.py                   # FastAPI app + lifespan management
│   ├── __main__.py               # python -m app entry point
│   │
│   ├── core/                     # Core infrastructure
│   │   ├── config.py             # Pydantic settings from .env
│   │   ├── redis_pool.py         # Async Redis connection pool
│   │   ├── logger.py             # Structured JSON logging
│   │   ├── event_queue.py        # Shared async event queue
│   │   ├── monitoring.py         # CPU/memory + Prometheus metrics
│   │   └── websocket_broadcast.py # WebSocket multicast broadcaster
│   │
│   ├── collectors/               # Real-time data ingestion
│   │   ├── base.py               # WebSocket base with auto-reconnect
│   │   ├── handlers.py           # Binance stream parsers
│   │   ├── manager.py            # Collector lifecycle management
│   │   └── validation.py         # Data validation schemas
│   │
│   ├── features/                 # Technical indicators
│   │   ├── computations.py       # Pure feature functions (RSI, EMA, etc.)
│   │   └── engine.py             # Real-time feature computation loop
│   │
│   ├── events/                   # Event detection
│   │   └── engine.py             # Pattern detection → async queue
│   │
│   ├── signals/                  # Signal generation & management
│   │   ├── engine.py             # Database-first signal flow
│   │   ├── scoring.py            # Rule-based scoring (V1)
│   │   ├── tracker.py            # TP/SL/expiration tracking
│   │   └── on_demand_scorer.py   # Real-time scoring service
│   │
│   ├── telegram/                 # Telegram integration
│   │   ├── bot.py                # Worker with dedup + retry queue
│   │   ├── sender.py             # HTTP sender with rate limiting
│   │   └── query_handler.py      # AI query processing
│   │
│   ├── ai/                       # AI features (optional)
│   │   ├── inference.py          # Model inference (LightGBM/XGBoost)
│   │   └── ollama_client.py      # Ollama API client for chat
│   │
│   └── storage/                  # Data persistence
│       ├── database.py           # SQLite schema + CRUD operations
│       └── signal_log.py         # Signal persistence layer
│
├── frontend/                     # Next.js 15 UI (React 19)
│   ├── src/
│   │   ├── app/                  # App Router pages
│   │   │   ├── page.tsx          # Home dashboard
│   │   │   ├── signals/          # Signals table page
│   │   │   ├── chat/             # AI chat interface
│   │   │   └── dashboard/        # System metrics
│   │   │
│   │   ├── components/           # React components
│   │   │   ├── SignalsTable.tsx  # **Professional signals table**
│   │   │   ├── SignalTabs.tsx    # Tab filtering component
│   │   │   ├── Navigation.tsx    # Top navigation bar
│   │   │   └── ...
│   │   │
│   │   ├── contexts/             # React contexts
│   │   │   └── SignalContext.tsx # WebSocket + signal state management
│   │   │
│   │   ├── hooks/                # Custom React hooks
│   │   │   └── useWebSocket.ts   # **WebSocket client hook**
│   │   │
│   │   └── lib/                  # Utilities
│   │       ├── api-client.ts     # REST API client
│   │       └── types.ts          # TypeScript type definitions
│   │
│   ├── package.json              # npm dependencies
│   └── tsconfig.json             # TypeScript configuration
│
├── research/                     # Offline analysis (not in production)
│   ├── data/
│   │   └── loader.py             # Historical data download
│   ├── features/
│   │   └── builder.py            # Batch feature engineering
│   ├── training/
│   │   ├── trainer.py            # Model training
│   │   └── tracker.py            # Experiment tracking
│   ├── backtest/
│   │   └── engine.py             # Signal backtesting
│   └── models/                   # Exported model files
│
├── tests/                        # pytest test suite
│   ├── conftest.py               # Test fixtures
│   ├── test_computations.py
│   ├── test_scoring.py
│   ├── test_database.py
│   ├── test_event_queue.py
│   └── ...
│
├── data/                         # Runtime data (gitignored)
│   ├── db/
│   │   └── signalengine.db       # SQLite database (241 MB in your case)
│   └── signals/
│       └── signals_*.jsonl       # Daily signal logs
│
├── cli.py                        # Command-line interface
├── send_signal_to_telegram.py    # Manual Telegram sync script
├── check_unsent_signals.py       # Debug script for signal analysis
├── dashboard.html                # Classic HTML dashboard
├── open_dashboard.py             # Dashboard launcher
│
├── requirements.txt              # Python dependencies (production)
├── requirements-research.txt     # Python dependencies (research)
├── Dockerfile                    # Production Docker image
├── docker-compose.yml            # Docker stack (Redis + Backend)
├── pytest.ini                    # pytest configuration
├── .env                          # Configuration (not in git)
├── .gitignore                    # Git ignore patterns
└── README.md                     # This file
```

**Key Files:**
- [app/signals/engine.py](app/signals/engine.py#L227-L245) - Database-first signal flow
- [app/core/websocket_broadcast.py](app/core/websocket_broadcast.py#L46-L61) - WebSocket multicast
- [frontend/src/components/SignalsTable.tsx](frontend/src/components/SignalsTable.tsx) - Professional signals table
- [frontend/src/hooks/useWebSocket.ts](frontend/src/hooks/useWebSocket.ts) - WebSocket client
- [app/telegram/bot.py](app/telegram/bot.py#L410-L414) - Telegram worker with deduplication

---

## Data Storage

### SQLite (Persistent)

**Database:** `data/db/signalengine.db` (WAL mode, async via aiosqlite)

**Tables:**

1. **signals** - All emitted signals with full lifecycle tracking
   ```sql
   CREATE TABLE signals (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     timestamp REAL,
     symbol TEXT,
     direction TEXT,        -- 'long' or 'short'
     score REAL,
     entry_price REAL,
     tp_price REAL,         -- Take Profit target
     sl_price REAL,         -- Stop Loss target
     atr REAL,              -- ATR at signal time
     outcome TEXT,          -- NULL, 'tp_hit', 'sl_hit', 'expired'
     closed_at REAL,        -- Timestamp when closed
     return_pct REAL        -- Actual return percentage
   )
   ```

2. **events** - Market events that triggered analysis
   ```sql
   CREATE TABLE events (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     timestamp REAL,
     symbol TEXT,
     event_type TEXT,       -- 'oi_expansion', 'liquidation_cluster', etc.
     details TEXT           -- JSON metadata
   )
   ```

3. **signal_performance** - Aggregated performance metrics
   - Per-symbol win rates
   - Average returns
   - Sharpe ratios
   - Best/worst trades

**Database Size:** Can grow large with many signals (241 MB in active systems). Excluded from git via `.gitignore`.

### Redis (Real-Time Cache)

**Keys:**
- `{SYMBOL}:features` - Hash of latest technical indicators
- `{SYMBOL}:price` - Latest price data
- Signal pub/sub channels for real-time streaming

**Expiration:** Most keys have TTL to prevent memory bloat.

---

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "components": {
    "redis": "connected",
    "database": "ok",
    "websocket": "broadcasting",
    "telegram": "active"
  }
}
```

### Prometheus Metrics

**Endpoint:** `/metrics`

**Key Metrics:**
- `signals_emitted_total` - Total signals generated
- `signals_tp_hit_total` - Signals that hit TP
- `signals_sl_hit_total` - Signals that hit SL
- `telegram_sent_total` - Messages sent to Telegram
- `telegram_queue_size` - Current Telegram queue size
- `websocket_clients` - Connected WebSocket clients
- `cpu_percent` - CPU usage
- `memory_rss_bytes` - Memory usage

### Legacy JSON Metrics

**Endpoint:** `/metrics/legacy`

```json
{
  "system": {
    "cpu_percent": 12.3,
    "rss_mb": 85.4,
    "threads": 8,
    "uptime_seconds": 3600
  },
  "counters": {
    "events_triggered": 142,
    "signals_emitted": 23,
    "telegram_sent": 23,
    "signal_long": 12,
    "signal_short": 11
  },
  "gauges": {
    "signal_queue_size": 0,
    "telegram_queue_size": 0
  }
}
```

**Auto-Monitoring:**
- CPU warning when > 80%
- Memory warning when > 1 GB
- Queue size monitoring every 30 seconds

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ===== Core Settings =====
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
SQLITE_DB_NAME=signalengine.db          # Database filename
REDIS_URL=redis://localhost:6379/0      # Redis connection

# ===== Signal Generation =====
SIGNAL_SCORE_THRESHOLD=0.50             # Minimum score (0.0-1.0) to emit signal
SIGNAL_COOLDOWN_SECONDS=300             # Per-symbol cooldown (5 minutes)
SIGNAL_QUEUE_SIZE=10000                 # Max signals in queue (default: 10000)

# ===== Signal Lifecycle =====
SIGNAL_TP_MULTIPLIER=2.0                # TP = Entry ± (ATR × 2.0)
SIGNAL_SL_MULTIPLIER=1.0                # SL = Entry ± (ATR × 1.0)
SIGNAL_TTL_SECONDS=3600                 # Signals expire after 1 hour

# ===== Telegram Integration =====
TELEGRAM_BOT_TOKEN=1234567890:ABC...    # From @BotFather
TELEGRAM_CHAT_ID=-1003497403947         # Your chat/channel ID
TELEGRAM_RATE_LIMIT=1.0                 # Max messages per second

# ===== AI Features (Optional) =====
AI_ENABLED=false                        # Enable AI model inference
AI_MODEL_PATH=research/models/model.json
OLLAMA_BASE_URL=http://localhost:11434  # Ollama API endpoint
OLLAMA_MODEL=llama3.2:3b                # Model for chat queries

# ===== Monitoring =====
MONITOR_INTERVAL=30                     # System metrics poll (seconds)
ENABLE_PROMETHEUS=true                  # Expose /metrics endpoint
```

### Signal Scoring Parameters

**Rule-based scoring weights** (see [app/signals/scoring.py](app/signals/scoring.py)):

| Component | Weight | Description |
|-----------|--------|-------------|
| Trend (EMA slope) | 20% | Multi-timeframe trend alignment |
| Liquidation bias | 15% | Recent liquidation pressure |
| Volatility | 15% | Market volatility level |
| VWAP position | 10% | Price vs. VWAP |
| OI expansion | 15% | Open interest growth |
| Structure | 15% | Support/resistance levels |
| Event quality | 10% | Event strength and recency |

**Score Calculation:**
```python
score = (
    trend_score * 0.20 +
    liq_score * 0.15 +
    vol_score * 0.15 +
    vwap_score * 0.10 +
    oi_score * 0.15 +
    structure_score * 0.15 +
    event_score * 0.10
)

# Signal emitted if score >= SIGNAL_SCORE_THRESHOLD (default: 0.50)
```

### Technical Indicators Computed

1. **RSI** (14-period) - Momentum
2. **EMA** (9, 21, 50) - Trend direction
3. **VWAP** - Volume-weighted average price
4. **ATR** (14-period) - Volatility for TP/SL
5. **Bollinger Bands** - Volatility bands
6. **Volume Profile** - Volume distribution
7. **OI Delta** - Open interest change rate
8. **Liquidation Flow** - Buy/sell liquidation ratio
9. **Funding Rate** - Perpetual swap funding

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov aiosqlite

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_scoring.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "signal"
```

**Test Coverage:**
- ✅ Configuration loading and validation
- ✅ Feature computations (RSI, EMA, ATR, etc.)
- ✅ Signal scoring logic
- ✅ Database operations (CRUD, stats)
- ✅ Event queue functionality
- ✅ Monitoring metrics
- ✅ Tracker lifecycle management

---

## Research & Backtesting

The `research/` folder contains tools for offline analysis and model development:

### Setup Research Environment

```bash
# Install additional dependencies
pip install -r requirements-research.txt

# This includes: pandas, numpy, scikit-learn, lightgbm, xgboost, matplotlib, jupyter
```

### Download Historical Data

```python
import asyncio
from research.data.loader import bulk_download_klines, bulk_download_open_interest

# Download 90 days of 5-minute klines
asyncio.run(bulk_download_klines('BTCUSDT', '5m', days=90))

# Download 30 days of open interest data
asyncio.run(bulk_download_open_interest('BTCUSDT', '5m', days=30))
```

### Feature Engineering

```python
from research.features.builder import FeatureBuilder

builder = FeatureBuilder()
df = builder.build_features('BTCUSDT', start_date='2026-01-01', end_date='2026-02-01')

# Output: DataFrame with all 9 technical indicators
```

### Model Training

```python
from research.training.trainer import train_lightgbm

# Train model on historical data
model, metrics = train_lightgbm(
    train_data='research/data/train.parquet',
    features=['rsi', 'ema_9', 'ema_21', 'atr', 'oi_delta', 'vwap_dist'],
    target='signal_direction'
)

# Export for production use
model.save_model('research/models/model.json')
```

### Backtesting

```python
from research.backtest.engine import Backtester

backtester = Backtester(
    symbol='BTCUSDT',
    start_date='2026-01-01',
    end_date='2026-02-01',
    score_threshold=0.50
)

results = backtester.run()

print(f"Total Signals: {results['total_signals']}")
print(f"Win Rate: {results['win_rate']:.2%}")
print(f"Avg Return: {results['avg_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
```

---

## Debugging & Troubleshooting

### Common Issues

**1. Backend Won't Start**

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Check port 8000 is free
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac

# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip install -r requirements.txt
```

**2. UI Not Updating**

```bash
# Check WebSocket connection in browser console (F12)
# Should see: "WebSocket connected" (in dev mode only)

# Check backend logs for WebSocket errors
# Look for: "WebSocket broadcaster started"

# Verify frontend is connected to correct backend
# .env.local should have: NEXT_PUBLIC_API_URL=http://localhost:8000
```

**3. Signals Not Sending to Telegram**

```bash
# Check Telegram credentials in .env
# TELEGRAM_BOT_TOKEN should start with a number
# TELEGRAM_CHAT_ID should be number or -100... for channels

# Check backend logs for Telegram worker
# Should see: "Telegram worker started (main + retry)"

# Test with manual send
python send_signal_to_telegram.py 1

# Check for errors
# Common: "Unauthorized" means wrong token
# Common: "Chat not found" means wrong chat ID
```

**4. Database Issues**

```bash
# Check database exists
ls data/db/signalengine.db  # Linux/Mac
dir data\db\signalengine.db # Windows

# Delete and recreate (WARNING: loses all data)
rm data/db/signalengine.db*
# Restart backend to recreate

# Query database directly
sqlite3 data/db/signalengine.db
# sqlite> SELECT COUNT(*) FROM signals;
# sqlite> .exit
```

### Debug Scripts

**Check Unsent Signals:**
```bash
python check_unsent_signals.py
```
- Shows recent 100 signals from database
- Groups by symbol to identify patterns
- Displays signal details for debugging

**Analyze Signal Hashes:**
```bash
python debug_telegram_signals.py
```
- Shows unique signal hashes in database
- Helps debug deduplication issues

**View Backend Logs:**
```bash
# Real-time log viewing (if running in background)
docker-compose logs -f  # Docker
tail -f logs/signalengine.log  # If logging to file

# Or run backend in foreground to see logs directly
python -m app
```

### Performance Optimization

**High CPU Usage:**
- Reduce `MONITOR_INTERVAL` to 60+ seconds
- Disable Prometheus if not needed: `ENABLE_PROMETHEUS=false`
- Reduce number of tracked symbols in collectors

**High Memory Usage:**
- Reduce `SIGNAL_QUEUE_SIZE` if not needed
- Clear Redis periodically: `redis-cli FLUSHDB`
- Archive old database records

**Slow Database Queries:**
```sql
-- Add indexes for common queries
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_timestamp ON signals(timestamp);
CREATE INDEX idx_signals_outcome ON signals(outcome);
```

---

## Recent Changes

### v3.2 (February 2026) - Database-First Architecture

**Major Changes:**
1. **Database-First Signal Flow**
   - Signals saved to SQLite before delivery
   - Ensures zero data loss even if delivery fails
   - See: [app/signals/engine.py](app/signals/engine.py#L228)

2. **WebSocket Multicast Pattern**
   - WebSocket broadcast no longer consumes from signal queue
   - Signals now multicast to both UI and Telegram
   - Fixes: UI not updating, Telegram missing signals
   - See: [app/core/websocket_broadcast.py](app/core/websocket_broadcast.py#L46-L56)

3. **10x Queue Capacity Increase**
   - Signal queue: 500 → 10,000 signals
   - Prevents drops during high-volume market periods
   - See: [app/signals/engine.py](app/signals/engine.py#L45)

4. **Enhanced Telegram Formatting**
   - Shows outcome (TP Hit, SL Hit, Expired)
   - Includes duration and return percentage
   - Emoji indicators: 🟢 (TP), 🔴 (SL), ⏱️ (Expired)
   - See: [app/telegram/bot.py](app/telegram/bot.py#L320-L397)

5. **Professional Signals Table**
   - 8-column table with real-time sorting
   - Tab filtering: All, Open, Closed, TP Hit, SL Hit, Expired
   - Color-coded status indicators
   - Auto-updates via WebSocket (no refresh)
   - See: [frontend/src/components/SignalsTable.tsx](frontend/src/components/SignalsTable.tsx)

6. **Deduplication Fix**
   - Changed from time-window hashing to exact timestamp
   - Prevents false duplicates on sub-minute signals
   - Hash now: `MD5(symbol:direction:timestamp:score)`
   - See: [app/telegram/bot.py](app/telegram/bot.py#L410-L414)

7. **Queue Monitoring**
   - Debug logs show queue size and capacity
   - Helps identify bottlenecks and drops
   - Metrics exposed via `/metrics` endpoint

**Breaking Changes:**
- None - all changes backward compatible

**Migration:**
- No migration needed for existing databases
- New columns auto-created on first run
- Existing signals remain unchanged

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## Support

**Issues:** Report bugs via GitHub Issues
**Questions:** Use GitHub Discussions
**Security:** Email security issues privately

---

## Acknowledgments

- **Binance API** - Real-time market data
- **FastAPI** - Modern Python web framework
- **Next.js** - React framework for production
- **Ollama** - Local AI inference
- **python-telegram-bot** - Telegram integration
- **Redis** - High-performance caching
- **SQLite** - Reliable embedded database

---

**Built with ❤️ for cryptocurrency traders**
