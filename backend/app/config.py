from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/postgres"
    secret_key: str = "change-this-secret-key-in-production-must-be-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    redis_url: str = "redis://localhost:6379"
    google_service_account_email: str = "emailer-builder@your-project.iam.gserviceaccount.com"
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173"

    # Google Sheets integration
    google_sheets_credentials_json: str = ""  # JSON string of service account credentials
    global_utm_prefix: str = ""
    service_account_email: str = "builder@project.iam.gserviceaccount.com"

    # OpenAI
    openai_api_key: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
