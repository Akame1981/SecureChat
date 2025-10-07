from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth as auth_routes
from .routes import stats as stats_routes
from .core.config import get_settings

app = FastAPI(title="Whispr Analytics API", version="0.1.0")
settings = get_settings()

origins = [o.strip() for o in settings.allowed_origins.split(',')]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(stats_routes.router)

@app.get('/health')
async def health():
    return {"status": "ok"}
