"""
Signal Engine - Main Entry Point
Scheduler and worker for crypto trading signal generation
"""
import asyncio
import logging
from datetime import datetime

from config.settings import settings
from data.binance_client import BinanceClient
from signals.generator import SignalGenerator
from notifier.telegram import TelegramNotifier
from tracking.open_signals import OpenSignalsTracker
from utils.logger import setup_logger
from database.connection import init_db


logger = setup_logger(__name__)


class SignalEngine:
    """Main signal engine orchestrator"""
    
    def __init__(self):
        self.binance_client = BinanceClient()
        self.signal_generator = SignalGenerator()
        self.notifier = TelegramNotifier()
        self.tracker = OpenSignalsTracker()
        
    async def run_scan(self):
        """Execute a full market scan for all configured pairs"""
        logger.info("Starting market scan...")
        
        try:
            signals = []
            scanned = 0
            for symbol in settings.TRADING_PAIRS:
                signal = await self.signal_generator.generate_signal(symbol)
                scanned += 1
                if signal:
                    signals.append(signal)
                    
            if signals:
                logger.info(f"Generated {len(signals)} new signals (scanned {scanned} pairs)")
                await self.notifier.send_signals(signals)
                await self.tracker.save_signals(signals)
            else:
                logger.info(f"No new signals generated (scanned {scanned} pairs)")
                
        except Exception as e:
            logger.error(f"Error during scan: {e}", exc_info=True)
    
    async def update_tracking(self):
        """Update outcomes for open signals"""
        try:
            await self.tracker.update_outcomes()
        except Exception as e:
            logger.error(f"Error updating tracking: {e}", exc_info=True)
    
    async def run_scheduler(self):
        """Run periodic scanning based on configured intervals"""
        logger.info("Signal Engine started")
        
        while True:
            await self.run_scan()
            await self.update_tracking()
            
            # Wait for next scan interval
            await asyncio.sleep(settings.SCAN_INTERVAL_SECONDS)


async def main():
    """Application entry point"""
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Start signal engine
    engine = SignalEngine()
    await engine.run_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
