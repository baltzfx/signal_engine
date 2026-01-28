# 📊 Signal Engine

Advanced cryptocurrency trading signal generator with multi-timeframe analysis, confidence scoring, and automated notifications.

## 🎯 Features

### Core Features
- **Multi-Timeframe Analysis**: Combines 1H and 4H timeframes for trend confirmation
- **Enhanced Technical Indicators**: EMA, RSI, MACD, Bollinger Bands, Stochastic, ATR, Volume
- **Quality Filters**: Liquidity, spread, and funding rate filters
- **⭐ Advanced Confidence Scoring**: Weighted scoring system (0-100%) with 9 factors
- **Signal Tracking**: Monitors open signals and evaluates outcomes
- **Telegram Notifications**: Real-time signal alerts via Telegram
- **Automated Scanning**: Configurable interval-based market scanning

### Advanced Features (Enhanced Strategy)
- **Market Regime Detection**: Identifies trending/ranging/volatile conditions
- **Support/Resistance Levels**: Key level detection for better entries
- **Divergence Detection**: Bullish/bearish divergence signals
- **Dynamic Stop Loss/TP**: ATR-based and S/R-aware position sizing
- **Multi-Indicator Confluence**: Requires 7/10 conditions for signals
- **Backtesting Framework**: Test strategies on historical data

## 📁 Project Structure

```
signal-engine/
├── app/
│   ├── main.py                 # Application entry point
│   ├── config/                 # Configuration and settings
│   ├── data/                   # Market data fetching and caching
│   ├── indicators/             # Technical indicators (EMA, RSI, Volume)
│   ├── strategy/               # Trading strategy logic and filters
│   ├── scoring/                # Confidence scoring system
│   ├── signals/                # Signal generation and validation
│   ├── notifier/               # Telegram notifications
│   ├── tracking/               # Signal tracking and outcomes
│   └── utils/                  # Utilities (logging, time)
├── tests/                      # Unit tests
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Docker configuration
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Binance API credentials (read-only)
- Telegram Bot Token and Chat ID

### Installation

1. **Clone and navigate to directory**
   ```bash
   cd signal-engine
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

4. **Run the engine**
   ```bash
   python -m app.main
   ```

### Docker Deployment

```bash
docker-compose up -d
```

## ⚙️ Configuration

Edit `.env` file:

```env
# Binance API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret

# Trading Pairs
TRADING_PAIRS=BTCUSDT,ETHUSDT,SOLUSDT

# Confidence Threshold
MIN_CONFIDENCE_SCORE=70

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Scan Interval (seconds)
SCAN_INTERVAL_SECONDS=300
```

## 📈 Strategy Logic

### Signal Generation (Enhanced Strategy)

**Requires 7 out of 10 conditions for higher accuracy:**

**LONG Signal Conditions:**
1. ✅ Market regime: Trending up with >60% confidence
2. ✅ 4H timeframe in uptrend (price > EMA 200)
3. ✅ 1H bullish EMA crossover or uptrend
4. ✅ RSI 20-65 (momentum without overbought)
5. ✅ MACD bullish cross or positive histogram
6. ✅ Stochastic not overbought (<80)
7. ✅ Volume spike or above average
8. ✅ Bollinger Bands: near lower band or mid-range
9. ✅ S/R: near support or not near resistance
10. ✅ Divergence: bullish or neutral

**SHORT Signal Conditions:**
1. ✅ Market regime: Trending down with >60% confidence
2. ✅ 4H timeframe in downtrend
3. ✅ 1H bearish EMA crossover or downtrend
4. ✅ RSI 35-80 (moment (Enhanced)

Advanced weighted scoring system (0-100%) with 9 factors:
- **Trend Alignment (20%)**: Multi-timeframe trend confirmation
- **Momentum (15%)**: RSI and MACD positioning
- **Volume (15%)**: Volume spikes and patterns
- **Market Regime (15%)**: Favorable trending conditions
- **Liquidity (10%)**: Market liquidity quality
- **S/R Alignment (10%)**: Position relative to key levels
- **Funding (5%)**: Funding rate health
- **Divergence (5%)**: Price/indicator divergence
- **Confluence (5%)**: Multi-indicator agreement

Only signals with confidence ≥ 75% threshold are sent (adjustable)
1. **Liquidity Filter**: Min 24h volume of $1M
2. **Spread Filter**: Max 0.1% bid-ask spread
3. **Funding Filter**: No extreme funding rates

### Confidence Scoring

Weighted scoring system (0-100%):
- **Trend Alignment (30%)**: Multi-timeframe trend confirmation
- **Momentum (25%)**: RSI positioning
- **Volume (20%)**: Volume spikes and patterns
- **Liquidity (15%)**: Market liquidity quality
- **Funding (10%)**: Funding rate health

Only signals with confidence ≥ threshold are sent.

## 📊 Signal Tracking

The engine automatically tracks:
- Open signal positions
- Real-time PnL (Enhanced Strategy):
- **Dynamic Stop Loss**: 1.5-2.5x ATR based on volatility
- **Dynamic Take Profit**: 2.5-4.0x ATR based on conditions
- **S/R-Aware**: Adjusts stops/targets based on key levels
- **Risk/Reward Ratio**: Minimum 1.5:1, typically 2-3:1
- **Expiry**
Default targets:
- Profit Target: +2%
- Stop Loss: -1%
- Expiry: 72 hours

## 🔔 Notifications

Telegram notifications include:
- Signal type (LONG/SHORT)
- Entry price
- Confidence score
- Key indicators (RSI, volume)
- Timestamp

## 🧪 Testing

Run unit tests:
```bash
pytest tests/ -v
```

Test specific modules:
```bash
pytest tests/test_indicators.py -v
pytest tests/test_strategy.py -v
```

## 📝 Logging

Logs are written to:
- Console (stdout)
- `logs/signal-engine.log`

Configure log level in `.env`:
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## 🔒 Security Notes

- Never commit `.env` file with real credentials
- Use read-only API keys (no trading permissions needed)
- Keep Telegram bot token secure
- Review signals before trading (for educational purposes)

## ⚠️ Disclaimer

This signal engine is for **educational and informational purposes only**. 

- Not financial advice
- Trading cryptocurrencies involves significant risk
- Past performance does not guarantee future results
- Always do your own research (DYOR)
- Never invest more than you can afford to lose

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review test files for usage examples

---

**Happy Trading! 📈**
