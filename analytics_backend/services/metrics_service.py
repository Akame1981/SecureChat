import psutil
import time
from .event_collector import get_user_stats as ec_user_stats, get_message_stats as ec_message_stats

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
    return ec_user_stats()

def get_message_stats() -> dict:
    return ec_message_stats()
