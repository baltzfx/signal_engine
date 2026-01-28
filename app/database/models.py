"""
Database Models
SQLAlchemy models for storing signals and outcomes
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Signal(Base):
    """Signal model - stores all generated signals"""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Signal basics
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)  # LONG or SHORT
    status = Column(String(20), default='OPEN', index=True)  # OPEN, CLOSED, EXPIRED
    
    # Pricing
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    current_price = Column(Float)
    
    # Risk/Reward
    confidence = Column(Float)
    risk_reward_ratio = Column(Float)
    
    # Outcomes
    outcome = Column(String(20))  # WIN, LOSS, NEUTRAL, PENDING
    pnl_percent = Column(Float)
    pnl_points = Column(Float)
    exit_price = Column(Float)
    exit_reason = Column(String(50))
    
    # Metadata
    timeframe_1h = Column(JSON)
    timeframe_4h = Column(JSON)
    market_regime = Column(JSON)
    support_resistance = Column(JSON)
    filters = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Signal(id={self.id}, symbol={self.symbol}, type={self.signal_type}, status={self.status})>"


class RejectedSignal(Base):
    """Rejected signals for analysis"""
    __tablename__ = 'rejected_signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(10))
    rejection_reason = Column(String(200), nullable=False)
    confidence_score = Column(Float)
    
    # Analysis data
    analysis_summary = Column(JSON)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<RejectedSignal(id={self.id}, symbol={self.symbol}, reason={self.rejection_reason})>"


class PerformanceMetrics(Base):
    """Daily performance metrics"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Signal counts
    total_signals = Column(Integer, default=0)
    total_closed = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    
    # Performance
    win_rate = Column(Float)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    profit_factor = Column(Float)
    total_r = Column(Float)
    
    # By symbol
    best_symbol = Column(String(20))
    worst_symbol = Column(String(20))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PerformanceMetrics(date={self.date}, win_rate={self.win_rate})>"
