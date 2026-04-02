# NoizDNS Telegram Control

Telegram bot + FastAPI backend for installing and controlling **NoizDNS** servers through the `noizdns-admin` interface.

## What this project is

This repo is the **control plane**, not the installer itself.

- `pouramin/noizdns-deploy` stays focused on install + server-side management
- this repo adds:
  - Telegram bot
  - FastAPI backend
  - SQLite storage
  - SSH-based command execution
  - server registry
  - NoizDNS action mapping

## MVP scope

Current MVP supports:

- add server
- install NoizDNS on server
- status
- config show
- users list
- users add / remove / passwd
- service restart / start / stop
- logs

No arbitrary shell is exposed.

## Architecture

Telegram Bot -> FastAPI -> SQLite -> SSH -> noizdns-admin on remote server

## Important assumptions

For the first MVP, remote commands are executed over SSH.

The target server should satisfy one of these:

1. SSH as `root`
2. SSH as a user with working `sudo`
3. if using password auth, the SSH password should also work for `sudo -S`
4. if using private key auth for a non-root user, passwordless sudo is recommended

## Quick start

### 1) Create virtualenv

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment

Copy `.env.example` to `.env` and fill:

- `BOT_TOKEN`
- `ALLOWED_TELEGRAM_USER_IDS`
- optionally `APP_SECRET_KEY`

If `APP_SECRET_KEY` is empty, the app generates one into `.app_secret_key` on first run.

### 4) Run

```bash
python run.py
```

API will start on the configured host/port, and the Telegram bot will start polling if `BOT_TOKEN` is set.

## Telegram flows

### Main
- `/start`
- `Servers`
- `Add Server`
- `Help`

### After selecting a server
- Status
- Install
- Users list
- Restart service
- Logs

### Extra commands
After selecting a server from the menu:

```text
/useradd <username> <password>
/userdel <username>
/passwd <username> <new_password>
```

## API examples

### Create server
```bash
curl -X POST http://127.0.0.1:8000/servers \
  -H "Content-Type: application/json" \
  -d '{
    "owner_telegram_user_id": 123456789,
    "name": "vps-1",
    "host": "1.2.3.4",
    "port": 22,
    "username": "root",
    "auth_type": "password",
    "password": "YOUR_PASSWORD",
    "noizdns_domain": "t.example.com",
    "noizdns_mtu": 1232
  }'
```

### Install NoizDNS
```bash
curl -X POST http://127.0.0.1:8000/servers/1/install
```

### Status
```bash
curl http://127.0.0.1:8000/servers/1/status
```

## Security notes

This is an MVP.

Recommended next hardening steps:

- host key verification
- encrypted credential storage with a stronger ops model
- per-user RBAC
- audit log
- job queue
- agent-based mode instead of direct SSH
- better secret rotation
- webhook mode for Telegram instead of polling in production

## فارسی

این پروژه خود **نصب‌کننده‌ی NoizDNS** نیست؛
بلکه لایه‌ی **کنترل و مدیریت از طریق تلگرام** برای پروژه‌ی `noizdns-deploy` است.

### کارهایی که نسخه‌ی فعلی انجام می‌دهد
- اضافه کردن سرور
- نصب NoizDNS روی سرور
- گرفتن وضعیت
- نمایش config
- لیست کاربران
- ساخت / حذف / تغییر پسورد کاربر
- ریستارت سرویس
- گرفتن لاگ

### چیزی که عمدا نداریم
- شل آزاد
- اجرای دستور دلخواه
- ترمینال عمومی روی تلگرام

### پیش‌فرض‌های مهم
برای MVP فعلی، اجرای دستورها با SSH انجام می‌شود.
پس بهتر است سرور یکی از این حالت‌ها را داشته باشد:

1. ورود با `root`
2. یا کاربری که `sudo` درست دارد
3. اگر با پسورد SSH وصل می‌شوی، بهتر است همان پسورد برای `sudo -S` هم جواب بدهد
4. اگر با private key و کاربر غیر root وصل می‌شوی، بهتر است passwordless sudo داشته باشی

### اجرای پروژه
1. فایل `.env.example` را به `.env` تبدیل کن
2. `BOT_TOKEN` و `ALLOWED_TELEGRAM_USER_IDS` را پر کن
3. وابستگی‌ها را نصب کن
4. `python run.py` را اجرا کن

### مرحله‌ی بعدی پیشنهادی
- audit log
- queue
- agent-based architecture
- webhook
- role-based access control
