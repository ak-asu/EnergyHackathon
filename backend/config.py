from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    eia_api_key: str = "DEMO_KEY"
    gridstatus_api_key: str = ""
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    data_dir: str = "data/silver"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]
    regime_refresh_secs: int = 300
    news_refresh_secs: int = 1800
    moirai_cache_secs: int = 3600

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
