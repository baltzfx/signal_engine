import asyncio
import sys
sys.path.insert(0, 'C:/Projects/SignalEngine.v3')

from app.signals.tracker import get_all_open_signals

# Get all active signals
signals = get_all_open_signals()

print(f"\n=== {len(signals)} Active Signals ===\n")
for sig in signals:
    print(f"Symbol: {sig['symbol']}")
    print(f"Direction: {sig['direction'].upper()}")
    print(f"Entry: ${sig['entry_price']:.4f}")
    print(f"TP: ${sig['tp_price']:.4f}")
    print(f"SL: ${sig['sl_price']:.4f}")
    print(f"Score: {sig['score']*100:.1f}%")
    print(f"Age: {sig.get('age_seconds', 0):.0f} seconds")
    print(f"ATR: ${sig['atr']:.6f}")
    print("-" * 50)
