"""
Query handler for processing user messages from Telegram.

Parses natural language queries and coordinates responses.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.signals.on_demand_scorer import get_top_symbols
from app.ai.response_generator import generate_query_response

logger = logging.getLogger(__name__)


class QueryHandler:
    """Handles parsing and processing of user queries."""

    def __init__(self):
        # Query patterns for different types of requests
        self.patterns = {
            'top_symbols': re.compile(r'\b(top|best|hot|profitable|leading)\s+(symbols?|tokens?|coins?|futures?)\b', re.IGNORECASE),
            'futures': re.compile(r'\b(futures?|trading|trade)\b', re.IGNORECASE),
            'analysis': re.compile(r'\b(analysis|analyze|what|how|why)\b', re.IGNORECASE),
            'help': re.compile(r'\b(help|commands?|what can you do|usage)\b', re.IGNORECASE)
        }

    async def process_query(self, message: str) -> str:
        """
        Process a user query and return a response.

        Args:
            message: The user's message text

        Returns:
            Response string to send back to user
        """
        message = message.strip().lower()

        # Check for help requests
        if self._is_help_query(message):
            return self._get_help_text()

        # Check for top symbols query
        if self._is_top_symbols_query(message):
            return await self._handle_top_symbols_query(message)

        # Default response for unrecognized queries
        return self._get_default_response(message)

    def _is_help_query(self, message: str) -> bool:
        """Check if the message is asking for help."""
        return bool(self.patterns['help'].search(message))

    def _is_top_symbols_query(self, message: str) -> bool:
        """Check if the message is asking for top symbols."""
        return bool(self.patterns['top_symbols'].search(message) or
                   (self.patterns['futures'].search(message) and
                    (self.patterns['analysis'].search(message) or 'what' in message)))

    async def _handle_top_symbols_query(self, original_query: str) -> str:
        """Handle a query for top symbols."""
        try:
            # Get top symbols
            top_symbols = await get_top_symbols()

            if not top_symbols:
                return "❌ Unable to analyze symbols at the moment. Please try again later."

            # Generate AI-powered response
            response = await generate_query_response(original_query, top_symbols)

            return response

        except Exception as e:
            logger.error(f"Failed to handle top symbols query: {e}")
            return "❌ Sorry, there was an error processing your request. Please try again."

    def _get_help_text(self) -> str:
        """Return help text for available commands."""
        return """🤖 SignalEngine Bot Commands:

📊 **Top Symbols Query:**
• "What's the top symbols for futures now?"
• "Best futures tokens today?"
• "Show me the leading coins"

💡 **How it works:**
• Analyzes real-time technical indicators
• Uses AI for market insights
• Ranks symbols by trading potential

⚠️ **Disclaimer:**
This is for informational purposes only.
Not financial advice. DYOR!

Try asking: "what are the top futures symbols?" """

    def _get_default_response(self, message: str) -> str:
        """Return a default response for unrecognized queries."""
        return """🤔 I didn't understand that query.

I can help you find the top performing futures symbols based on real-time analysis.

Try asking:
• "What's the top symbols for futures now?"
• "Show me the best futures tokens"
• "Help" for more commands

What would you like to know?"""


# Global instance
query_handler = QueryHandler()