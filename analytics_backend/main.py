from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth as auth_routes
from .routes import stats as stats_routes

app = FastAPI(title="Whispr Analytics API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(stats_routes.router)

@app.get('/health')
async def health():
    return {"status": "ok"}
