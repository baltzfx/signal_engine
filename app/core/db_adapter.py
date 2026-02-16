"""
Database adapter that works with both SQLite (local) and PostgreSQL (production).
Automatically detects DATABASE_URL and uses appropriate engine.
"""

import os
from typing import Optional

def get_database_config() -> dict:
    """
    Returns database configuration based on environment.
    
    Local: Uses SQLite
    Render/Production: Uses PostgreSQL from DATABASE_URL
    """
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Production: Use PostgreSQL
        # Render provides postgres:// but SQLAlchemy needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif not database_url.startswith("postgresql"):
            database_url = f"postgresql+asyncpg://{database_url}"
        
        return {
            "url": database_url,
            "driver": "postgresql",
            "pool_size": 10,
            "max_overflow": 20,
        }
    else:
        # Local development: Use SQLite
        db_path = "data/db/signalengine.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        return {
            "url": f"sqlite+aiosqlite:///{db_path}",
            "driver": "sqlite",
            "pool_size": 1,
            "max_overflow": 0,
        }


def get_sql_placeholder() -> str:
    """
    Returns the correct SQL placeholder for the current database.
    SQLite uses ?, PostgreSQL uses $1, $2, etc.
    """
    config = get_database_config()
    return "?" if config["driver"] == "sqlite" else "%s"


# Example usage in database.py or similar:
# 
# from app.core.db_adapter import get_database_config
# 
# config = get_database_config()
# DATABASE_URL = config["url"]
# db = Database(DATABASE_URL)
