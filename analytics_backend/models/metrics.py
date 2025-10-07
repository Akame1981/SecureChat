from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from .base import Base

class MessageMetric(Base):
    __tablename__ = 'message_metrics'
    id = Column(Integer, primary_key=True, index=True)
    period = Column(String, index=True)  # e.g. 'hour', 'day'
    period_start = Column(DateTime, index=True)
    message_count = Column(Integer, default=0)
    avg_message_size = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

class UserMetric(Base):
    __tablename__ = 'user_metrics'
    id = Column(Integer, primary_key=True, index=True)
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    period = Column(String, index=True)
    period_start = Column(DateTime, index=True)
    created_at = Column(DateTime, server_default=func.now())
