from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards import auth_type_keyboard, main_menu_keyboard, server_actions_keyboard, servers_keyboard
from app.bot.states import (
    ADD_SERVER_AUTH_TYPE,
    ADD_SERVER_DOMAIN,
    ADD_SERVER_HOST,
    ADD_SERVER_MTU,
    ADD_SERVER_NAME,
    ADD_SERVER_PORT,
    ADD_SERVER_SECRET,
    ADD_SERVER_USERNAME,
)
from app.config import settings
from app.db import SessionLocal
from app.schemas.server import ServerCreate
from app.services import noizdns_service, server_service


def _is_allowed(user_id: int) -> bool:
    allowed = settings.allowed_telegram_user_ids
    return not allowed or user_id in allowed


async def _guard(update) -> bool:
    user = update.effective_user
    if not user or not _is_allowed(user.id):
        target = update.effective_message
        if target:
            await target.reply_text("Access denied.")
        return False
    return True


def _db():
    return SessionLocal()


async def start(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await update.message.reply_text(
        "Welcome to NoizDNS Telegram Control.\nChoose an action:",
        reply_markup=main_menu_keyboard(),
    )


async def help_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    text = (
        "Available flows:\n"
        "- Add Server\n"
        "- Servers\n\n"
        "Server actions currently available:\n"
        "- Install NoizDNS\n"
        "- Status\n"
        "- Users list\n"
        "- Restart service\n"
        "- Logs\n\n"
        "Advanced commands after selecting a server:\n"
        "/useradd <username> <password>\n"
        "/userdel <username>\n"
        "/passwd <username> <new_password>"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())


async def show_servers(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    db = _db()
    try:
        servers = server_service.list_servers_for_user(db, update.effective_user.id)
        payload = [(server.id, f"{server.name} ({server.host})") for server in servers]
    finally:
        db.close()
    await update.message.reply_text("Your servers:", reply_markup=servers_keyboard(payload))


async def add_server_entry(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _guard(update):
        return ConversationHandler.END
    context.user_data["new_server"] = {}
    await update.message.reply_text("Server name?")
    return ADD_SERVER_NAME


async def add_server_name(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_server"]["name"] = update.message.text.strip()
    await update.message.reply_text("Server IP or hostname?")
    return ADD_SERVER_HOST


async def add_server_host(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_server"]["host"] = update.message.text.strip()
    await update.message.reply_text("SSH port? (default 22)")
    return ADD_SERVER_PORT


async def add_server_port(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    context.user_data["new_server"]["port"] = int(raw or "22")
    await update.message.reply_text("SSH username?")
    return ADD_SERVER_USERNAME


async def add_server_username(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_server"]["username"] = update.message.text.strip()
    await update.message.reply_text("Auth type?", reply_markup=auth_type_keyboard())
    return ADD_SERVER_AUTH_TYPE


async def add_server_auth_type(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    auth_type = update.message.text.strip().lower()
    if auth_type not in {"password", "private_key"}:
        await update.message.reply_text("Please choose password or private_key.")
        return ADD_SERVER_AUTH_TYPE
    context.user_data["new_server"]["auth_type"] = auth_type
    if auth_type == "password":
        await update.message.reply_text("SSH password?")
    else:
        await update.message.reply_text("Paste private key content.")
    return ADD_SERVER_SECRET


async def add_server_secret(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    auth_type = context.user_data["new_server"]["auth_type"]
    secret = update.message.text
    if auth_type == "password":
        context.user_data["new_server"]["password"] = secret
    else:
        context.user_data["new_server"]["private_key"] = secret
    await update.message.reply_text("NoizDNS domain? Example: t.example.com")
    return ADD_SERVER_DOMAIN


async def add_server_domain(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_server"]["noizdns_domain"] = update.message.text.strip()
    await update.message.reply_text("MTU? (default 1232)")
    return ADD_SERVER_MTU


async def add_server_mtu(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    context.user_data["new_server"]["noizdns_mtu"] = int(raw or "1232")
    data = context.user_data["new_server"]

    payload = ServerCreate(
        owner_telegram_user_id=update.effective_user.id,
        name=data["name"],
        host=data["host"],
        port=data["port"],
        username=data["username"],
        auth_type=data["auth_type"],
        password=data.get("password"),
        private_key=data.get("private_key"),
        noizdns_domain=data["noizdns_domain"],
        noizdns_mtu=data["noizdns_mtu"],
    )

    db = _db()
    try:
        server = server_service.create_server(db, payload)
    finally:
        db.close()

    context.user_data["active_server_id"] = server.id
    await update.message.reply_text(
        f"Server saved: {server.name}\nYou can now open it from Servers.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def cancel(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("new_server", None)
    await update.message.reply_text("Cancelled.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


async def server_selected(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await _guard(update):
        return

    _, server_id = query.data.split(":")
    context.user_data["active_server_id"] = int(server_id)

    db = _db()
    try:
        server = server_service.get_server_for_user(db, int(server_id), query.from_user.id)
    finally:
        db.close()

    if not server:
        await query.edit_message_text("Server not found.")
        return

    await query.edit_message_text(
        f"Server: {server.name}\nHost: {server.host}\nDomain: {server.noizdns_domain}",
        reply_markup=server_actions_keyboard(server.id),
    )


def _get_active_server_for_user(user_id: int, context):
    server_id = context.user_data.get("active_server_id")
    if not server_id:
        return None
    db = _db()
    try:
        return server_service.get_server_for_user(db, int(server_id), user_id)
    finally:
        db.close()


async def server_action(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await _guard(update):
        return

    _, server_id_raw, action = query.data.split(":", 2)
    server_id = int(server_id_raw)

    db = _db()
    try:
        server = server_service.get_server_for_user(db, server_id, query.from_user.id)
    finally:
        db.close()

    if not server:
        await query.edit_message_text("Server not found.")
        return

    try:
        if action == "status":
            output = noizdns_service.status(server)
        elif action == "install":
            await query.edit_message_text("Installing NoizDNS... this can take a while.")
            output = noizdns_service.install_noizdns(server)
        elif action == "users_list":
            output = noizdns_service.users_list(server)
        elif action == "service_restart":
            output = noizdns_service.service_action(server, "restart")
        elif action == "logs":
            output = noizdns_service.logs(server, 100)
        else:
            output = "Unknown action."
    except Exception as exc:
        output = f"Action failed:\n{exc}"

    if len(output) > 3500:
        output = output[:3500] + "\n\n[truncated]"

    await query.edit_message_text(output, reply_markup=server_actions_keyboard(server.id))


async def useradd_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /useradd <username> <password>")
        return
    server = _get_active_server_for_user(update.effective_user.id, context)
    if not server:
        await update.message.reply_text("Select a server first from Servers.")
        return
    username, password = context.args
    try:
        output = noizdns_service.users_add(server, username, password)
    except Exception as exc:
        output = f"Action failed:\n{exc}"
    await update.message.reply_text(output)


async def userdel_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /userdel <username>")
        return
    server = _get_active_server_for_user(update.effective_user.id, context)
    if not server:
        await update.message.reply_text("Select a server first from Servers.")
        return
    try:
        output = noizdns_service.users_remove(server, context.args[0])
    except Exception as exc:
        output = f"Action failed:\n{exc}"
    await update.message.reply_text(output)


async def passwd_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /passwd <username> <new_password>")
        return
    server = _get_active_server_for_user(update.effective_user.id, context)
    if not server:
        await update.message.reply_text("Select a server first from Servers.")
        return
    username, password = context.args
    try:
        output = noizdns_service.users_passwd(server, username, password)
    except Exception as exc:
        output = f"Action failed:\n{exc}"
    await update.message.reply_text(output)


def build_application_handlers(application: Application) -> None:
    add_server_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Add Server$"), add_server_entry),
            CommandHandler("addserver", add_server_entry),
        ],
        states={
            ADD_SERVER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_name)],
            ADD_SERVER_HOST: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_host)],
            ADD_SERVER_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_port)],
            ADD_SERVER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_username)],
            ADD_SERVER_AUTH_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_auth_type)],
            ADD_SERVER_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_secret)],
            ADD_SERVER_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_domain)],
            ADD_SERVER_MTU: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_mtu)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("servers", show_servers))
    application.add_handler(CommandHandler("useradd", useradd_command))
    application.add_handler(CommandHandler("userdel", userdel_command))
    application.add_handler(CommandHandler("passwd", passwd_command))
    application.add_handler(MessageHandler(filters.Regex("^Servers$"), show_servers))
    application.add_handler(MessageHandler(filters.Regex("^Help$"), help_command))
    application.add_handler(add_server_conv)
    application.add_handler(CallbackQueryHandler(server_selected, pattern=r"^server:\d+$"))
    application.add_handler(CallbackQueryHandler(server_action, pattern=r"^action:\d+:.+$"))
