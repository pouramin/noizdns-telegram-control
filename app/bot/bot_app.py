from __future__ import annotations

from telegram.ext import Application

from app.bot.handlers import build_application_handlers
from app.config import settings


def build_bot_app() -> Application:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    application = Application.builder().token(settings.bot_token).build()
    build_application_handlers(application)
    return application
