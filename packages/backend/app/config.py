import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = "change-this-webhook-secret"
    TELEGRAM_AUTH_SECRET: str = "change-this-auth-secret"
    BACKEND_SECRET_KEY: str = "change-this-backend-secret"
    HISTORY_RETENTION_HOURS: int = 72
    MAX_UPLOAD_SIZE_MB: int = 25
    CORS_ALLOW_ORIGINS: str = "*"
    DATA_DIR: str = "./data"
    TELEGRAM_POLLING_MODE: bool = False
    SITE_NAMES_MAPPING: str = "{}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def site_names(self) -> dict[str, str]:
        """Parses configured website mappings (JSON or key=value format)."""
        mapping: dict[str, str] = {}
        if not self.SITE_NAMES_MAPPING:
            return mapping
        raw = self.SITE_NAMES_MAPPING.strip()
        if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
            raw = raw[1:-1].strip()

        try:
            if raw.startswith("{"):
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return {str(k).strip(): str(v).strip() for k, v in parsed.items()}
        except Exception:
            pass

        for pair in raw.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                mapping[k.strip()] = v.strip()
            elif ":" in pair and not pair.strip().startswith("{"):
                k, v = pair.split(":", 1)
                mapping[k.strip().strip('"').strip("'")] = v.strip().strip('"').strip("'")
        return mapping

    @property
    def data_path(self) -> Path:
        clean_dir = self.DATA_DIR.strip('"').strip("'").strip()
        p = Path(clean_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        return self.data_path / "chat.db"


settings = Settings()
