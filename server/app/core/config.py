from functools import cached_property, lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "SCosmetics API"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    database_url: str = "sqlite:///./scosmetics.db"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    client_origin: str = "http://localhost:3000"
    admin_origin: str = "http://localhost:3001"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @cached_property
    def allowed_origins(self) -> list[str]:
        return [self.client_origin, self.admin_origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

