import logging
import os
import platform
import time
import asyncio
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards.admin_kb import (
    admin_panel_keyboard, bot_control_keyboard, confirm_keyboard,
    logs_keyboard, freeze_keyboard, back_admin_keyboard,
)
from keyboards.main_kb import admin_main_keyboard, admin_submenu_keyboard
from utils.rate_limiter import set_pending_action, get_pending_action, clear_pending_action
from config import ADMIN_IDS, PREMIUM_PLANS, BOT_VERSION, BOT_NAME
import config as cfg

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)

IST_TZ = ZoneInfo("Asia/Kolkata")
_IST_DELTA = timedelta(hours=5, minutes=30)

SEARCH_TYPE_LABELS = {
    "search_number":   ("📱", "Number Lookup"),
    "search_telegram": ("📞", "Telegram Lookup"),
    "search_aadhaar":  ("🪪", "Aadhaar Lookup"),
    "search_family":   ("👨‍👩‍👧‍👦", "Family Lookup"),
    "search_pincode":  ("📍", "Pincode Lookup"),
    "search_ifsc":     ("🏦", "IFSC Lookup"),
    "search_vehicle":  ("🚗", "Vehicle Lookup"),
}

ADMIN_SUBMENU_BUTTONS = {
    "🛠 Bot Control",    "💎 Grant Premium",  "🚫 Revoke Premium",
    "❌ Remove User",    "👥 Users Summary",  "📊 Live Statistics",
    "📢 Broadcast",      "📋 Premium Users",  "🔄 Lifetime Update",
    "🧹 Clear Database", "🔐 Ban User",        "✅ Unban User",
    "⚡ Server Status",  "📂 Export Users",   "📝 Logs",
}

# Full set of buttons routed to the admin handler (entry + submenu + back)
ADMIN_PANEL_BUTTONS = ADMIN_SUBMENU_BUTTONS | {"👑 Admin Panel", "🔙 Back"}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _fmt_ist(created_at: str):
    try:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") + _IST_DELTA
        return dt.strftime("%d-%m-%Y"), dt.strftime("%I:%M:%S %p")
    except Exception:
        return "N/A", "N/A"


def _now_ist_str() -> str:
    return datetime.now(IST_TZ).strftime("%d-%m-%Y  %I:%M:%S %p IST")


def _fmt_duration(seconds: int) -> str:
    if seconds <= 0:
        return "Expired"
    days  = seconds // 86400
    hours = (seconds % 86400) // 3600
    mins  = (seconds % 3600) // 60
    parts = []
    if days:  parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if mins:  parts.append(f"{mins}m")
    return " ".join(parts) or "~1m"


def _build_logs_text(logs) -> str:
    if not logs:
        return (
            "📝 <b>RECENT SEARCH LOGS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>No search logs found.</i>\n\n"
            "🔥 <b>CYBER WILD WAVE</b>"
        )
    lines = ["📝 <b>RECENT SEARCH LOGS</b>", "━━━━━━━━━━━━━━━━━━━━━━"]
    for row in logs:
        emoji, label = SEARCH_TYPE_LABELS.get(row["search_type"], ("🔍", row["search_type"]))
        date_str, time_str = _fmt_ist(row["created_at"])
        name  = row["full_name"] or "Unknown"
        uid   = row["user_id"]
        query = row["query"] or "—"
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"👤 <b>User:</b> {name}")
        lines.append(f"🆔 <b>ID:</b> <code>{uid}</code>")
        lines.append(f"🔍 <b>Type:</b> {emoji} {label}")
        lines.append(f"📱 <b>Query:</b> <code>{query}</code>")
        lines.append(f"📅 <b>Date:</b> {date_str}  🕒 {time_str} IST")
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🔥 <b>CYBER WILD WAVE</b>")
    return "\n".join(lines)


# ── /admin command (still available as convenience) ────────────────────────────

async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Access Denied.")
        return
    await update.message.reply_text(
        f"🔥 <b>CYBER WILD WAVE</b>\n"
        f"👑 <b>ADMIN PANEL</b>\n\n"
        f"Welcome, <b>{user.first_name}</b>!\n"
        f"Version: <code>{BOT_VERSION}</code>\n"
        f"🕐 {_now_ist_str()}\n\n"
        f"📲 Use the buttons below ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_main_keyboard()
    )


# ── Inline callback router ─────────────────────────────────────────────────────

