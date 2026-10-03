from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://decor:local-development-only@127.0.0.1:5432/decor"
    auth_secret: SecretStr = SecretStr("development-only-replace-before-production-32-chars")
    allowed_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    session_hours: int = Field(default=168, ge=1, le=720)
    idle_minutes: int = Field(default=1440, ge=1, le=10080)
    admin_session_hours: int = Field(default=8, ge=1, le=24)
    admin_idle_minutes: int = Field(default=30, ge=1, le=120)
    login_limit: int = Field(default=10, ge=1, le=100)
    auth_ip_limit: int = Field(default=50, ge=1, le=1000)
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr = SecretStr("")
    razorpay_webhook_secret: SecretStr = SecretStr("")
    cloudinary_cloud_name: str = Field(default="", pattern=r"^[a-zA-Z0-9_-]*$")
    cloudinary_api_key: SecretStr = SecretStr("")
    cloudinary_api_secret: SecretStr = SecretStr("")
    email_notifications_enabled: bool = False
    whatsapp_notifications_enabled: bool = False
    resend_api_key: SecretStr = SecretStr("")
    notification_from_email: str = ""
    whatsapp_access_token: SecretStr = SecretStr("")
    whatsapp_phone_number_id: str = Field(default="", pattern=r"^[0-9]*$")
    whatsapp_api_version: str = Field(default="", pattern=r"^(v[0-9]+\.0)?$")
    whatsapp_template_language: str = Field(default="en", pattern=r"^[a-z]{2}(?:_[A-Z]{2})?$")
    whatsapp_templates: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def production_security(self):
        if self.email_notifications_enabled and (
            not self.resend_api_key.get_secret_value() or not self.notification_from_email
        ):
            raise ValueError(
                "Email notifications require RESEND_API_KEY and NOTIFICATION_FROM_EMAIL"
            )
        if self.whatsapp_notifications_enabled and not all(
            [
                self.whatsapp_access_token.get_secret_value(),
                self.whatsapp_phone_number_id,
                self.whatsapp_api_version,
                self.whatsapp_templates,
            ]
        ):
            raise ValueError(
                "WhatsApp notifications require token, phone ID, API version and approved templates"
            )
        if any(origin == "*" or origin.endswith("/") for origin in self.allowed_origins):
            raise ValueError("Use exact origins without trailing slash")
        if self.app_env == "production":
            secret = self.auth_secret.get_secret_value()
            if len(secret) < 32 or secret.startswith("development-only"):
                raise ValueError("Production requires a strong AUTH_SECRET")
            if not self.allowed_origins or any(
                not x.startswith("https://") for x in self.allowed_origins
            ):
                raise ValueError("Production requires explicit HTTPS origins")
            if "local-development-only" in self.database_url:
                raise ValueError("Production requires database credentials")
        return self

    @property
    def session_cookie(self) -> str:
        return "__Host-decor-session" if self.app_env == "production" else "decor-session"

    @property
    def csrf_cookie(self) -> str:
        return "__Host-decor-preauth" if self.app_env == "production" else "decor-preauth"


@lru_cache
def get_settings() -> Settings:
    return Settings()
