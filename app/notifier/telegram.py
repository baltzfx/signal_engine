"""
Telegram Notifier
Sends formatted trading signals to Telegram
"""
import logging
from typing import List, Dict
import aiohttp

from config.settings import settings
from notifier.templates import format_signal_message

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram Bot API"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to Telegram chat
        
        Args:
            text: Message text
            parse_mode: HTML or Markdown
            
        Returns:
            True if sent successfully
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Telegram message sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Telegram API error {response.status}: {error_text}"
                        )
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}", exc_info=True)
            return False
    
    async def send_signal(self, signal: Dict) -> bool:
        """Send a single signal notification"""
        message = format_signal_message(signal)
        return await self.send_message(message)
    
    async def send_signals(self, signals: List[Dict]) -> None:
        """Send multiple signal notifications"""
        for signal in signals:
            await self.send_signal(signal)
    
    async def send_alert(self, message: str) -> bool:
        """Send a generic alert message"""
        formatted = f"🔔 <b>Alert</b>\n\n{message}"
        return await self.send_message(formatted)