async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ Unauthorized", show_alert=True)
        return

    data = query.data

    if data == "adm_back":
        await query.edit_message_text(
            f"🔥 <b>CYBER WILD WAVE</b> | 👑 Admin Panel\n\n📲 Use the buttons below ↓",
            parse_mode=ParseMode.HTML
        )

    elif data == "adm_close":
        await query.delete_message()

    elif data == "adm_bot_ctrl":
        maint = "🔴 ON" if cfg.MAINTENANCE_MODE else "🟢 OFF"
        await query.edit_message_text(
            f"🛠 <b>BOT CONTROL</b>\n\n"
            f"Maintenance Mode: <b>{maint}</b>\n"
            f"🕐 {_now_ist_str()}\n\n"
            f"🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=bot_control_keyboard()
        )

    elif data == "adm_ctrl_start":
        cfg.MAINTENANCE_MODE = False
        await db.log_admin_action(query.from_user.id, "bot started (maintenance off)")
        await query.answer("▶ Bot is now RUNNING", show_alert=True)
        await query.edit_message_text(
            f"🛠 <b>BOT CONTROL</b>\n\n🟢 Bot is now <b>RUNNING</b>\n🕐 {_now_ist_str()}\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML, reply_markup=bot_control_keyboard()
        )

    elif data == "adm_ctrl_stop":
        cfg.MAINTENANCE_MODE = True
        await db.freeze_premium_start()
        await db.log_admin_action(query.from_user.id, "bot stopped (maintenance on, timers frozen)")
        await query.answer("⏹ Bot is now in MAINTENANCE", show_alert=True)
        await query.edit_message_text(
            f"🛠 <b>BOT CONTROL</b>\n\n🔴 Bot in <b>MAINTENANCE MODE</b>\n"
            f"⏸ Premium timers frozen.\n🕐 {_now_ist_str()}\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML, reply_markup=bot_control_keyboard()
        )

    elif data == "adm_ctrl_maint":
        cfg.MAINTENANCE_MODE = not cfg.MAINTENANCE_MODE
        if cfg.MAINTENANCE_MODE:
            await db.freeze_premium_start()
            state = "ON 🔴"; note = "\n⏸ <i>Premium timers frozen.</i>"
        else:
            await db.freeze_premium_end()
            state = "OFF 🟢"; note = "\n▶ <i>Premium timers resumed.</i>"
        await query.answer(f"Maintenance: {state}", show_alert=True)
        await db.log_admin_action(query.from_user.id, f"maintenance toggled: {state}")
        maint_text = "🔴 ON" if cfg.MAINTENANCE_MODE else "🟢 OFF"
        await query.edit_message_text(
            f"🛠 <b>BOT CONTROL</b>\n\nMaintenance: <b>{maint_text}</b>{note}\n🕐 {_now_ist_str()}\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML, reply_markup=bot_control_keyboard()
        )

    elif data == "adm_ctrl_restart":
        await query.answer("🔄 Restarting bot...", show_alert=True)
        await db.log_admin_action(query.from_user.id, "restart requested")
        import sys
        os.execv(sys.executable, [sys.executable] + sys.argv)

    elif data == "adm_stats":
        stats = await db.get_stats()
        text = (
            f"📊 <b>LIVE STATISTICS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total Users: <b>{stats['total_users']}</b>\n"
            f"💎 Premium Users: <b>{stats['premium_users']}</b>\n"
            f"🔍 Today's Searches: <b>{stats['today_searches']}</b>\n"
            f"📊 Total Searches: <b>{stats['total_searches']}</b>\n"
            f"🟢 Active Today: <b>{stats['active_today']}</b>\n"
            f"🚫 Banned Users: <b>{stats['banned_users']}</b>\n"
            f"💳 Pending Payments: <b>{stats['pending_payments']}</b>\n\n"
            f"🕐 {_now_ist_str()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <b>CYBER WILD WAVE</b>"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                       reply_markup=back_admin_keyboard())

    elif data == "adm_users":
        stats = await db.get_stats()
        users = await db.get_all_users()
        sample = "\n".join(
            f"  • {u['first_name']} (ID: <code>{u['user_id']}</code>)" for u in users[:10]
        )
        text = (
            f"👥 <b>USERS SUMMARY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Total: <b>{stats['total_users']}</b>\n"
            f"Premium: <b>{stats['premium_users']}</b>\n"
            f"Banned: <b>{stats['banned_users']}</b>\n\n"
            f"<b>Recent Users:</b>\n{sample or 'None'}\n\n"
            f"🕐 {_now_ist_str()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <b>CYBER WILD WAVE</b>"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                       reply_markup=back_admin_keyboard())

    elif data == "adm_prem_list":
        plist = await db.get_premium_users_list()
        if not plist:
            text = "📋 <b>Premium Users</b>\n\nNo active premium users.\n\n🔥 <b>CYBER WILD WAVE</b>"
        else:
            lines = ["📋 <b>PREMIUM USERS LIST</b>\n"]
            for u in plist:
                name = u["first_name"] or "Unknown"
                exp  = u["expires_at"][:10] if u["expires_at"] else "—"
                lines.append(f"• <b>{name}</b> — <code>{u['user_id']}</code> — Expires: {exp}")
            lines.append("\n🔥 <b>CYBER WILD WAVE</b>")
            text = "\n".join(lines)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                       reply_markup=back_admin_keyboard())

    elif data == "adm_grant":
        set_pending_action(query.from_user.id, "admin_grant")
        await query.edit_message_text(
            "💎 <b>GRANT PREMIUM</b>\n\nSend in format:\n<code>USER_ID DAYS</code>\n\nExample:\n<code>123456789 30</code>",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_revoke":
        set_pending_action(query.from_user.id, "admin_revoke")
        await query.edit_message_text(
            "🚫 <b>REVOKE PREMIUM</b>\n\nSend the <b>User ID</b> to revoke premium:",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_ban":
        set_pending_action(query.from_user.id, "admin_ban")
        await query.edit_message_text(
            "🔐 <b>BAN USER</b>\n\nSend:\n<code>USER_ID reason</code>",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_unban":
        set_pending_action(query.from_user.id, "admin_unban")
        await query.edit_message_text(
            "✅ <b>UNBAN USER</b>\n\nSend the <b>User ID</b> to unban:",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_del_user":
        set_pending_action(query.from_user.id, "admin_del_user")
        await query.edit_message_text(
            "❌ <b>REMOVE USER</b>\n\nSend the <b>User ID</b> to delete from database:",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_broadcast":
        set_pending_action(query.from_user.id, "admin_broadcast")
        await query.edit_message_text(
            "📢 <b>BROADCAST</b>\n\nSend the message to broadcast to all users.\nYou can send text, photo, or video.",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_export":
        users = await db.get_all_users()
        lines = ["USER_ID | USERNAME | NAME | JOINED | PREMIUM | SEARCHES"]
        for u in users:
            prem = await db.is_premium(u["user_id"])
            lines.append(
                f"{u['user_id']} | @{u['username'] or 'N/A'} | {u['first_name'] or ''} | "
                f"{u['joined_at'][:10]} | {'YES' if prem else 'NO'} | {u['total_searches']}"
            )
        tmp = "/tmp/users_export.txt"
        with open(tmp, "w") as f:
            f.write("\n".join(lines))
        await ctx.bot.send_document(
            chat_id=query.from_user.id,
            document=open(tmp, "rb"),
            filename="users_export.txt",
            caption="📂 <b>Users Export</b>\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML
        )
        os.remove(tmp)
        await query.answer("✅ Export sent!", show_alert=True)

    elif data in ("adm_logs", "adm_refresh_logs"):
        logs = await db.get_search_logs(limit=10)
        await query.edit_message_text(
            _build_logs_text(logs), parse_mode=ParseMode.HTML,
            reply_markup=logs_keyboard()
        )

    elif data == "adm_clear_logs":
        await query.edit_message_text(
            "🗑 <b>CLEAR SEARCH LOGS</b>\n\n⚠️ This will delete all search history. Are you sure?",
            parse_mode=ParseMode.HTML,
            reply_markup=confirm_keyboard("adm_confirm_clear_logs", "adm_logs")
        )

    elif data == "adm_confirm_clear_logs":
        await db.clear_search_logs()
        await db.log_admin_action(query.from_user.id, "search logs cleared")
        logs = await db.get_search_logs(limit=10)
        await query.edit_message_text(
            _build_logs_text(logs), parse_mode=ParseMode.HTML,
            reply_markup=logs_keyboard()
        )

    elif data == "adm_export_logs":
        logs = await db.export_search_logs()
        if not logs:
            await query.answer("No logs to export.", show_alert=True)
            return
        lines = ["ID | USER_ID | NAME | SEARCH TYPE | QUERY | RESULT | DATE (IST) | TIME (IST)"]
        for row in logs:
            emoji, label = SEARCH_TYPE_LABELS.get(row["search_type"], ("🔍", row["search_type"]))
            date_s, time_s = _fmt_ist(row["created_at"])
            result = "FOUND" if row["result_found"] else "NOT FOUND"
            lines.append(
                f"{row['id']} | {row['user_id']} | {row['full_name']} | "
                f"{label} | {row['query']} | {result} | {date_s} | {time_s}"
            )
        tmp = "/tmp/search_logs_export.txt"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        await ctx.bot.send_document(
            chat_id=query.from_user.id,
            document=open(tmp, "rb"),
            filename="search_logs.txt",
            caption="📥 <b>Search Logs Export</b>\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML
        )
        os.remove(tmp)
        await query.answer("✅ Logs exported!", show_alert=True)

    elif data == "adm_freeze":
        info   = await db.get_freeze_info()
        frozen = info["frozen"]
        status = "⏸ <b>FROZEN</b>" if frozen else "▶ <b>RUNNING</b>"
        if frozen and info["frozen_secs"]:
            status += f"\n⏱ Frozen for: <b>{_fmt_duration(info['frozen_secs'])}</b>"
        text = (
            f"⏸ <b>PREMIUM FREEZE CONTROL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Status: {status}\n\n"
            f"<i>Freeze pauses the premium countdown for all users.</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <b>CYBER WILD WAVE</b>"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                       reply_markup=freeze_keyboard(frozen))

    elif data == "adm_freeze_on":
        await db.freeze_premium_start()
        await db.log_admin_action(query.from_user.id, "manually froze premium timers")
        await query.answer("⏸ Premium timers frozen!", show_alert=True)
        await query.edit_message_text(
            f"⏸ <b>PREMIUM FREEZE CONTROL</b>\n\nStatus: ⏸ <b>FROZEN</b>\n\n"
            f"<i>All premium timers are now paused.</i>\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML, reply_markup=freeze_keyboard(True)
        )

    elif data == "adm_freeze_off":
        info        = await db.get_freeze_info()
        frozen_secs = info["frozen_secs"]
        await db.freeze_premium_end()
        await db.log_admin_action(query.from_user.id, f"resumed premium timers (compensated {frozen_secs}s)")
        comp = _fmt_duration(frozen_secs)
        await query.answer(f"▶ Resumed! Compensated {comp}", show_alert=True)
        await query.edit_message_text(
            f"▶ <b>PREMIUM FREEZE CONTROL</b>\n\nStatus: ▶ <b>RUNNING</b>\n"
            f"✅ Compensated: <b>{comp}</b> added to all active users.\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML, reply_markup=freeze_keyboard(False)
        )

    elif data == "adm_prem_report":
        report = await db.get_premium_time_report()
        info   = await db.get_freeze_info()
        freeze_line = "⏸ <b>FROZEN</b>" if info["frozen"] else "▶ Running"
        if not report:
            text = (
                f"📊 <b>PREMIUM TIME REPORT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Timer: {freeze_line}\n"
                f"🕐 {_now_ist_str()}\n\n"
                f"<i>No active premium users.</i>\n\n🔥 <b>CYBER WILD WAVE</b>"
            )
        else:
            lines = [
                "📊 <b>PREMIUM TIME REPORT</b>",
                "━━━━━━━━━━━━━━━━━━━━━━",
                f"Timer: {freeze_line}",
                f"Active: <b>{len(report)}</b>  🕐 {_now_ist_str()}",
                "━━━━━━━━━━━━━━━━━━━━━━", "",
            ]
            for u in report:
                name     = u["full_name"] or "Unknown"
                rem      = _fmt_duration(u["seconds_remaining"])
                exp_date = u["expires_at"][:10] if u["expires_at"] else "—"
                plan     = PREMIUM_PLANS.get(u["plan_key"], {}).get("label", u["plan_key"] or "Manual")
                lines += [f"👤 <b>{name}</b>",
                          f"🆔 <code>{u['user_id']}</code>  📦 {plan}",
                          f"⏳ {rem}  📅 {exp_date}", ""]
            lines.append("🔥 <b>CYBER WILD WAVE</b>")
            text = "\n".join(lines)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                       reply_markup=back_admin_keyboard())

    elif data == "adm_payments":
        pending = await db.get_pending_transactions()
        if not pending:
            await query.edit_message_text(
                "💳 <b>Pending Payments</b>\n\nNo pending payments.\n\n🔥 <b>CYBER WILD WAVE</b>",
                parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
            )
        else:
            from keyboards.admin_kb import payment_review_keyboard
            for txn in pending:
                plan = PREMIUM_PLANS.get(txn["plan_key"], {})
                cap  = (
                    f"💳 <b>Pending Payment</b>\n"
                    f"ID: #{txn['id']} | User: <code>{txn['user_id']}</code>\n"
                    f"Plan: {plan.get('label','N/A')} — ₹{txn['amount']}\n"
                    f"Date: {txn['created_at'][:10]}\n🔥 <b>CYBER WILD WAVE</b>"
                )
                try:
                    await ctx.bot.send_photo(
                        chat_id=query.from_user.id, photo=txn["screenshot_file_id"],
                        caption=cap, parse_mode=ParseMode.HTML,
                        reply_markup=payment_review_keyboard(txn["id"])
                    )
                except Exception:
                    await ctx.bot.send_message(
                        chat_id=query.from_user.id, text=cap, parse_mode=ParseMode.HTML,
                        reply_markup=payment_review_keyboard(txn["id"])
                    )
            await query.answer(f"Sent {len(pending)} pending payment(s).", show_alert=True)

    elif data == "adm_genkey":
        set_pending_action(query.from_user.id, "admin_genkey")
        plan_list = "\n".join(f"  • <code>{k}</code>" for k in PREMIUM_PLANS.keys())
        await query.edit_message_text(
            f"🔑 <b>GENERATE KEY</b>\n\nSend plan key:\n{plan_list}",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_clear_db":
        await query.edit_message_text(
            "🧹 <b>CLEAR DATABASE</b>\n\n⚠️ This will delete ALL data. Are you sure?",
            parse_mode=ParseMode.HTML,
            reply_markup=confirm_keyboard("adm_confirm_clear", "adm_back")
        )

    elif data == "adm_confirm_clear":
        await db.clear_database()
        await db.log_admin_action(query.from_user.id, "database cleared")
        await query.edit_message_text(
            "✅ <b>Database Cleared</b>\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML, reply_markup=back_admin_keyboard()
        )

    elif data == "adm_server":
        await _show_server_status(query, ctx)


async def _show_server_status(query_or_msg, ctx, is_message: bool = False):
    try:
        if HAS_PSUTIL:
            import psutil as _ps
            cpu  = _ps.cpu_percent(interval=0.5)
            mem  = _ps.virtual_memory()
            disk = _ps.disk_usage("/")
            cpu_line  = f"💻 CPU: <b>{cpu}%</b>"
            ram_line  = f"🧠 RAM: <b>{mem.percent}%</b> ({mem.used//1024//1024}MB / {mem.total//1024//1024}MB)"
            disk_line = f"💾 Disk: <b>{disk.percent}%</b> ({disk.used//1024//1024//1024}GB / {disk.total//1024//1024//1024}GB)"
        else:
            cpu_line = ram_line = disk_line = "<i>psutil not available</i>"

        frozen = await db.is_premium_frozen()
        freeze_status = "⏸ Frozen" if frozen else "▶ Running"
        text = (
            f"⚡ <b>SERVER STATUS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🖥 OS: <b>{platform.system()} {platform.release()}</b>\n"
            f"🐍 Python: <b>{platform.python_version()}</b>\n"
            f"🤖 Bot: <b>v{BOT_VERSION}</b>\n\n"
            f"{cpu_line}\n{ram_line}\n{disk_line}\n\n"
            f"⏸ Premium Timer: <b>{freeze_status}</b>\n"
            f"📅 Date & Time: <b>{_now_ist_str()}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <b>CYBER WILD WAVE</b>"
        )
    except Exception:
        text = "⚡ <b>SERVER STATUS</b>\n\nCould not retrieve server stats.\n\n🔥 <b>CYBER WILD WAVE</b>"

    if is_message:
        await query_or_msg.reply_text(text, parse_mode=ParseMode.HTML,
                                       reply_markup=back_admin_keyboard())
    else:
        await query_or_msg.edit_message_text(text, parse_mode=ParseMode.HTML,
                                              reply_markup=back_admin_keyboard())


# ── ReplyKeyboard handler — admin buttons ──────────────────────────────────────

async def handle_admin_panel_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle admin ReplyKeyboard button taps. Sends clean responses, no duplicate menus."""
    user = update.effective_user
    text = (update.message.text or "").strip()

    if text == "🔙 Back":
        # Return to main keyboard (clean user+admin panel button only)
        await update.message.reply_text(
            "🏠 <b>Main Menu</b>\n\n📲 Use the buttons below ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_main_keyboard()
        )
        return

    if text == "👑 Admin Panel":
        # Open the admin submenu keyboard
        stats = await db.get_stats()
        maint = "🔴 ON" if cfg.MAINTENANCE_MODE else "🟢 OFF"
        await update.message.reply_text(
            f"👑 <b>CYBER WILD WAVE — ADMIN PANEL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Admin: <b>{user.first_name}</b>\n"
            f"🤖 Bot: <b>v{BOT_VERSION}</b>\n"
            f"🛠 Maintenance: <b>{maint}</b>\n\n"
            f"👥 Users: <b>{stats['total_users']}</b>  "
            f"💎 Premium: <b>{stats['premium_users']}</b>  "
            f"🔍 Searches: <b>{stats['total_searches']}</b>\n\n"
            f"🕐 {_now_ist_str()}\n\n"
            f"Select an option below ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard()
        )
        return

    if text == "🛠 Bot Control":
        maint = "🔴 ON" if cfg.MAINTENANCE_MODE else "🟢 OFF"
        await update.message.reply_text(
            f"🛠 <b>BOT CONTROL</b>\n\n"
            f"Maintenance: <b>{maint}</b>\n"
            f"🕐 {_now_ist_str()}\n\n"
            f"🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=bot_control_keyboard()
        )

    elif text == "💎 Grant Premium":
        set_pending_action(user.id, "admin_grant")
        await update.message.reply_text(
            "💎 <b>GRANT PREMIUM</b>\n\nSend in format:\n<code>USER_ID DAYS</code>\n\nExample:\n<code>123456789 30</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "🚫 Revoke Premium":
        set_pending_action(user.id, "admin_revoke")
        await update.message.reply_text(
            "🚫 <b>REVOKE PREMIUM</b>\n\nSend the <b>User ID</b> to revoke premium:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "❌ Remove User":
        set_pending_action(user.id, "admin_del_user")
        await update.message.reply_text(
            "❌ <b>REMOVE USER</b>\n\nSend the <b>User ID</b> to delete from database:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "👥 Users Summary":
        stats = await db.get_stats()
        users = await db.get_all_users()
        sample = "\n".join(
            f"  • {u['first_name']} (<code>{u['user_id']}</code>)" for u in users[:10]
        )
        await update.message.reply_text(
            f"👥 <b>USERS SUMMARY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Total: <b>{stats['total_users']}</b>\n"
            f"Premium: <b>{stats['premium_users']}</b>\n"
            f"Banned: <b>{stats['banned_users']}</b>\n\n"
            f"<b>Recent Users:</b>\n{sample or 'None'}\n\n"
            f"🕐 {_now_ist_str()}\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "📊 Live Statistics":
        stats = await db.get_stats()
        await update.message.reply_text(
            f"📊 <b>LIVE STATISTICS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total Users: <b>{stats['total_users']}</b>\n"
            f"💎 Premium Users: <b>{stats['premium_users']}</b>\n"
            f"🔍 Today's Searches: <b>{stats['today_searches']}</b>\n"
            f"📊 Total Searches: <b>{stats['total_searches']}</b>\n"
            f"🟢 Active Today: <b>{stats['active_today']}</b>\n"
            f"🚫 Banned Users: <b>{stats['banned_users']}</b>\n"
            f"💳 Pending Payments: <b>{stats['pending_payments']}</b>\n\n"
            f"🕐 {_now_ist_str()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "📢 Broadcast":
        set_pending_action(user.id, "admin_broadcast")
        await update.message.reply_text(
            "📢 <b>BROADCAST</b>\n\nSend the message to broadcast to all users.\nYou can send text, photo, or video.",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "📋 Premium Users":
        plist = await db.get_premium_users_list()
        if not plist:
            text_out = "📋 <b>Premium Users</b>\n\nNo active premium users.\n\n🔥 <b>CYBER WILD WAVE</b>"
        else:
            lines = ["📋 <b>PREMIUM USERS LIST</b>\n"]
            for u in plist:
                name = u["first_name"] or "Unknown"
                exp  = u["expires_at"][:10] if u["expires_at"] else "—"
                lines.append(f"• <b>{name}</b> — <code>{u['user_id']}</code> — Expires: {exp}")
            lines.append("\n🔥 <b>CYBER WILD WAVE</b>")
            text_out = "\n".join(lines)
        await update.message.reply_text(
            text_out, parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "🔄 Lifetime Update":
        report = await db.get_premium_time_report()
        info   = await db.get_freeze_info()
        freeze_line = "⏸ <b>FROZEN</b>" if info["frozen"] else "▶ Running"
        lines = [
            "📊 <b>PREMIUM TIME REPORT</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"Timer: {freeze_line}  Active: <b>{len(report)}</b>",
            f"🕐 {_now_ist_str()}",
            "━━━━━━━━━━━━━━━━━━━━━━", "",
        ]
        if report:
            for u in report:
                name     = u["full_name"] or "Unknown"
                rem      = _fmt_duration(u["seconds_remaining"])
                exp_date = u["expires_at"][:10] if u["expires_at"] else "—"
                plan     = PREMIUM_PLANS.get(u["plan_key"], {}).get("label", u["plan_key"] or "Manual")
                lines += [f"👤 <b>{name}</b>",
                          f"🆔 <code>{u['user_id']}</code>  📦 {plan}",
                          f"⏳ {rem}  📅 {exp_date}", ""]
        else:
            lines.append("<i>No active premium users.</i>")
        lines.append("🔥 <b>CYBER WILD WAVE</b>")
        await update.message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML,
            reply_markup=freeze_keyboard(info["frozen"])
        )

    elif text == "🧹 Clear Database":
        from keyboards.admin_kb import confirm_keyboard as ckb
        await update.message.reply_text(
            "🧹 <b>CLEAR DATABASE</b>\n\n⚠️ This will delete ALL data. Are you sure?\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=ckb("adm_confirm_clear", "adm_close")
        )

    elif text == "🔐 Ban User":
        set_pending_action(user.id, "admin_ban")
        await update.message.reply_text(
            "🔐 <b>BAN USER</b>\n\nSend:\n<code>USER_ID reason</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "✅ Unban User":
        set_pending_action(user.id, "admin_unban")
        await update.message.reply_text(
            "✅ <b>UNBAN USER</b>\n\nSend the <b>User ID</b> to unban:",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif text == "⚡ Server Status":
        await _show_server_status(update.message, ctx, is_message=True)

    elif text == "📂 Export Users":
        users = await db.get_all_users()
        lines = ["USER_ID | USERNAME | NAME | JOINED | PREMIUM | SEARCHES"]
        for u in users:
            prem = await db.is_premium(u["user_id"])
            lines.append(
                f"{u['user_id']} | @{u['username'] or 'N/A'} | {u['first_name'] or ''} | "
                f"{u['joined_at'][:10]} | {'YES' if prem else 'NO'} | {u['total_searches']}"
            )
        tmp = "/tmp/users_export.txt"
        with open(tmp, "w") as f:
            f.write("\n".join(lines))
        await ctx.bot.send_document(
            chat_id=user.id, document=open(tmp, "rb"),
            filename="users_export.txt",
            caption="📂 <b>Users Export</b>\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML
        )
        os.remove(tmp)

    elif text == "📝 Logs":
        logs = await db.get_search_logs(limit=10)
        await update.message.reply_text(
            _build_logs_text(logs), parse_mode=ParseMode.HTML,
            reply_markup=logs_keyboard()
        )


# ── Text input handler (admin pending actions) ────────────────────────────────

async def handle_admin_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return

    action = get_pending_action(user.id)
    if not action or not action.startswith("admin_"):
        return

    text = (update.message.text or "").strip()
    clear_pending_action(user.id)

    if action == "admin_grant":
        parts = text.split()
        if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
            await update.message.reply_text(
                "❌ Invalid format. Use: <code>USER_ID DAYS</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=admin_submenu_keyboard(),
            )
            return
        uid, days = int(parts[0]), int(parts[1])
        await db.grant_premium(uid, days, user.id, "manual")
        await db.log_admin_action(user.id, f"granted premium to {uid} for {days} days")
        await update.message.reply_text(
            f"✅ Premium granted to <code>{uid}</code> for <b>{days} days</b>.\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )
        try:
            await ctx.bot.send_message(
                uid,
                f"🎉 Admin has granted you <b>{days} days</b> of Premium access!\n"
                f"💎 Enjoy VIP benefits!\n\n🔥 <b>CYBER WILD WAVE</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    elif action == "admin_revoke":
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Invalid User ID. Send a numeric ID.",
                reply_markup=admin_submenu_keyboard(),
            )
            return
        uid = int(text)
        await db.revoke_premium(uid)
        await db.log_admin_action(user.id, f"revoked premium from {uid}")
        await update.message.reply_text(
            f"✅ Premium revoked for <code>{uid}</code>.\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif action == "admin_ban":
        parts = text.split(maxsplit=1)
        if not parts or not parts[0].isdigit():
            await update.message.reply_text(
                "❌ Invalid format. Use: <code>USER_ID reason</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=admin_submenu_keyboard(),
            )
            return
        uid    = int(parts[0])
        reason = parts[1] if len(parts) > 1 else "No reason given"
        await db.ban_user(uid, reason, user.id)
        await db.log_admin_action(user.id, f"banned user {uid}: {reason}")
        await update.message.reply_text(
            f"🔐 User <code>{uid}</code> banned.\nReason: {reason}\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif action == "admin_unban":
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Invalid User ID. Send a numeric ID.",
                reply_markup=admin_submenu_keyboard(),
            )
            return
        uid = int(text)
        await db.unban_user(uid)
        await db.log_admin_action(user.id, f"unbanned user {uid}")
        await update.message.reply_text(
            f"✅ User <code>{uid}</code> unbanned.\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif action == "admin_del_user":
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Invalid User ID. Send a numeric ID.",
                reply_markup=admin_submenu_keyboard(),
            )
            return
        uid = int(text)
        await db.delete_user(uid)
        await db.log_admin_action(user.id, f"deleted user {uid}")
        await update.message.reply_text(
            f"✅ User <code>{uid}</code> removed from database.\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )

    elif action == "admin_broadcast":
        users    = await db.get_all_users()
        sent, failed = 0, 0
        for u in users:
            try:
                if update.message.photo:
                    await ctx.bot.send_photo(
                        u["user_id"], update.message.photo[-1].file_id,
                        caption=update.message.caption or ""
                    )
                elif update.message.video:
                    await ctx.bot.send_video(
                        u["user_id"], update.message.video.file_id,
                        caption=update.message.caption or ""
                    )
                else:
                    await ctx.bot.send_message(
                        u["user_id"], update.message.text or "", parse_mode=ParseMode.HTML
                    )
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"📢 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )
        await db.log_admin_action(user.id, f"broadcast sent to {sent} users")

    elif action == "admin_genkey":
        plan_key = text.strip()
        if plan_key not in PREMIUM_PLANS:
            await update.message.reply_text(
                "❌ Invalid plan key. Check the list and try again.",
                reply_markup=admin_submenu_keyboard(),
            )
            return
        import secrets
        key_code = secrets.token_urlsafe(12).upper()
        await db.create_key(key_code, plan_key)
        await db.log_admin_action(user.id, f"generated key {key_code} for {plan_key}")
        plan = PREMIUM_PLANS[plan_key]
        await update.message.reply_text(
            f"🔑 <b>Key Generated</b>\n\nCode: <code>{key_code}</code>\nPlan: <b>{plan['label']}</b>\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_submenu_keyboard(),
        )


# ── /apistatus — admin-only live API diagnostics ──────────────────────────────

async def apistatus_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Admin-only command: live-tests every configured API endpoint and reports
    which variables are set, which are missing, and whether each URL responds.
    Usage: /apistatus
    """
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        return

    from services.api_service import test_api_connection

    endpoints = [
        ("📱 Number",   cfg.API_NUMBER_LOOKUP,   "9999999999"),
        ("📞 Telegram", cfg.API_TELEGRAM_LOOKUP,  "test"),
        ("🪪 Aadhaar",  cfg.API_AADHAAR_LOOKUP,   "999999999999"),
        ("👨‍👩‍👧‍👦 Family",  cfg.API_FAMILY_LOOKUP,   "test"),
        ("📍 Pincode",  cfg.API_PINCODE_LOOKUP,   "110001"),
        ("🏦 IFSC",     cfg.API_IFSC_LOOKUP,      "SBIN0001234"),
        ("🚗 Vehicle",  cfg.API_VEHICLE_LOOKUP,   "DL1CAB1234"),
    ]

    lines = [
        "<b>🔧 API Status Report</b>",
        f"API_KEY set: {'✅ Yes' if cfg.API_KEY else '❌ No'}",
        "",
    ]

    for label, url_template, test_val in endpoints:
        if not url_template:
            lines.append(f"{label}: ❌ <i>Not configured (env var missing)</i>")
        else:
            import re as _re
            masked = _re.sub(
                r'(key=|apikey=|api_key=|token=)[^&\s]+',
                r'\1***', url_template, flags=_re.IGNORECASE
            )
            ok, msg = await test_api_connection(url_template, test_val)
            icon = "✅" if ok else "❌"
            lines.append(f"{label}: {icon}")
            lines.append(f"  <code>{masked[:90]}</code>")
            lines.append(f"  <i>{msg[:90]}</i>")
        lines.append("")

    await update.message.reply_text(
        "\n".join(lines) + "🔥 <b>CYBER WILD WAVE</b>",
        parse_mode=ParseMode.HTML,
    )
