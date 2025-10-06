# utils/server_check.py
import requests
import time
import threading

def start_server_check(app, interval=1.0):
    """
    Loop that periodically checks app.SERVER_URL and schedules UI updates.
    Keeps the same notifier/SSL handling behavior as your original code.
    Runs until app.stop_event is set.
    """
    while not app.stop_event.is_set():
        online = False
        try:
            # Simple GET request to server root
            resp = requests.get(app.SERVER_URL, verify=app.SERVER_CERT, timeout=3)
            online = True  # request succeeded
        except requests.exceptions.ConnectionError as e:
            msg = f"⚠ Server offline (connection refused): {e}"
            print(msg)
            if hasattr(app, 'notifier') and app.notifier:
                try:
                    app.notifier.show(msg, type_="error")
                except Exception:
                    # Never crash the loop because of notifier
                    pass
            online = False
        except requests.exceptions.SSLError as e:
            msg = f"⚠ SSL verification failed: {e}"
            print(msg)
            if hasattr(app, 'notifier') and app.notifier:
                try:
                    app.notifier.show(msg, type_="warning")
                except Exception:
                    pass
            online = False
        except requests.exceptions.RequestException as e:
            msg = f"⚠ Server check failed: {e}"
            print(msg)
            if hasattr(app, 'notifier') and app.notifier:
                try:
                    app.notifier.show(msg, type_="error")
                except Exception:
                    pass
            online = False

        # Schedule GUI update (safe from background thread)
        try:
            app.after(0, app.update_status_color, online)
        except Exception:
            # If the UI is already gone or update fails, continue and let the loop end when stop_event set
            pass

        # Sleep for a bit
        # Use small sleeps in chunks so stop_event can interrupt promptly
        slept = 0.0
        while slept < interval and not app.stop_event.is_set():
            time.sleep(0.1)
            slept += 0.1


def run_server_check_in_thread(app, interval=1.0):
    """Start start_server_check in a daemon thread."""
    t = threading.Thread(target=start_server_check, args=(app, interval), daemon=True)
    t.start()
    return t
