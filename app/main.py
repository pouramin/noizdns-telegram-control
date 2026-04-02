from __future__ import annotations

import uvicorn
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app.bot.bot_app import build_bot_app
from app.config import settings
from app.db import Base, engine, get_db
from app.schemas.server import ServerCreate, ServerRead
from app.schemas.user import RemotePasswordChange, RemoteUserCreate
from app.services import noizdns_service, server_service

bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app
    Base.metadata.create_all(bind=engine)
    if settings.bot_token:
        bot_app = build_bot_app()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
    try:
        yield
    finally:
        if bot_app:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()


app = FastAPI(title="NoizDNS Telegram Control", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/servers", response_model=list[ServerRead])
def list_servers(telegram_user_id: int = Query(...), db: Session = Depends(get_db)):
    return server_service.list_servers_for_user(db, telegram_user_id)


@app.post("/servers", response_model=ServerRead)
def create_server(payload: ServerCreate, db: Session = Depends(get_db)):
    return server_service.create_server(db, payload)


def _server_or_404(db: Session, server_id: int):
    server = server_service.get_server_by_id(db, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@app.post("/servers/{server_id}/install")
def install_server(server_id: int, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.install_noizdns(server)}


@app.get("/servers/{server_id}/status")
def server_status(server_id: int, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.status(server)}


@app.get("/servers/{server_id}/config")
def server_config(server_id: int, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.config_show(server)}


@app.post("/servers/{server_id}/service/{action}")
def server_service_action(server_id: int, action: str, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.service_action(server, action)}


@app.get("/servers/{server_id}/logs")
def server_logs(server_id: int, lines: int = 100, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.logs(server, lines)}


@app.get("/servers/{server_id}/users")
def server_users(server_id: int, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.users_list(server)}


@app.post("/servers/{server_id}/users")
def add_server_user(server_id: int, payload: RemoteUserCreate, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.users_add(server, payload.username, payload.password)}


@app.delete("/servers/{server_id}/users/{username}")
def remove_server_user(server_id: int, username: str, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.users_remove(server, username)}


@app.post("/servers/{server_id}/users/{username}/password")
def change_server_user_password(server_id: int, username: str, payload: RemotePasswordChange, db: Session = Depends(get_db)):
    server = _server_or_404(db, server_id)
    return {"output": noizdns_service.users_passwd(server, username, payload.password)}


def run():
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
