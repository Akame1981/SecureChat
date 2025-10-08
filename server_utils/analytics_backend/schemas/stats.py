from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

class SystemStats(BaseModel):
    cpu: float
    memory: float
    disk: float
    net_sent_mb: float
    net_recv_mb: float
    uptime_seconds: int

class UserStats(BaseModel):
    total_users: int
    active_users: int
    new_users_today: int

class MessageStats(BaseModel):
    messages_today: int
    avg_message_size: float
    per_hour: List[Dict[str, Any]]
    per_day: List[Dict[str, Any]]
    bytes_today: int | None = None
    total_bytes: int | None = None
    total_mb: float | None = None
    total_gb: float | None = None

class AttachmentStats(BaseModel):
    attachments_today: int
    avg_attachment_size: float
    per_hour: List[Dict[str, Any]]
    per_day: List[Dict[str, Any]]
    bytes_today: int | None = None
    total_bytes: int | None = None
    total_mb: float | None = None
    total_gb: float | None = None
