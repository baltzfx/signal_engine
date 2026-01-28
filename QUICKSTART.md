# 🚀 Quick Start Guide

## Prerequisites

- Python 3.9 or higher
- Binance account with API access
- Telegram Bot Token and Chat ID

---

## Step 1: Install Dependencies

```bash
cd signal-engine
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**

### Required Settings:

```env
# Binance API (Read-only recommended)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_secret_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### How to Get Credentials:

**Binance API:**
1. Go to Binance.com → API Management
2. Create new API Key
3. Enable "Enable Reading" ONLY (no trading permissions)
4. Copy Key and Secret

**Telegram Bot:**
1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token
4. Message your bot
5. Get your chat ID from `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`

---

## Step 3: Initialize Database

The database will be created automatically on first run at:
```
signal-engine/signals.db
```

Or manually initialize:
```bash
python -c "from app.database.connection import init_db; init_db()"
```

---

## Step 4: Run the Signal Engine

```bash
python -m app.main
```

You should see:
```
INFO - Initializing database...
INFO - Database tables created successfully
INFO - Database initialized
INFO - Using Enhanced Strategy
INFO - Signal Engine started
INFO - Starting market scan...
```

---

## Step 5: Verify It's Working

1. Check Telegram - you should receive signals within 5-10 minutes
2. Check database:
   ```bash
   sqlite3 signals.db "SELECT * FROM signals;"
   ```
3. Check health endpoint (if running):
   ```bash
   curl http://localhost:8080/health
   ```

---

## Optional Configurations

### Adjust Confidence Threshold
```env
MIN_CONFIDENCE_SCORE=75  # Default, try 70-85
```

### Add More Trading Pairs
```env
TRADING_PAIRS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT
```

### Adjust Scan Interval
```env
SCAN_INTERVAL_SECONDS=300  # 5 minutes (default)
```

### Change Log Level
```env
LOG_LEVEL=INFO  # DEBUG for more details
```

---

## Troubleshooting

**No signals being generated?**
- Check if enhanced strategy is enabled: `USE_ENHANCED_STRATEGY=true`
- Lower confidence threshold: `MIN_CONFIDENCE_SCORE=70`
- Check logs for errors

**Database errors?**
- Delete `signals.db` and restart
- Check file permissions

**Telegram not working?**
- Verify bot token and chat ID
- Make sure you've messaged the bot first
- Check Telegram firewall settings

**Binance API errors?**
- Verify API keys are correct
- Check API key has "Enable Reading" permission
- Ensure IP whitelist is configured (if set)

---

## Database Schema

The system creates 3 tables:

1. **signals** - All generated signals with outcomes
2. **rejected_signals** - Signals that didn't pass filters
3. **performance_metrics** - Daily performance tracking

---

## Next Steps

1. **Paper trade for 1 month** - Track all signals
2. **Monitor win rate** - Should be 55-65%
3. **Adjust confidence** - Fine-tune threshold
4. **Review rejected signals** - Optimize filters

---

## Running in Production

### Using Docker:
```bash
docker-compose up -d
```

### Using systemd (Linux):
Create `/etc/systemd/system/signal-engine.service`:
```ini
[Unit]
Description=Crypto Signal Engine
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/signal-engine
ExecStart=/usr/bin/python3 -m app.main
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable signal-engine
sudo systemctl start signal-engine
```

---

## Support

- Check logs: `logs/signal-engine.log`
- Monitor database: `sqlite3 signals.db`
- Review rejected signals for tuning
- Adjust confidence threshold based on results

**Good luck! 🚀**
