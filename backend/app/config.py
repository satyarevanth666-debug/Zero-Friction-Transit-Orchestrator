"""Application configuration settings using Pydantic Settings."""


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for the Transit Orchestrator."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./zero_friction_transit.db"
    JWT_SECRET: str = "development_secret_key_must_be_over_32_characters_long_for_security"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    COOKIE_SECURE: bool = False

    FRONTEND_ORIGIN: str = "http://localhost:3000"

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "noreply@zerofrictiontransit.local"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:7b-instruct"
    LLM_ENABLED: bool = True
    LLM_TIMEOUT_SECONDS: int = 8

    ENABLE_GOOGLE_OAUTH: bool = False
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    ENABLE_THIRD_PARTY_RAIL: bool = False
    RAIL_API_KEY: str | None = None

    FLIGHT_PROVIDER: str = "mock"
    FLIGHT_API_KEY: str | None = None

    TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_EVENING_START: str = "16:00"
    DEFAULT_EVENING_END: str = "21:00"
    DOMESTIC_CHECKIN_BUFFER_MIN: int = 90

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [self.FRONTEND_ORIGIN.rstrip("/")]


settings = Settings()


def resolve_data_path(rel_path: str) -> str:
    """Resolve data paths whether running from workspace root or backend subdirectory."""
    from pathlib import Path
    p = Path(rel_path)
    if p.exists():
        return str(p)
    p_up = Path("..") / rel_path
    if p_up.exists():
        return str(p_up)
    # Search upwards to project root
    curr = Path(__file__).resolve().parent
    for _ in range(4):
        candidate = curr / rel_path
        if candidate.exists():
            return str(candidate)
        curr = curr.parent
    return rel_path

