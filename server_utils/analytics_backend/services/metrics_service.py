import psutil
import time
import os
from typing import Optional
from .event_collector import (
    get_user_stats as ec_user_stats,
    get_message_stats as ec_message_stats,
    get_attachment_stats as ec_attachment_stats,
    register_message as ec_register_message,
    register_attachment as ec_register_attachment,
)

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

def _redis_user_stats():
    import datetime
    now = datetime.datetime.utcnow()
    day_key = now.strftime('%Y%m%d')
    total_users = _redis_client.scard('metrics:users:all') or 0
    new_users_today = _redis_client.scard(f'metrics:users:new:{day_key}') or 0
    cutoff = time.time() - 300
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

def _redis_message_stats():
    import datetime
    now = datetime.datetime.utcnow()
    day_key = now.strftime('%Y%m%d')
    messages_today = int(_redis_client.get(f'metrics:messages:count:{day_key}') or 0)
    bytes_today = int(_redis_client.get(f'metrics:messages:bytes:{day_key}') or 0)
    avg_size = (bytes_today / messages_today) if messages_today else 0.0
    # Approximate total bytes (retention 7 days) by summing last 7 keys
    total_bytes = 0
    for i in range(0, 7):
        d = now - datetime.timedelta(days=i)
        d_key = d.strftime('%Y%m%d')
        total_bytes += int(_redis_client.get(f'metrics:messages:bytes:{d_key}') or 0)
    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_bytes / (1024 * 1024 * 1024)
    per_hour = []
    for i in range(23, -1, -1):
        h = now - datetime.timedelta(hours=i)
        hour_key = h.strftime('%Y%m%d%H')
        count = int(_redis_client.get(f'metrics:messages:hour:{hour_key}') or 0)
        per_hour.append({'hour': h.strftime('%H:00'), 'messages': count})
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
        'per_day': per_day,
        'bytes_today': bytes_today,
        'total_bytes': total_bytes,
        'total_mb': round(total_mb, 2),
        'total_gb': round(total_gb, 3)
    }

def _redis_attachment_stats():
    import datetime
    now = datetime.datetime.utcnow()
    day_key = now.strftime('%Y%m%d')
    attachments_today = int(_redis_client.get(f'metrics:attachments:count:{day_key}') or 0)
    bytes_today = int(_redis_client.get(f'metrics:attachments:bytes:{day_key}') or 0)
    avg_size = (bytes_today / attachments_today) if attachments_today else 0.0
    total_bytes = 0
    for i in range(0, 7):
        d = now - datetime.timedelta(days=i)
        d_key = d.strftime('%Y%m%d')
        total_bytes += int(_redis_client.get(f'metrics:attachments:bytes:{d_key}') or 0)
    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_bytes / (1024 * 1024 * 1024)
    per_hour = []
    for i in range(23, -1, -1):
        h = now - datetime.timedelta(hours=i)
        hour_key = h.strftime('%Y%m%d%H')
        count = int(_redis_client.get(f'metrics:attachments:hour:{hour_key}') or 0)
        per_hour.append({'hour': h.strftime('%H:00'), 'attachments': count})
    per_day = []
    for i in range(6, -1, -1):
        d = now - datetime.timedelta(days=i)
        d_key = d.strftime('%Y%m%d')
        count = int(_redis_client.get(f'metrics:attachments:count:{d_key}') or 0)
        per_day.append({'day': d.strftime('%Y-%m-%d'), 'attachments': count})
    return {
        'attachments_today': attachments_today,
        'avg_attachment_size': avg_size,
        'per_hour': per_hour,
        'per_day': per_day,
        'bytes_today': bytes_today,
        'total_bytes': total_bytes,
        'total_mb': round(total_mb, 2),
        'total_gb': round(total_gb, 3)
    }

# Lightweight ingestion from file log when Redis absent
_last_ingested_offset = 0
def _ingest_file_events():
    global _last_ingested_offset
    log_file = 'analytics_events.log'
    try:
        import os, json
        if not os.path.exists(log_file):
            return
        size = os.path.getsize(log_file)
        if size < _last_ingested_offset:
            # file rotated or truncated
            _last_ingested_offset = 0
        with open(log_file, 'r', encoding='utf-8') as f:
            f.seek(_last_ingested_offset)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                    if evt.get('type') == 'attachment':
                        ec_register_attachment(size_bytes=evt.get('size',0), sender=evt.get('from','?'), recipient=evt.get('to','?'), ts=evt.get('ts'))
                    else:
                        ec_register_message(size_bytes=evt.get('size',0), sender=evt.get('from','?'), recipient=evt.get('to','?'), ts=evt.get('ts'))
                except Exception:
                    continue
            _last_ingested_offset = f.tell()
    except Exception:
        pass

# Wrap original functions so they trigger ingestion when Redis is not in use
_orig_ec_user_stats = ec_user_stats
_orig_ec_message_stats = ec_message_stats
_orig_ec_attachment_stats = ec_attachment_stats

def get_user_stats():  # type: ignore[override]
    if _redis_client:
        return _redis_user_stats()
    _ingest_file_events()
    return _orig_ec_user_stats()

def get_message_stats():  # type: ignore[override]
    if _redis_client:
        return _redis_message_stats()
    _ingest_file_events()
    return _orig_ec_message_stats()

def get_attachment_stats():  # type: ignore[override]
    if _redis_client:
        return _redis_attachment_stats()
    _ingest_file_events()
    return _orig_ec_attachment_stats()

