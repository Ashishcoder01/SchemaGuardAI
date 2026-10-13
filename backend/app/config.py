
from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SchemaGuard AI"
    environment: str = "development"

    api_key: str = Field(
        default="",
        validation_alias=AliasChoices("SCHEMAGUARD_API_KEY", "API_KEY"),
    )

    database_url: str = "sqlite:///./schemaguard.db"

    llm_provider: str = "mock"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    max_retries: int = 2
    request_timeout: int = 30
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_cors(self):
        if self.environment.strip().lower() == "production":
            origins = self.allowed_origins

            if not origins:
                raise ValueError(
                    "Production requires at least one configured CORS origin."
                )

            for origin in origins:
                normalized = origin.lower().rstrip("/")

                if normalized == "*":
                    raise ValueError(
                        "Wildcard CORS origins are not allowed in production."
                    )

                if normalized.startswith(
                    ("http://localhost", "http://127.0.0.1")
                ):
                    raise ValueError(
                        "Production CORS origins must not use local HTTP addresses."
                    )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
