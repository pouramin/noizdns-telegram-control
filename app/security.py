from __future__ import annotations

from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.app_secret_key.encode("utf-8"))


def encrypt_text(value: str) -> str:
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
