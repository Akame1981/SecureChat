from datetime import datetime, timedelta
from typing import List, Dict, Any
import psutil
import os
import time

_process_start_time = time.time()

# Placeholder functions; integrate with actual app database / runtime state where possible.

def get_system_stats() -> dict:
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
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

# Stubs for user/message stats. Replace with real logic.
_fake_total_users = 42
_fake_active_users = 7
_fake_messages_today = 350
_fake_avg_message_size = 512.0

_per_hour = []
_per_day = []

now = datetime.utcnow()
for i in range(24):
    _per_hour.append({
        'hour': (now - timedelta(hours=i)).strftime('%H:00'),
        'messages': max(0, _fake_messages_today // 24 + (i % 5) - 2)
    })
_per_hour.reverse()

for i in range(7):
    _per_day.append({
        'day': (now - timedelta(days=i)).strftime('%Y-%m-%d'),
        'messages': max(0, _fake_messages_today // 7 + (i % 3) - 1)
    })
_per_day.reverse()

def get_user_stats() -> dict:
    new_users_today = 2
    return {
        'total_users': _fake_total_users,
        'active_users': _fake_active_users,
        'new_users_today': new_users_today
    }

def get_message_stats() -> dict:
    return {
        'messages_today': _fake_messages_today,
        'avg_message_size': _fake_avg_message_size,
        'per_hour': _per_hour,
        'per_day': _per_day
    }
