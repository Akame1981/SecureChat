try:
    from pydantic_settings import BaseSettings  # Pydantic v2
except ImportError:  # Fallback for pydantic v1 if environment differs
    from pydantic import BaseSettings  # type: ignore
from functools import lru_cache

class Settings(BaseSettings):
    admin_username: str = "admin"
    admin_password: str = "change_me"
    admin_password_hash: str | None = None
    jwt_secret: str = "change_this_secret_key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./analytics.db"
    allowed_origins: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
