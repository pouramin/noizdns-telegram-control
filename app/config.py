from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def _parse_allowed_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        ids.add(int(chunk))
    return ids


def _get_or_create_secret_key() -> str:
    env_key = os.getenv("APP_SECRET_KEY", "").strip()
    if env_key:
        return env_key

    key_path = BASE_DIR / ".app_secret_key"
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()

    key = Fernet.generate_key().decode("utf-8")
    key_path.write_text(key, encoding="utf-8")
    return key


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    app_secret_key: str
    default_ssh_timeout: int
    allowed_telegram_user_ids: set[int]
    git_repo_url: str
    git_branch: str
    host: str
    port: int


def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./app.db").strip(),
        app_secret_key=_get_or_create_secret_key(),
        default_ssh_timeout=int(os.getenv("DEFAULT_SSH_TIMEOUT", "20")),
        allowed_telegram_user_ids=_parse_allowed_ids(os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")),
        git_repo_url=os.getenv("GIT_REPO_URL", "https://github.com/pouramin/noizdns-deploy.git").strip(),
        git_branch=os.getenv("GIT_BRANCH", "main").strip(),
        host=os.getenv("HOST", "127.0.0.1").strip(),
        port=int(os.getenv("PORT", "8000")),
    )


settings = get_settings()
