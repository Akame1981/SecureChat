from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    admin_username: str = "admin"
    admin_password: str = "change_me_securely"
    jwt_secret: str = "change_this_secret_key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./analytics.db"

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
