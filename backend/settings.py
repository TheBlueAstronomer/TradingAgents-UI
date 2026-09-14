from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_path: Path = Path("tradingagents.sqlite3")
    cors_origins: str = "http://localhost:3000"
    cors_origin_regex: str | None = None

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def parsed_cors_origin_regex(self) -> str | None:
        if self.cors_origin_regex is None:
            return None
        return self.cors_origin_regex.strip() or None
