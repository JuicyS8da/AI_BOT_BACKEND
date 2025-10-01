from pydantic import BaseSettings, AnyUrl
from functools import lru_cache
from typing import Literal, Optional

class Settings(BaseSettings):
    APP_ENV: Literal["dev", "prod"] = "dev"

    # FastAPI
    APP_NAME: str = "Music Schedule Bot"
    DEBUG: bool = False

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = ["*"]

    # DB
    DATABASE_URL: AnyUrl

    # Uvicorn/HTTP
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Твои кастомные переменные (если есть)
    # TELEGRAM_BOT_TOKEN: str | None = None

    class Config:
        env_file = ".env"   # Render прокинет переменные окружения без файла,
                            # локально .env.dev/.env.prod можно указывать вручную

@lru_cache
def get_settings() -> Settings:
    s = Settings()  # читает переменные из окружения
    if s.APP_ENV == "dev":
        s.DEBUG = True
        s.WORKERS = 1
    else:
        s.DEBUG = False
        # WORKERS можно оставить из ENV/Procfile
    return s
