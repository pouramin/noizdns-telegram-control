from __future__ import annotations

from pydantic import BaseModel, Field


class ServerCreate(BaseModel):
    owner_telegram_user_id: int
    name: str = Field(min_length=1, max_length=255)
    host: str = Field(min_length=1, max_length=255)
    port: int = 22
    username: str = Field(min_length=1, max_length=255)
    auth_type: str
    password: str | None = None
    private_key: str | None = None
    noizdns_domain: str = Field(min_length=1, max_length=255)
    noizdns_mtu: int = 1232


class ServerRead(BaseModel):
    id: int
    owner_telegram_user_id: int
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    noizdns_domain: str
    noizdns_mtu: int

    class Config:
        from_attributes = True
