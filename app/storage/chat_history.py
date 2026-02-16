"""Chat history storage for AI conversations."""
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.core.config import settings
import aiosqlite

logger = logging.getLogger(__name__)

DB_DIR = "data/db"
os.makedirs(DB_DIR, exist_ok=True)


async def init_chat_db():
    """Initialize chat history database table."""
    db_path = os.path.join(DB_DIR, settings.sqlite_db_name)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT
            )
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_session 
            ON chat_history(session_id, timestamp)
        """)
        
        await db.commit()
        logger.info("Chat history database initialized")


async def save_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """Save a chat message to the database."""
    try:
        db_path = os.path.join(DB_DIR, settings.sqlite_db_name)
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT INTO chat_history (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    datetime.now(timezone.utc).timestamp(),
                    json.dumps(metadata) if metadata else None
                )
            )
            await db.commit()
            logger.debug(f"Saved {role} message to session {session_id}")
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")


async def get_session_history(
    session_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get chat history for a session."""
    try:
        db_path = os.path.join(DB_DIR, settings.sqlite_db_name)
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, role, content, timestamp, metadata
                FROM chat_history
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (session_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": row["timestamp"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                    }
                    for row in rows
                ]
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        return []


async def get_all_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """Get list of recent chat sessions."""
    try:
        db_path = os.path.join(DB_DIR, settings.sqlite_db_name)
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT 
                    session_id,
                    MIN(timestamp) as first_message,
                    MAX(timestamp) as last_message,
                    COUNT(*) as message_count
                FROM chat_history
                GROUP BY session_id
                ORDER BY last_message DESC
                LIMIT ?
                """,
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "session_id": row["session_id"],
                        "first_message": row["first_message"],
                        "last_message": row["last_message"],
                        "message_count": row["message_count"]
                    }
                    for row in rows
                ]
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        return []


async def delete_session(session_id: str):
    """Delete a chat session."""
    try:
        db_path = os.path.join(DB_DIR, settings.sqlite_db_name)
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "DELETE FROM chat_history WHERE session_id = ?",
                (session_id,)
            )
            await db.commit()
            logger.info(f"Deleted chat session {session_id}")
    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")
