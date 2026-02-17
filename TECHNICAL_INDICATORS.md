Technical Indicators & Features Used in SignalEngine v3
📊 Core Technical Indicators
1. Trend Indicators
EMA (Exponential Moving Average)
Fast EMA: 9 periods (default)
Slow EMA: 21 periods (default)
EMA Slope: Measures trend direction and strength (normalized)
Positive slope → Uptrend | Negative slope → Downtrend
2. Volatility Indicators
ATR (Average True Range): 14 periods
Measures market volatility
Used for TP/SL calculations (2.0× ATR for TP, 1.0× ATR for SL)
Candle Range Expansion
Ratio of current candle range vs average range
Detects volatility spikes
3. Volume/Price Indicators
VWAP (Volume Weighted Average Price): 20 periods
VWAP Distance: % distance from VWAP
Price above VWAP = Bullish | Below VWAP = Bearish
🏗️ Market Structure Features
4. Market Structure
Higher Highs / Lower Lows (HH/LL)
Higher Lows / Lower Highs (HL/LH)
State Detection: Uptrend, Downtrend, or Neutral
Breakout Detection: 20-period lookback
Bullish breakout (above resistance)
Bearish breakout (below support)
📈 Derivatives-Specific Features
5. Open Interest (OI)
OI Delta: % change over 10 samples
OI Expansion: Confirms trend strength
OI Contraction: Weakens signal
6. Funding Rate
Funding Z-Score: 50-period rolling window
Extreme funding → Potential reversal
Positive funding = Longs paying shorts
Negative funding = Shorts paying longs
7. Liquidations
Liquidation Ratio: Long vs Short liquidations (20 window)
Ratio > 1.3 → More longs liquidated (Bearish)
Ratio < 0.7 → More shorts liquidated (Bullish)
Total USD Liquidated: Volume indicator
Liquidation Spike Detection (Z-score based)
📖 Order Book Features
8. Orderbook Imbalance
Range: -1 (all asks) to +1 (all bids)
Threshold: 30% skew
Measures buy/sell pressure
9. Wall Pressure Detection
Detects large "whale" orders
Threshold: 5× mean order size
Identifies bid/ask walls with price levels
⚙️ Multi-Timeframe Analysis (MTF)
10. Timeframe Analysis
Timeframes: 1m, 5m, 15m, 1h
Primary Timeframe: 5m (for signal generation)
MTF Alignment: Requires minimum 2 timeframes aligned
MTF Score: Weighted consensus across timeframes
🎯 Event Detection System
The system detects 6 types of market events:

Liquidation Spike - Unusual liquidation activity
OI Expansion - Rapid open interest growth
ATR Expansion - Volatility spike (1.5× threshold)
Structure Breakout - Price breaking key levels
Orderbook Flip - Imbalance reversal (20% change)
Funding Extreme - Extreme funding rate (2.5 Z-score)
📐 Signal Scoring Weights
The system uses a weighted scoring model (0-1 scale):

Component	Weight
Trend (EMA slope)	20%
Liquidation bias	15%
Volatility expansion	15%
VWAP position	10%
OI expansion	15%
Structure (HH/LL + Breakout)	15%
Event Quality	10%
Total Score Required: ≥ 50% (configurable)

🔄 Real-Time Features
Current Price: Mark price (primary) or Kline close (fallback)
Real-Time P&L: Live profit/loss calculation for open signals
Price Updates: Every 1-10 seconds depending on source
TP/SL Tracking: Continuous monitoring every 1 second
⏰ Timeframes & Windows
ATR Period: 14 candles
VWAP Period: 20 candles
Funding Z-Score: 50 samples
OI Delta: 10 samples
Liquidation Ratio: 20 liquidations
Structure Lookback: 20 candles
Signal TTL: 6 hours (21,600 seconds)
All these features work together to generate high-confidence trading signals with multi-dimensional market analysis! 🎯📊