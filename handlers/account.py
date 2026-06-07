import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from utils.helpers import get_user_display_name, fmt_date
from config import FREE_DAILY_SEARCHES, ADMIN_IDS

logger = logging.getLogger(__name__)


async def account_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    row = await db.get_user(user.id)
    premium = await db.is_premium(user.id)
    prem_info = await db.get_premium_info(user.id)
    used_today = await db.get_daily_search_count(user.id)

    name = get_user_display_name(user)
    username = f"@{user.username}" if user.username else "N/A"
    badge = "💎 VIP PREMIUM" if premium else "👤 Free User"
    status_icon = "✅" if premium else "❌"
    total = row["total_searches"] if row else 0
    is_adm = "👑 Admin" if user.id in ADMIN_IDS else ""

    if premium and prem_info:
        expiry = fmt_date(prem_info["expires_at"])
        plan = prem_info["plan_key"].upper() if prem_info["plan_key"] else "N/A"
    else:
        expiry = "N/A"
        plan = "N/A"

    if premium:
        credits_line = "📜 Remaining Credits: <b>Unlimited ♾️</b>"
    else:
        remaining = max(0, FREE_DAILY_SEARCHES - used_today)
        credits_line = f"📜 Remaining Credits: <b>{remaining} / {FREE_DAILY_SEARCHES}</b>"

    vip_badge = "🏅 <b>VIP MEMBER</b>" if premium else "🔓 Not a VIP member"

    text = f"""
👤 <b>MY ACCOUNT</b>
━━━━━━━━━━━━━━━━━━━━━━

👤 Name: <b>{name}</b>
📛 Username: <b>{username}</b>
🆔 User ID: <b>{user.id}</b>
{f"🛡 Role: <b>{is_adm}</b>" if is_adm else ""}
💎 Premium: <b>{status_icon} {badge}</b>
📋 Plan: <b>{plan}</b>
📅 Expiry: <b>{expiry}</b>

📊 Total Searches: <b>{total}</b>
🔍 Today's Searches: <b>{used_today}</b>
{credits_line}

{vip_badge}
━━━━━━━━━━━━━━━━━━━━━━
🔥 <b>CYBER WILD WAVE</b>
""".strip()

    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
