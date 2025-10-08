"""In-memory aggregation of message and user analytics.

This avoids hitting a database for each dashboard refresh while providing
quick approximate stats. For production persistence, mirror updates to
SQLAlchemy models and periodically compact.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List

UTC = timezone.utc

lock = Lock()

@dataclass
class HourBucket:
    count: int = 0
    bytes: int = 0

@dataclass
class DayBucket:
    count: int = 0
    bytes: int = 0

# Aggregates
hour_buckets: Dict[datetime, HourBucket] = {}
day_buckets: Dict[datetime, DayBucket] = {}
# Separate attachment aggregates (kept distinct to avoid mixing semantics)
att_hour_buckets: Dict[datetime, HourBucket] = {}
att_day_buckets: Dict[datetime, DayBucket] = {}
first_seen: Dict[str, datetime] = {}
last_seen: Dict[str, datetime] = {}

RETENTION_DAYS = 7
ACTIVE_WINDOW_SECONDS = 300  # 5 minutes

def _truncate_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0, tzinfo=UTC)

def _truncate_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)

def register_message(size_bytes: int, sender: str, recipient: str, ts: float | None = None) -> None:
    """Record a message event.

    size_bytes: size of encrypted (decoded) payload
    sender / recipient: user identifiers (NOT stored beyond aggregation)
    ts: unix timestamp (seconds)
    """
    if ts is None:
        now = datetime.now(UTC)
    else:
        now = datetime.fromtimestamp(ts, UTC)

    hour_key = _truncate_hour(now)
    day_key = _truncate_day(now)

    with lock:
        hb = hour_buckets.get(hour_key)
        if hb is None:
            hb = HourBucket()
            hour_buckets[hour_key] = hb
        hb.count += 1
        hb.bytes += size_bytes

        db = day_buckets.get(day_key)
        if db is None:
            db = DayBucket()
            day_buckets[day_key] = db
        db.count += 1
        db.bytes += size_bytes

        if sender not in first_seen:
            first_seen[sender] = day_key
        last_seen[sender] = now

        _retention_cleanup()

def register_attachment(size_bytes: int, sender: str, recipient: str, ts: float | None = None) -> None:
    """Record an attachment event (encrypted payload size)."""
    if ts is None:
        now = datetime.now(UTC)
    else:
        now = datetime.fromtimestamp(ts, UTC)
    hour_key = _truncate_hour(now)
    day_key = _truncate_day(now)
    with lock:
        hb = att_hour_buckets.get(hour_key)
        if hb is None:
            hb = HourBucket()
            att_hour_buckets[hour_key] = hb
        hb.count += 1
        hb.bytes += size_bytes

        db = att_day_buckets.get(day_key)
        if db is None:
            db = DayBucket()
            att_day_buckets[day_key] = db
        db.count += 1
        db.bytes += size_bytes

        # Track users (attachments count as activity)
        if sender not in first_seen:
            first_seen[sender] = day_key
        last_seen[sender] = now

        _retention_cleanup()

def _retention_cleanup():
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS + 1)
    # Remove old hour buckets
    for bucket_map in (hour_buckets, att_hour_buckets):
        for k in list(bucket_map.keys()):
            if k < cutoff:
                del bucket_map[k]
    # Remove old day buckets beyond retention
    for bucket_map in (day_buckets, att_day_buckets):
        for k in list(bucket_map.keys()):
            if k < cutoff:
                del bucket_map[k]

def get_user_stats() -> dict:
    now = datetime.now(UTC)
    with lock:
        total_users = len(first_seen)
        active_users = sum(1 for ts in last_seen.values() if (now - ts).total_seconds() <= ACTIVE_WINDOW_SECONDS)
        today_key = _truncate_day(now)
        new_users_today = sum(1 for u, d in first_seen.items() if d == today_key)
    return {
        'total_users': total_users,
        'active_users': active_users,
        'new_users_today': new_users_today
    }

def get_message_stats() -> dict:
    now = datetime.now(UTC)
    today_key = _truncate_day(now)
    hour_series: List[dict] = []
    day_series: List[dict] = []

    with lock:
        # Per hour (last 24 hours)
        for i in range(23, -1, -1):
            h = _truncate_hour(now - timedelta(hours=i))
            hb = hour_buckets.get(h)
            hour_series.append({
                'hour': h.strftime('%H:00'),
                'messages': hb.count if hb else 0
            })
        # Per day (last 7 days)
        for i in range(6, -1, -1):
            d = _truncate_day(now - timedelta(days=i))
            db = day_buckets.get(d)
            day_series.append({
                'day': d.strftime('%Y-%m-%d'),
                'messages': db.count if db else 0
            })

        today_bucket = day_buckets.get(today_key)
        messages_today = today_bucket.count if today_bucket else 0
        bytes_today = today_bucket.bytes if today_bucket else 0
        avg_size = (bytes_today / messages_today) if messages_today else 0.0
        total_bytes = sum(db.bytes for db in day_buckets.values())
        total_mb = total_bytes / (1024 * 1024)
        total_gb = total_bytes / (1024 * 1024 * 1024)

    return {
        'messages_today': messages_today,
        'avg_message_size': avg_size,
        'per_hour': hour_series,
        'per_day': day_series,
        'bytes_today': bytes_today,
        'total_bytes': total_bytes,
        'total_mb': round(total_mb, 2),
        'total_gb': round(total_gb, 3)
    }

def get_attachment_stats() -> dict:
    """Return attachment analytics (counts & average sizes)."""
    now = datetime.now(UTC)
    today_key = _truncate_day(now)
    hour_series: List[dict] = []
    day_series: List[dict] = []
    with lock:
        # Per hour last 24h
        for i in range(23, -1, -1):
            h = _truncate_hour(now - timedelta(hours=i))
            hb = att_hour_buckets.get(h)
            hour_series.append({
                'hour': h.strftime('%H:00'),
                'attachments': hb.count if hb else 0
            })
        # Per day last 7 days
        for i in range(6, -1, -1):
            d = _truncate_day(now - timedelta(days=i))
            db = att_day_buckets.get(d)
            day_series.append({
                'day': d.strftime('%Y-%m-%d'),
                'attachments': db.count if db else 0
            })
        today_bucket = att_day_buckets.get(today_key)
        attachments_today = today_bucket.count if today_bucket else 0
        bytes_today = today_bucket.bytes if today_bucket else 0
        avg_size = (bytes_today / attachments_today) if attachments_today else 0.0
        total_bytes = sum(db.bytes for db in att_day_buckets.values())
        total_mb = total_bytes / (1024 * 1024)
        total_gb = total_bytes / (1024 * 1024 * 1024)
    return {
        'attachments_today': attachments_today,
        'avg_attachment_size': avg_size,
        'per_hour': hour_series,
        'per_day': day_series,
        'bytes_today': bytes_today,
        'total_bytes': total_bytes,
        'total_mb': round(total_mb, 2),
        'total_gb': round(total_gb, 3)
    }
