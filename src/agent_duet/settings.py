"""Runtime configuration shared by both agent implementations."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, HttpUrl, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings.

    A single Foundry project endpoint and model deployment are deliberately
    shared by both implementations so the framework comparison does not
    accidentally become a model comparison.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    foundry_project_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("FOUNDRY_PROJECT_ENDPOINT", "AZURE_AI_PROJECT_ENDPOINT"),
    )
    foundry_model: str = Field(default="", validation_alias="FOUNDRY_MODEL")
    azure_credential_mode: Literal["cli", "default", "managed_identity"] = "cli"
    azure_client_id: str | None = None

    maf_host: str = "127.0.0.1"
    maf_port: PositiveInt = 8001
    maf_public_url: HttpUrl = HttpUrl("http://127.0.0.1:8001/")

    langgraph_host: str = "127.0.0.1"
    langgraph_port: PositiveInt = 8002
    langgraph_public_url: HttpUrl = HttpUrl("http://127.0.0.1:8002/")

    inventory_agent_host: str = "127.0.0.1"
    inventory_agent_port: PositiveInt = 8003
    inventory_agent_public_url: HttpUrl = HttpUrl("http://127.0.0.1:8003/")

    inventory_api_url: HttpUrl = HttpUrl("https://koko-demo-api.azurewebsites.net/inventory/")
    inventory_mode: Literal["live", "fixture"] = "fixture"
    inventory_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    inventory_max_attempts: int = Field(default=2, ge=1, le=3)
    inventory_retry_delay_seconds: float = Field(default=0.2, ge=0, le=5)
    inventory_fallback_to_fixture: bool = True

    a2a_timeout_seconds: PositiveInt = 120
    max_input_chars: PositiveInt = 20_000
    log_level: str = "INFO"

    def require_foundry(self) -> None:
        """Fail fast before a live model client is created."""
        missing: list[str] = []
        if not self.foundry_project_endpoint:
            missing.append("FOUNDRY_PROJECT_ENDPOINT")
        if not self.foundry_model:
            missing.append("FOUNDRY_MODEL")
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required Microsoft Foundry settings: {names}")


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""
    return Settings()
