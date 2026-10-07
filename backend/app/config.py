"""Runtime configuration. Missing provider credentials mean unavailable capabilities."""
from __future__ import annotations

from functools import lru_cache
from pydantic import AliasChoices, Field, SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str = Field(default="sqlite:///./ditto.db", validation_alias=AliasChoices("DITTO_DATABASE_URL", "DATABASE_URL", "database_url"))
    demo_mode: bool = Field(default=False, validation_alias=AliasChoices("DITTO_DEMO_MODE", "demo_mode"))
    media_root: str = Field(default="./private_media", validation_alias=AliasChoices("DITTO_MEDIA_ROOT", "media_root"))
    appwrite_endpoint: str = "https://sgp.cloud.appwrite.io/v1"
    appwrite_project_id: str = "6ac46d45002b91afdd73"
    appwrite_api_key: SecretStr = SecretStr("")
    media_storage: str = Field(default="local", pattern=r"^(local|appwrite)$", validation_alias=AliasChoices("DITTO_MEDIA_STORAGE", "media_storage"))

    meta_access_token: SecretStr = SecretStr("")
    instagram_app_id: str = Field(default="1107232135218848", pattern=r"^\d+$")
    instagram_app_secret: SecretStr = SecretStr("")
    public_base_url: str = ""
    token_encryption_key: SecretStr = SecretStr("")
    meta_api_version: str = Field(default="v25.0", pattern=r"^v[0-9]+\.0$")
    serpapi_api_key: SecretStr = SecretStr("")
    search_monthly_unit_limit: int = Field(default=225,ge=0,le=250)
    search_user_monthly_unit_limit: int = Field(default=10,ge=0,le=250)
    google_cloud_api_key: SecretStr = SecretStr("")
    vision_monthly_unit_limit: int = Field(default=900,ge=0,le=900)
    vision_user_monthly_unit_limit: int = Field(default=40,ge=0,le=900)
    meta_ad_library_token: str = ""
    llm_api_key: str = ""
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = Field(default="gemini-3.5-flash-lite", pattern=r"^gemini-[a-zA-Z0-9.-]+$")

    support_email: str = "svarsha.t@gmail.com"
    operator_name: str = "Svarsha T"
    smtp_from: str = ""
    smtp_host: str = ""
    smtp_port: int = 0
    smtp_user: str = ""
    smtp_password: str = ""
    cloud_email_outreach_enabled: bool = False

    # Follow-up cadence in days; the scheduler re-evaluates open cases on this interval.
    follow_up_interval_days: int = 7
    processing_worker_enabled: bool = True

    @property
    def has_llm(self) -> bool:
        return bool(self.llm_api_key) and not self.demo_mode

    @property
    def has_vision(self) -> bool:
        return bool(self.google_cloud_api_key.get_secret_value()) and not self.demo_mode

    @property
    def has_meta(self) -> bool:
        return bool(self.meta_access_token.get_secret_value())

    @property
    def outreach_is_live(self) -> bool:
        return bool(self.cloud_email_outreach_enabled and self.smtp_host and
                    self.smtp_port in (465,587) and self.smtp_from and self.smtp_user and self.smtp_password)

    def provider_status(self) -> dict[str, str]:
        """Human-readable status for /api/health, so callers know what is real."""
        return {
            "ai_drafting": (f"Gemini ({self.gemini_model}): key configured; connectivity not verified by health" if self.gemini_api_key.get_secret_value() else "Gemini: key not configured"),
            "instagram": ("Instagram OAuth: app secret configured; live sign-in not verified by health" if self.instagram_app_secret.get_secret_value() else "Instagram OAuth: app secret not configured"),
            "verification":"Measured similarity only; infringement and manipulation classifiers unavailable",
            "discovery":("Google web-image search configured; results require review" if self.has_vision else
                         "No live discovery provider configured; submitted media comparison available"),
            "own_content":"Private uploads and per-user Instagram OAuth import; each user must authorize their own connection",
            "outreach":"SMTP configured; recipient and evidence confirmation required" if self.outreach_is_live else "Email sender unavailable",
            "matching":"Visual similarity analysis",
            "media_storage":("Appwrite originals with local hashing copies; connectivity not checked by health" if self.media_storage == "appwrite" else "Private local originals"),
            "manipulation":"Unavailable; no detector configured",
        }



@lru_cache
def get_settings() -> Settings:
    return Settings()
