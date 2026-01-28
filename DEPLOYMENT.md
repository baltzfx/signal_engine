# Deployment Guide

## Deploy to Render (Recommended for Production)

### Prerequisites
- GitHub account
- Render account (free tier available)
- Binance API keys
- Telegram bot token

### Steps:

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/signal-engine.git
   git push -u origin main
   ```

2. **Create Render Service**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Background Worker"
   - Connect your GitHub repository
   - Select "signal-engine"

3. **Configure Service**
   - **Name**: signal-engine
   - **Environment**: Docker
   - **Region**: Choose closest to you
   - **Instance Type**: Free
   - **Docker Command**: `python -m app.main`

4. **Add Environment Variables**
   Go to Environment tab and add:
   ```
   BINANCE_API_KEY=your_key_here
   BINANCE_API_SECRET=your_secret_here
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   TRADING_PAIRS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT
   MIN_CONFIDENCE_SCORE=70
   SCAN_INTERVAL_SECONDS=300
   LOG_LEVEL=INFO
   ```

5. **Add Disk Storage** (for SQLite database)
   - Go to "Disks" tab
   - Add disk: `/opt/render/project/src/data`
   - Size: 1GB (free tier)

6. **Deploy**
   - Click "Create Background Worker"
   - Render will build and deploy automatically
   - Check logs to verify it's running

### Update Dockerfile for Render

The current Dockerfile should work, but ensure it has:
```dockerfile
# Create data directory for SQLite
RUN mkdir -p /app/data

# Set working directory
WORKDIR /app
```

---

## Deploy to Replit (Development/Testing Only)

### Steps:

1. **Import to Replit**
   - Go to [replit.com](https://replit.com)
   - Click "Create Repl"
   - Import from GitHub
   - Paste your repository URL

2. **Configure Secrets**
   - Click "Secrets" (lock icon)
   - Add all environment variables from `.env`

3. **Update .replit file**
   Create `.replit`:
   ```toml
   run = "python -m app.main"
   language = "python3"
   
   [nix]
   channel = "stable-22_11"
   
   [deployment]
   run = ["python", "-m", "app.main"]
   ```

4. **Keep Alive Service** (Required for free tier)
   - Use UptimeRobot or similar to ping every 5 minutes
   - Add health check endpoint first

5. **Run**
   - Click "Run" button
   - Monitor console for signals

### ⚠️ Replit Limitations
- Free tier sleeps after 1 hour of inactivity
- Requires external monitoring to stay alive
- Less reliable for production use
- Database resets on container restart (need to use Replit DB instead)

---

## Recommended: Use Render

For a production trading signal engine that needs 24/7 uptime, **Render is strongly recommended** over Replit.

## Monitoring

After deployment, monitor:
- Logs for signal generation
- Telegram messages
- Database size
- API rate limits

## Cost

Both offer free tiers:
- **Render**: Free background worker (750 hours/month)
- **Replit**: Free tier with limitations

For continuous operation, Render's free tier is more suitable.
