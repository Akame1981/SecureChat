import psutil
import time
import os
from typing import Optional
from .event_collector import get_user_stats as ec_user_stats, get_message_stats as ec_message_stats

# Optional Redis integration for cross-process metrics
try:
    import redis  # type: ignore
    _redis_client: Optional["redis.Redis"] = redis.Redis(host=os.getenv('REDIS_HOST','localhost'), port=int(os.getenv('REDIS_PORT','6379')), db=0, decode_responses=True)
    try:
        _redis_client.ping()
    except Exception:
        _redis_client = None
except Exception:
    _redis_client = None

_process_start_time = time.time()

def get_system_stats() -> dict:
    cpu = psutil.cpu_percent(interval=0.05)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/') .percent
    net = psutil.net_io_counters()
    sent_mb = net.bytes_sent / (1024 * 1024)
    recv_mb = net.bytes_recv / (1024 * 1024)
    uptime = int(time.time() - _process_start_time)
    return {
        'cpu': cpu,
        'memory': mem,
        'disk': disk,
        'net_sent_mb': round(sent_mb, 2),
        'net_recv_mb': round(recv_mb, 2),
        'uptime_seconds': uptime
    }

def get_user_stats() -> dict:
    if _redis_client:
        import datetime
        now = datetime.datetime.utcnow()
        day_key = now.strftime('%Y%m%d')
        total_users = _redis_client.scard('metrics:users:all') or 0
        new_users_today = _redis_client.scard(f'metrics:users:new:{day_key}') or 0
        # Active: last 5 minutes window from sorted set
        cutoff = time.time() - 300
        # Remove anything older than a day opportunistically
        try:
            _redis_client.zremrangebyscore('metrics:active_users', 0, time.time() - 86400)
        except Exception:
            pass
        active_users = _redis_client.zcount('metrics:active_users', cutoff, '+inf') or 0
        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_users_today': new_users_today
        }
    return ec_user_stats()

def get_message_stats() -> dict:
    if _redis_client:
        import datetime
        now = datetime.datetime.utcnow()
        day_key = now.strftime('%Y%m%d')
        # Daily counts
        messages_today = int(_redis_client.get(f'metrics:messages:count:{day_key}') or 0)
        bytes_today = int(_redis_client.get(f'metrics:messages:bytes:{day_key}') or 0)
        avg_size = (bytes_today / messages_today) if messages_today else 0.0
        # Hour series (last 24h)
        per_hour = []
        for i in range(23, -1, -1):
            h = now - datetime.timedelta(hours=i)
            hour_key = h.strftime('%Y%m%d%H')
            count = int(_redis_client.get(f'metrics:messages:hour:{hour_key}') or 0)
            per_hour.append({'hour': h.strftime('%H:00'), 'messages': count})
        # Day series (last 7 days)
        per_day = []
        for i in range(6, -1, -1):
            d = now - datetime.timedelta(days=i)
            d_key = d.strftime('%Y%m%d')
            count = int(_redis_client.get(f'metrics:messages:count:{d_key}') or 0)
            per_day.append({'day': d.strftime('%Y-%m-%d'), 'messages': count})
        return {
            'messages_today': messages_today,
            'avg_message_size': avg_size,
            'per_hour': per_hour,
            'per_day': per_day
        }
    return ec_message_stats()
