"""
Basic response generator for market queries.

Provides rule-based responses for user queries about market signals and analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def generate_custom_query_response(
    query: str,
    context_symbols: List[Dict[str, Any]],
    active_signals: List[Dict[str, Any]] = None
) -> str:
    """
    Generate a response to a custom user query about the market.

    Args:
        query: The user's custom query
        context_symbols: List of current top symbols for context (scoring only)
        active_signals: List of active signals with entry/TP/SL levels

    Returns:
        Response string
    """
    if active_signals is None:
        active_signals = []

    query_lower = query.lower()

    # Handle queries about specific signals/trading levels
    if any(keyword in query_lower for keyword in ['entry', 'tp', 'sl', 'stop', 'take profit', 'price', 'level']):
        # Try to find the symbol mentioned in the query
        mentioned_signal = None
        for sig in active_signals:
            if sig['symbol'].lower() in query_lower:
                mentioned_signal = sig
                break

        if mentioned_signal:
            direction = "📈 LONG" if mentioned_signal['direction'] == 'long' else "📉 SHORT"
            response = f"**{mentioned_signal['symbol']}** {direction} Signal:\n\n"
            response += f"• Entry: ${mentioned_signal['entry_price']:.4f}\n"
            response += f"• Take Profit: ${mentioned_signal['tp_price']:.4f}\n"
            response += f"• Stop Loss: ${mentioned_signal['sl_price']:.4f}\n"
            response += f"• Confidence: {int(mentioned_signal['score']*100)}%\n"
            response += f"• Age: {mentioned_signal.get('age_seconds', 0):.0f} seconds\n\n"
            response += "⚠️ This is not financial advice. Always manage your risk."
            return response
        elif active_signals:
            # Show all active signals if no specific symbol found
            response = f"**Active Signals ({len(active_signals)}):**\n\n"
            for sig in active_signals[:5]:  # Show top 5
                direction = "📈 LONG" if sig['direction'] == 'long' else "📉 SHORT"
                response += f"**{sig['symbol']}** {direction}\n"
                response += f"Entry: ${sig['entry_price']:.4f} | TP: ${sig['tp_price']:.4f} | SL: ${sig['sl_price']:.4f}\n\n"
            response += "⚠️ This is not financial advice. Always manage your risk."
            return response
        else:
            return "No active signals with trading levels at the moment. The system is analyzing market data for new opportunities."

    # Handle common queries
    if 'trend' in query_lower or 'trending' in query_lower:
        if context_symbols:
            top_symbol = context_symbols[0]
            score_pct = int(top_symbol['score'] * 100)
            direction = "📈 LONG" if top_symbol['direction'] == 'long' else "📉 SHORT" if top_symbol['direction'] == 'short' else "🔄 NEUTRAL"
            return f"Based on current signals, **{top_symbol['symbol']}** appears to be trending with a {score_pct}% confidence {direction.lower()} signal. Other notable symbols include {', '.join([s['symbol'] for s in context_symbols[1:3]])}. This is based on technical analysis and market data."
        else:
            return "I'm currently analyzing market data. No strong trends detected at the moment."

    elif 'sentiment' in query_lower or 'market' in query_lower:
        if context_symbols:
            long_count = sum(1 for s in context_symbols if s['direction'] == 'long')
            short_count = sum(1 for s in context_symbols if s['direction'] == 'short')
            if long_count > short_count:
                sentiment = "bullish 📈"
            elif short_count > long_count:
                sentiment = "bearish 📉"
            else:
                sentiment = "mixed 🔄"
            return f"Current market sentiment appears {sentiment} based on signal analysis. {long_count} long signals vs {short_count} short signals from top tracked symbols."
        else:
            return "Market sentiment analysis requires current signal data. Please check back in a moment."

    elif 'top' in query_lower or 'best' in query_lower:
        if context_symbols:
            top_3 = context_symbols[:3]
            response = "Here are the top 3 performing symbols based on current signals:\n\n"
            for i, symbol in enumerate(top_3, 1):
                score_pct = int(symbol['score'] * 100)
                direction = "📈 LONG" if symbol['direction'] == 'long' else "📉 SHORT" if symbol['direction'] == 'short' else "🔄 NEUTRAL"
                response += f"{i}. **{symbol['symbol']}** - {score_pct}% confidence, {direction}\n"
            response += "\nThese rankings are based on real-time technical analysis."
            return response
        else:
            return "No top symbols available at the moment. The system is collecting market data."

    elif 'help' in query_lower or 'what' in query_lower:
        return """I can help you with market analysis! Try asking:
• "What is trending now?"
• "What's the market sentiment?"
• "Show me top symbols"
• "Explain long vs short positions"
• "What are the risks of futures trading?"

I'm analyzing real-time data from 110+ cryptocurrency futures pairs."""

    else:
        # Generic response for unrecognized queries
        return f"I understand you're asking about: \"{query}\". I'm analyzing current market signals from {len(context_symbols)} symbols. For specific trading advice, I recommend consulting financial professionals. This analysis is for informational purposes only."


async def generate_query_response(query: str, top_symbols: List[Dict[str, Any]]) -> str:
    """
    Generate a response to a user query about top symbols.

    Args:
        query: The user's original query
        top_symbols: List of top scored symbols with explanations

    Returns:
        Formatted response string
    """
    if not top_symbols:
        return "No symbols available for analysis at the moment."

    response_lines = [f"📊 Top {len(top_symbols)} Futures Symbols Analysis:", ""]

    for i, symbol in enumerate(top_symbols, 1):
        score_pct = int(symbol['score'] * 100)
        direction_emoji = "🟢" if symbol['direction'] == 'long' else "🔴" if symbol['direction'] == 'short' else "🟡"
        response_lines.append(f"{i}. {direction_emoji} {symbol['symbol']} ({score_pct}% confidence)")
        response_lines.append(f"   {symbol['explanation']}")
        response_lines.append("")

    response_lines.append("⚠️ This is not financial advice. Always do your own research.")

    return "\n".join(response_lines)
