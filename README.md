# SignalEngine v3 — AI-Powered Futures Analysis Bot

AI-powered cryptocurrency futures analysis system with Telegram bot interface.
Uses real-time technical analysis and Ollama AI for intelligent market insights.

> **🎉 NEW: Modern Chat UI!** The system now includes a beautiful Next.js chat interface for real-time signal monitoring and AI queries. See [Next.js Chat UI](#3-nextjs-chat-ui) section below or check [frontend/README.md](frontend/README.md).

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
                                                         │  Signal   │────► SQLite
                                                         │  Engine   │
                                                         └─────┬─────┘
                                                               │
                                                   ┌───────────┴───────────┐
                                                   │                       │
                                             ┌─────▼─────┐          ┌─────▼─────┐
                                             │ Telegram   │          │ Monitoring│
                                             │    Bot     │          │  System   │
                                             └─────┬─────┘          └───────────┘
                                                   │
                                                   ▼
                                             ┌─────▼─────┐
                                             │   Ollama  │
                                             │     AI    │
                                             └───────────┘
```

## Features

### Core Features
- **Real-time Data Collection**: WebSocket streams from Binance Futures
- **Multi-Timeframe Analysis**: 1m, 5m, 15m, 1h timeframe confluence
- **Technical Analysis**: 9+ technical indicators computed in real-time
- **AI-Powered Insights**: Ollama integration for intelligent analysis
- **Signal Lifecycle Tracking**: Automated TP/SL management with outcome tracking
- **Performance Metrics**: Win rate, returns, Sharpe ratio per symbol
- **REST API**: Programmatic access to analysis results

### New in v3.1 (Enhanced)
- ✨ **Multi-Timeframe Confirmation**: Signals require alignment across multiple timeframes
- 📊 **Prometheus Metrics**: Production-grade monitoring and observability
- 📈 **Performance Tracking**: Detailed signal outcome analytics and historical performance
- 🎯 **Feature Importance**: Track which features drive AI model decisions
- 🔴 **Real-Time WebSocket API**: Live signal streaming to connected clients
- 🌐 **Enhanced Dashboard**: Modern real-time web interface with live updates

See [ENHANCEMENTS_SUMMARY.md](ENHANCEMENTS_SUMMARY.md) for detailed information.

## Quick Start

### Prerequisites
- Python 3.11+
- Redis server running on localhost:6379
- [Ollama](https://ollama.ai/) installed and running locally
- Telegram bot token (optional, for bot functionality)

### Install & Setup

```bash
# Clone & enter project
cd SignalEngine.v3

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Ollama model (recommended: llama3.2:3b)
ollama pull llama3.2:3b

# Copy env template
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac

# Edit .env with your settings:
# - TELEGRAM_BOT_TOKEN=your_bot_token_here
# - TELEGRAM_ALLOWED_CHAT_IDS=["123456789"]  # Your chat ID
# - OLLAMA_MODEL=llama3.2:3b

# Start the engine
uvicorn app.main:app --host 0.0.0.0 --port 8000
# or
python -m app
```

### Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Start a chat with your bot and send a message
4. Get your chat ID from the API or use a bot like [@userinfobot](https://t.me/userinfobot)
5. Add the token and chat ID to your `.env` file

### User Interface Options

SignalEngine provides multiple interfaces for different use cases:

#### 1. Real-Time Dashboard (NEW - Recommended)
Modern WebSocket-powered dashboard with live updates:

```bash
# Start the engine
python -m app

# Open in browser
open http://localhost:8000/dashboard_realtime.html
```

Features:
- ⚡ **Real-Time Updates**: Signals appear instantly via WebSocket
- 📊 **Live Stats**: Win rate, returns, CPU usage updated in real-time
- 🎯 **MTF Indicators**: Multi-timeframe alignment visualization
- 🔔 **Toast Notifications**: Pop-up alerts for new signals
- 📱 **Responsive Design**: Works on desktop and mobile
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations

#### 2. Classic Dashboard
Static HTML dashboard with manual refresh:

```bash
# Open dashboard in browser
python open_dashboard.py
# or manually open dashboard.html in your browser
```

Features:
- ✅ Real-time system health monitoring
- ✅ Top symbols analysis with AI insights
- ✅ Interactive market queries
- ✅ Recent signals history
- ✅ System metrics dashboard

#### 3. Next.js Chat UI
Modern chat-like interface with real-time signal notifications and AI queries:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000
```

Features:
- 💬 Chat-like interface with AI
- 🔴 Real-time WebSocket signal streaming
- 📊 Beautiful signal cards with price levels
- 📈 Performance metrics sidebar
- 🎨 Modern, responsive design
- 🔧 System metrics visualization

#### 3. Command Line Interface
A powerful CLI for automation and scripting:

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

### Docker

```bash
docker-compose up --build
```

This starts both Redis and the engine. Health checks are configured automatically.

### Health Check

```
GET http://localhost:8000/health
```

## API Endpoints

### Core Endpoints
| Method | Path              | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | `/health`         | Service health + uptime                  |
| GET    | `/metrics`        | Prometheus metrics (for monitoring)      |
| GET    | `/metrics/legacy` | JSON metrics (backward compatible)       |
| GET    | `/symbols`        | List of tracked symbols                  |
| GET    | `/dashboard`      | Dashboard summary with recent data       |

### Signal Endpoints
| Method | Path              | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | `/signals`        | Recent signals (query: `?symbol=&limit=`)|
| GET    | `/signals/stats`  | Aggregate signal statistics              |

### Event Endpoints
| Method | Path              | Description                              |
|--------|-------------------|------------------------------------------|
| GET    | `/events`         | Recent events (query: `?symbol=&type=`)  |
| GET    | `/events/stats`   | Aggregate event statistics               |

### Performance & Analytics (NEW)
| Method | Path                              | Description                              |
|--------|-----------------------------------|------------------------------------------|
| GET    | `/performance/stats`              | Signal performance by symbol (win rate, avg return, etc.) |
| GET    | `/performance/feature-importance` | AI model feature importance scores       |

### AI Query Endpoints
| Method | Path                  | Description                              |
|--------|----------------------|------------------------------------------|
| GET    | `/query/top-symbols` | AI analysis of top symbols (query: `?count=5`) |
| GET    | `/query/custom`      | Custom AI query (query: `?query=...`)    |

### WebSocket (NEW)
| Protocol | Path        | Description                              |
|----------|-------------|------------------------------------------|
| WS       | `/ws/feed`  | Real-time signal and status feed         |

#### WebSocket Message Types:
```javascript
// New signal
{"type": "signal", "data": {...}}

// System status update
{"type": "status", "data": {"metrics": {...}}}

// Connection confirmed
{"type": "connected", "data": {...}}

// Keepalive
{"type": "keepalive"}
```

## Telegram Bot Commands

Send messages to your bot:

- **"What's the top symbols for futures now?"** - Get AI analysis of top performing symbols
- **"Show me the best futures tokens"** - Alternative query for top symbols
- **"/help"** - Show available commands
- **"/start"** - Welcome message

The bot uses Ollama AI to provide intelligent analysis of real-time market data.

## Project Structure

```
app/
├── main.py                 # FastAPI entry-point + lifespan
├── __main__.py             # python -m app support
├── core/
│   ├── config.py           # Pydantic settings (env + defaults)
│   ├── redis_pool.py       # Async Redis connection pool
│   ├── logger.py           # Structured JSON logging
│   ├── event_queue.py      # Shared async event queue
│   └── monitoring.py       # CPU/memory + counters/gauges
├── collectors/
│   ├── base.py             # WebSocket base with auto-reconnect
│   ├── handlers.py         # Stream-specific parsers → Redis
│   └── manager.py          # Start/stop all collectors
├── features/
│   ├── computations.py     # Pure feature functions
│   └── engine.py           # Background feature loop
├── events/
│   └── engine.py           # Event detection → async queue → SQLite
├── signals/
│   ├── scoring.py          # Rule-based scoring (V1)
│   └── engine.py           # Signal consumer + emission
├── telegram/
│   └── sender.py           # Async sender with dedup + retry
├── ai/
│   └── inference.py        # LightGBM/XGBoost inference (V2, GPU/CPU)
└── storage/
    ├── signal_log.py       # JSONL + Redis + SQLite signal persistence
    └── database.py         # SQLite schema, CRUD, stats queries

research/                    # Offline — never runs in production
├── data/
│   └── loader.py           # Klines, OI, funding, liquidation download
├── features/
│   └── builder.py          # Batch feature engineering (9 features)
├── training/
│   ├── trainer.py          # LightGBM / XGBoost training
│   └── tracker.py          # SQLite experiment tracker
├── backtest/
│   └── engine.py           # Signal backtester
└── models/                  # Exported model files

tests/                       # pytest test suite
├── conftest.py
├── test_config.py
├── test_computations.py
├── test_scoring.py
├── test_database.py
├── test_event_queue.py
└── test_monitoring.py

Dockerfile                   # python:3.11-slim production image
docker-compose.yml           # Engine + Redis stack
```

## Storage

### Redis (real-time)
- Feature hashes (`SYMBOL:features`), signal lists, event pub/sub

### SQLite (persistent)
- `signals` — every emitted signal with score, direction, features snapshot
- `events` — every triggered event with type, detail JSON
- `feature_snapshots` — point-in-time feature records for replay

Database is stored at `data/db/signalengine.db` (WAL mode, async via aiosqlite).

## Monitoring

The `/metrics` endpoint returns:

```json
{
  "system": {"cpu_percent": 12.3, "rss_mb": 85.4, "threads": 8, "uptime_seconds": 3600},
  "counters": {"events_triggered": 142, "signals_emitted": 23, "telegram_sent": 23},
  "gauges": {}
}
```

Background loop warns when CPU > 80% or RSS > 1 GB.

## Version 1 — Rule-Based Signals

Signals are generated when events align across multiple dimensions:

| Component          | Weight |
|--------------------|--------|
| Trend (EMA slope)  | 20%    |
| Liquidation bias   | 15%    |
| Volatility         | 15%    |
| VWAP position      | 10%    |
| OI expansion       | 15%    |
| Structure          | 15%    |
| Event quality      | 10%    |

A signal fires only when `score ≥ 0.60` (configurable).

## Version 2 — AI Upgrade

1. Train a model in the `research/` environment
2. Export to `research/models/model.json`
3. Set `AI_ENABLED=true` and `AI_MODEL_PATH` in `.env`
4. Restart the engine

The AI layer runs inference via `run_in_executor` (non-blocking) with automatic GPU/CPU fallback.

## Configuration

All settings are in `app/core/config.py` and overridable via `.env`:

| Variable                   | Default              | Description                     |
|----------------------------|----------------------|---------------------------------|
| `REDIS_URL`                | redis://localhost:6379/0 | Redis connection URL        |
| `SIGNAL_SCORE_THRESHOLD`   | 0.60                 | Minimum score to emit signal    |
| `SIGNAL_COOLDOWN_SECONDS`  | 300                  | Per-symbol cooldown             |
| `TELEGRAM_BOT_TOKEN`       | (empty)              | Telegram bot API token          |
| `TELEGRAM_CHAT_ID`         | (empty)              | Target chat/channel ID          |
| `AI_ENABLED`               | false                | Enable AI inference layer       |
| `SQLITE_DB_NAME`           | signalengine.db      | SQLite database filename        |
| `MONITOR_INTERVAL`         | 30                   | System metrics poll (seconds)   |
| `LOG_LEVEL`                | INFO                 | Logging verbosity               |

## Testing

```bash
pip install pytest pytest-asyncio aiosqlite
pytest
```

## Research Environment

```bash
pip install -r requirements-research.txt

# Download historical data
python -c "
import asyncio
from research.data.loader import bulk_download_klines, bulk_download_open_interest
asyncio.run(bulk_download_klines('BTCUSDT', '5m', days=90))
asyncio.run(bulk_download_open_interest('BTCUSDT', '5m', days=30))
"

# Then use Jupyter or scripts in research/ for feature engineering,
# training, and backtesting.
```
