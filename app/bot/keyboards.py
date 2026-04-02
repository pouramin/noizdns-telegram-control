from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["Servers", "Add Server"], ["Help"]],
        resize_keyboard=True,
    )


def auth_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["password", "private_key"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def servers_keyboard(servers: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(name, callback_data=f"server:{server_id}")] for server_id, name in servers]
    return InlineKeyboardMarkup(rows or [[InlineKeyboardButton("No servers yet", callback_data="noop")]])


def server_actions_keyboard(server_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Status", callback_data=f"action:{server_id}:status")],
            [InlineKeyboardButton("Install", callback_data=f"action:{server_id}:install")],
            [InlineKeyboardButton("Users list", callback_data=f"action:{server_id}:users_list")],
            [InlineKeyboardButton("Restart service", callback_data=f"action:{server_id}:service_restart")],
            [InlineKeyboardButton("Logs", callback_data=f"action:{server_id}:logs")],
        ]
    )
