"""
Database Connection and Session Management
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

from config.settings import settings
from database.models import Base

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.DATABASE_URL
        
        # SQLite-specific configuration
        connect_args = {}
        poolclass = None
        
        if self.database_url.startswith('sqlite'):
            connect_args = {"check_same_thread": False}
            poolclass = StaticPool
        
        self.engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            poolclass=poolclass,
            echo=False  # Set to True for SQL debugging
        )
        
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )
    
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def close_session(self):
        """Close session"""
        self.SessionLocal.remove()


# Global database instance
db = Database()


def init_db():
    """Initialize database (create tables)"""
    db.create_tables()
    logger.info("Database initialized")


def get_db():
    """Get database session (for dependency injection)"""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
