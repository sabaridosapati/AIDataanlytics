from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://analytics:analytics@postgres:5432/analytics"
    query_ro_url: str = "postgresql://query_ro:query_ro@postgres:5432/analytics"
    redis_url: str = "redis://redis:6379/0"

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_planner_model: str = "gpt-4o"
    openai_embed_model: str = "text-embedding-3-small"
    openai_temperature: float | None = 0.0
    embed_dim: int = 1536

    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60
    admin_email: str = "admin@analytics.local"
    admin_password: str = "Test@123"

    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_from: str = "AI Analytics <no-reply@analytics.local>"
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False

    upload_dir: str = "/data/uploads"
    max_upload_mb: int = 50
    max_sql_rows: int = 5000
    step_timeout_s: int = 30
    cache_ttl_s: int = 3600
    rate_limit_enabled: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
