from telegram import Update, Bot
from telegram.error import TelegramError
from config import REQUIRED_CHANNEL, CHANNEL_INVITE_LINK
import logging

logger = logging.getLogger(__name__)


async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        return True


def get_user_display_name(user) -> str:
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username or str(user.id)


def fmt_date(dt_str: str) -> str:
    if not dt_str:
        return "N/A"
    try:
        from datetime import datetime
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y")
    except Exception:
        return dt_str[:10]


def fmt_datetime(dt_str: str) -> str:
    if not dt_str:
        return "N/A"
    try:
        from datetime import datetime
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return dt_str
