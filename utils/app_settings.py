import os
import json
from .path_utils import get_resource_path


CONFIG_REL = os.path.join("config", "settings.json")


def load_app_settings() -> dict:
    """Load settings from config/settings.json and return a settings dict.

    Returns a dict with at least: server_type, custom_url, use_cert, cert_path,
    server_url, server_cert
    """
    settings = {
        "server_type": "public",
        "custom_url": "http://127.0.0.1:8000",
        "use_cert": True,
        "cert_path": os.path.join("utils", "cert.pem"),
    }

    cfg_path = get_resource_path(CONFIG_REL)
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                settings.update({
                    "server_type": data.get("server_type", settings["server_type"]),
                    "custom_url": data.get("custom_url", settings["custom_url"]),
                    "use_cert": data.get("use_cert", settings["use_cert"]),
                    "cert_path": data.get("cert_path", settings["cert_path"]),
                    "theme_name": data.get("theme_name"),
                })
        except Exception:
            # Return defaults on failure
            pass

    # Compute effective server URL and cert absolute path
    if settings.get("server_type") == "public":
        settings["server_url"] = "https://34.61.34.132:8000"
        settings["server_cert"] = get_resource_path(os.path.join("utils", "cert.pem"))
    else:
        settings["server_url"] = settings.get("custom_url")
        settings["server_cert"] = (
            get_resource_path(settings.get("cert_path")) if settings.get("use_cert") else None
        )

    return settings
