from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Server
from app.schemas.server import ServerCreate
from app.security import decrypt_text, encrypt_text


def create_server(db: Session, payload: ServerCreate) -> Server:
    server = Server(
        owner_telegram_user_id=payload.owner_telegram_user_id,
        name=payload.name,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        auth_type=payload.auth_type,
        password_encrypted=encrypt_text(payload.password) if payload.password else None,
        private_key_encrypted=encrypt_text(payload.private_key) if payload.private_key else None,
        noizdns_domain=payload.noizdns_domain,
        noizdns_mtu=payload.noizdns_mtu,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


def list_servers_for_user(db: Session, telegram_user_id: int) -> list[Server]:
    return (
        db.query(Server)
        .filter(Server.owner_telegram_user_id == telegram_user_id)
        .order_by(Server.created_at.desc())
        .all()
    )


def get_server_for_user(db: Session, server_id: int, telegram_user_id: int) -> Server | None:
    return (
        db.query(Server)
        .filter(Server.id == server_id, Server.owner_telegram_user_id == telegram_user_id)
        .first()
    )


def get_server_by_id(db: Session, server_id: int) -> Server | None:
    return db.query(Server).filter(Server.id == server_id).first()


def resolved_secret(server: Server) -> tuple[str | None, str | None]:
    return decrypt_text(server.password_encrypted), decrypt_text(server.private_key_encrypted)
