"""Application configuration using Pydantic settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/biblical_evals"
    )
    database_password: str | None = None

    @property
    def effective_database_url(self) -> str:
        """Get database URL with password injected if DATABASE_PASSWORD is set."""
        if self.database_password:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(self.database_url)
            if parsed.username:
                netloc = f"{parsed.username}:{self.database_password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))
        return self.database_url

    # Auth (NextAuth.js shared secret for JWT verification)
    nextauth_secret: str | None = None
    admin_emails: str = "xdtsong@gmail.com,daniel@appraisehq.ai"

    # CORS (comma-separated list of origins)
    cors_origins: str = "http://localhost:3000"

    # LLM API Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    google_ai_api_key: str | None = None

    @property
    def effective_google_api_key(self) -> str | None:
        """Return the canonical Google key, falling back to legacy name."""

        return self.google_ai_api_key or self.google_api_key

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.admin_emails.split(",")
            if email.strip()
        }

    @property
    def primary_admin_email(self) -> str:
        for email in self.admin_emails.split(","):
            cleaned = email.strip().lower()
            if cleaned:
                return cleaned
        return "xdtsong@gmail.com"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
