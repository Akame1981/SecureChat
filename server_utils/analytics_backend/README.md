# Whispr Analytics Backend

## Quick Start

Create a `.env` file based on `.env.example`.

Install dependencies:
```
pip install -r requirements.txt
```

Run:
```
uvicorn server_utils.analytics_backend.main:app --reload --port 8001
```

## Endpoints
- `POST /api/auth/login` (OAuth2 password form) -> access token
- `GET /api/stats/system` (Bearer token)
- `GET /api/stats/users` (Bearer token)
- `GET /api/stats/messages` (Bearer token)

Health check: `GET /health`

## Notes
- Replace stub metric functions in `services/metrics_service.py` with real aggregation from Whispr runtime/database.
- Ensure admin password hashed & stored securely in production.
