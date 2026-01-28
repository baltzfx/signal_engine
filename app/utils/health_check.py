"""
Health Check Endpoint
Simple HTTP endpoint for monitoring system health
"""
import asyncio
import logging
from datetime import datetime
from aiohttp import web

from data.binance_client import BinanceClient
from config.settings import settings

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """Simple health check HTTP server"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = web.Application()
        self.client = BinanceClient()
        self.last_scan_time = None
        self.total_signals_sent = 0
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.detailed_status)
    
    async def health_check(self, request):
        """Basic health check - is service running?"""
        return web.json_response({
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'signal-engine'
        })
    
    async def detailed_status(self, request):
        """Detailed status with metrics"""
        
        # Test Binance connection
        binance_ok = False
        try:
            ticker = await self.client.fetch_ticker('BTCUSDT')
            binance_ok = ticker is not None
        except:
            pass
        
        # Test Telegram connection
        telegram_ok = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
        
        status = {
            'status': 'healthy' if (binance_ok and telegram_ok) else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'binance': 'ok' if binance_ok else 'error',
                'telegram': 'ok' if telegram_ok else 'not_configured'
            },
            'metrics': {
                'last_scan': self.last_scan_time.isoformat() if self.last_scan_time else None,
                'total_signals_sent': self.total_signals_sent,
                'configured_pairs': len(settings.TRADING_PAIRS)
            },
            'config': {
                'scan_interval': settings.SCAN_INTERVAL_SECONDS,
                'min_confidence': settings.MIN_CONFIDENCE_SCORE,
                'enhanced_strategy': settings.USE_ENHANCED_STRATEGY
            }
        }
        
        return web.json_response(status)
    
    def update_metrics(self, last_scan_time: datetime = None, signals_sent: int = 0):
        """Update internal metrics"""
        if last_scan_time:
            self.last_scan_time = last_scan_time
        self.total_signals_sent += signals_sent
    
    async def start(self):
        """Start health check server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Health check server started on port {self.port}")
