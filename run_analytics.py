"""Convenience runner for the analytics backend.

Ensures you are in the repository root and starts uvicorn with reload.
Use:  python run_analytics.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("server_utils.analytics_backend.main:app", host="0.0.0.0", port=8001, reload=True)
