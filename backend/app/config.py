"""Runtime configuration.

Every external provider is optional. A missing key is not an error: the relevant
capability falls back to its Demo Mode implementation and reports that plainly,
so the API never claims a live integration it does not have (report §51).
"""
from __future__ import annotations

from functools import lru_cache
from pydantic import AliasChoices, Field

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str = Field(default="sqlite:///./ditto.db", validation_alias=AliasChoices("DITTO_DATABASE_URL", "database_url"))
    demo_mode: bool = Field(default=True, validation_alias=AliasChoices("DITTO_DEMO_MODE", "demo_mode"))
    media_root: str = Field(default="./private_media", validation_alias=AliasChoices("DITTO_MEDIA_ROOT", "media_root"))

    meta_access_token: str = ""
    google_cloud_api_key: str = ""
    meta_ad_library_token: str = ""
    llm_api_key: str = ""

    smtp_host: str = ""
    smtp_port: int = 0
    smtp_user: str = ""
    smtp_password: str = ""

    # Follow-up cadence in days; the scheduler re-evaluates open cases on this interval.
    follow_up_interval_days: int = 7

    @property
    def has_llm(self) -> bool:
        return bool(self.llm_api_key) and not self.demo_mode

    @property
    def has_vision(self) -> bool:
        return bool(self.google_cloud_api_key) and not self.demo_mode

    @property
    def has_meta(self) -> bool:
        return bool(self.meta_access_token) and not self.demo_mode

    @property
    def outreach_is_live(self) -> bool:
        return False  # No live transport adapter is installed.

    def provider_status(self) -> dict[str, str]:
        """Human-readable status for /api/health, so callers know what is real."""
        return {
            "verification":"Demo Verification Agent (deterministic rules; no LLM called)",
            "discovery":"Demo discovery corpus (synthetic, no live scraping)",
            "own_content":"Local upload only (Meta adapter unavailable in this build)",
            "outreach":"Sandboxed — messages are recorded, never transmitted",
            "matching":"Measured five-frame pHash (local)",
            "manipulation":"Unavailable; simulated evidence only",
        }



@lru_cache
def get_settings() -> Settings:
    return Settings()
