import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards.main_kb import (
    user_panel_keyboard, admin_main_keyboard, search_submenu_keyboard
)
from keyboards.search_kb import back_to_search_keyboard
from services import api_service
from utils.rate_limiter import check_rate_limit, set_pending_action, get_pending_action, clear_pending_action
from utils.msg_tracker import track, cleanup_all
from utils.formatters import (
    format_number_lookup, format_telegram_lookup, format_aadhaar_lookup,
    format_family_lookup, format_pincode_lookup, format_ifsc_lookup,
    format_vehicle_lookup,
)
from config import FREE_DAILY_SEARCHES, ADMIN_IDS
import config as cfg

logger = logging.getLogger(__name__)


def _get_main_kb(user_id: int):
    """Return the correct persistent main keyboard for this user."""
    return admin_main_keyboard() if user_id in ADMIN_IDS else user_panel_keyboard()


# ── Keyboard-button → action mapping ─────────────────────────────────────────

SEARCH_KB_MAP = {
    "📱 NUMBER LOOKUP":   "search_number",
    "📞 TELEGRAM LOOKUP": "search_telegram",
    "🪪 AADHAAR LOOKUP":  "search_aadhaar",
    "👨‍👩‍👧‍👦 FAMILY LOOKUP":  "search_family",
    "📍 PINCODE LOOKUP":  "search_pincode",
    "🏦 IFSC LOOKUP":     "search_ifsc",
    "🚗 VEHICLE LOOKUP":  "search_vehicle",
}

SEARCH_KB_BUTTONS = set(SEARCH_KB_MAP.keys())

SEARCH_PROMPTS = {
    "search_number":   ("📱", "Number Lookup",   "Enter the <b>10-digit mobile number</b>"),
    "search_telegram": ("📞", "Telegram Lookup", "Enter the <b>Telegram username</b> (without @) or user ID"),
    "search_aadhaar":  ("🪪", "Aadhaar Lookup",  "Enter the <b>12-digit Aadhaar number</b>"),
    "search_family":   ("👨‍👩‍👧‍👦", "Family Lookup",  "Enter <b>Aadhaar number or full name</b> to find family data"),
    "search_pincode":  ("📍", "Pincode Lookup",  "Enter the <b>6-digit Pincode</b>"),
    "search_ifsc":     ("🏦", "IFSC Lookup",     "Enter the <b>IFSC Code</b> (e.g. SBIN0001234)"),
    "search_vehicle":  ("🚗", "Vehicle Lookup",  "Enter the <b>Vehicle Registration Number</b> (e.g. MH12AB1234)"),
}

FORMATTERS = {
    "search_number":   format_number_lookup,
    "search_telegram": format_telegram_lookup,
    "search_aadhaar":  format_aadhaar_lookup,
    "search_family":   format_family_lookup,
    "search_pincode":  format_pincode_lookup,
    "search_ifsc":     format_ifsc_lookup,
    "search_vehicle":  format_vehicle_lookup,
}

API_FUNCS = {
    "search_number":   api_service.lookup_number,
    "search_telegram": api_service.lookup_telegram,
    "search_aadhaar":  api_service.lookup_aadhaar,
    "search_family":   api_service.lookup_family,
    "search_pincode":  api_service.lookup_pincode,
    "search_ifsc":     api_service.lookup_ifsc,
    "search_vehicle":  api_service.lookup_vehicle,
}


async def _safe_delete(bot, chat_id: int, msg_id: int):
    if not msg_id:
        return
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


# ── Keyboard-based search type selection ─────────────────────────────────────

async def handle_search_kb_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Called when user taps a search-type button from the search submenu keyboard.
    Swaps keyboard back to main, sends a clean prompt, tracks it, sets pending action.
    """
    user   = update.effective_user
    text   = (update.message.text or "").strip()
    action = SEARCH_KB_MAP.get(text)
    if not action:
        return

    kb = _get_main_kb(user.id)

    if not check_rate_limit(user.id):
        sent = await update.message.reply_text(
            "⏳ <b>Slow down!</b>\n\nPlease wait a moment before searching again.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        track(ctx, sent)
        return

    if cfg.MAINTENANCE_MODE and user.id not in ADMIN_IDS:
        sent = await update.message.reply_text(
            "🛠 <b>Maintenance Mode</b>\n\nThe bot is under maintenance. Please try again later.\n\n🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        track(ctx, sent)
        return

    banned, premium = await asyncio.gather(
        db.is_banned(user.id),
        db.is_premium(user.id),
    )

    if banned:
        sent = await update.message.reply_text(
            "🚫 <b>Banned</b>\n\nYou are banned from using this bot.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        track(ctx, sent)
        return

    if not premium:
        used = await db.get_daily_search_count(user.id)
        if used >= FREE_DAILY_SEARCHES:
            sent = await update.message.reply_text(
                f"❌ <b>Daily Limit Reached</b>\n\n"
                f"You've used all <b>{FREE_DAILY_SEARCHES}</b> free searches today.\n\n"
                f"💎 Upgrade to <b>Premium</b> for unlimited searches!\n\n"
                f"🔥 <b>CYBER WILD WAVE</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            track(ctx, sent)
            ctx.user_data["_kbd_mode"] = "main"
            return

    emoji, label, prompt = SEARCH_PROMPTS[action]
    set_pending_action(user.id, action)

    sent = await update.message.reply_text(
        f"╔══════════════════════════╗\n"
        f"║  {emoji}  {label.upper():<18} ║\n"
        f"╚══════════════════════════╝\n\n"
        f"{prompt}:\n\n"
        f"<i>Type and send below ↓</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    track(ctx, sent)
    ctx.user_data["_kbd_mode"] = "main"
    ctx.user_data["_prompt_id"] = sent.message_id


# ── Legacy inline search callbacks (kept for back-compat) ────────────────────

async def search_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔍 <b>SEARCH MENU</b>\n\nSelect the type of lookup:",
        parse_mode=ParseMode.HTML,
        reply_markup=back_to_search_keyboard()
    )


async def search_type_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Legacy inline callback — maps to keyboard handler."""
    query  = update.callback_query
    await query.answer()
    action = query.data

    if action not in SEARCH_PROMPTS:
        return

    user = update.effective_user

    banned, premium = await asyncio.gather(
        db.is_banned(user.id),
        db.is_premium(user.id),
    )
    if banned:
        await query.answer("🚫 You are banned.", show_alert=True)
        return
    if not premium:
        used = await db.get_daily_search_count(user.id)
        if used >= FREE_DAILY_SEARCHES:
            await query.edit_message_text(
                f"❌ <b>Daily Limit Reached</b>\n\n"
                f"You've used all <b>{FREE_DAILY_SEARCHES}</b> free searches today.\n\n"
                f"💎 Upgrade to <b>Premium</b> for unlimited searches!\n\n"
                f"🔥 <b>CYBER WILD WAVE</b>",
                parse_mode=ParseMode.HTML,
            )
            return

    emoji, label, prompt = SEARCH_PROMPTS[action]
    set_pending_action(user.id, action)

    await query.edit_message_text(
        f"{emoji} <b>{label.upper()}</b>\n\n{prompt}:\n\n"
        f"<i>Type your query and send it below ↓</i>",
        parse_mode=ParseMode.HTML,
    )
    ctx.user_data["_prompt_id"] = query.message.message_id


# ── Main search text handler ──────────────────────────────────────────────────

async def handle_search_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Flow:
    1. Validate query
    2. Cleanup ALL previously tracked bot messages (welcome, menus, prompts, etc.)
    3. Send loading placeholder (no keyboard — temporary)
    4. Call API
    5. Send result WITH the correct persistent keyboard
    6. Delete loading
    Chat result: only user query + final result card remain visible.
    Keyboard: immediately restored after result.
    """
    user   = update.effective_user
    action = get_pending_action(user.id)
    if not action or action not in SEARCH_PROMPTS:
        return

    if await db.is_banned(user.id):
        return

    query_text = (update.message.text or "").strip()
    if not query_text:
        return

    clear_pending_action(user.id)

    chat_id = update.effective_chat.id
    kb      = _get_main_kb(user.id)

    # Step 1 — Delete all tracked bot messages (menus, prompts, welcome, etc.)
    await cleanup_all(ctx.bot, chat_id, ctx)

    # Step 2 — Loading placeholder (no keyboard while loading)
    loading = await update.effective_chat.send_message(
        "⏳ <b>Searching...</b>\n🔍 Fetching data, please wait...",
        parse_mode=ParseMode.HTML,
    )

    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or None

    try:
        api_fn = API_FUNCS[action]
        data   = await api_fn(query_text)
        found  = bool(data) if isinstance(data, list) else (data is not None)

        if found:
            result_text = FORMATTERS[action](data)
        else:
            result_text = (
                f"❌ <b>No Data Found</b>\n\n"
                f"No results for: <code>{query_text}</code>\n\n"
                f"Please verify your input and try again.\n\n"
                f"🔥 <b>CYBER WILD WAVE</b>"
            )

        # Step 3 — Send result WITH correct keyboard — keyboard restored here
        await update.effective_chat.send_message(
            result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

        await asyncio.gather(
            db.increment_daily_search(user.id),
            db.log_search(user.id, action, query_text, found,
                          username=user.username, full_name=full_name),
        )

    except Exception as exc:
        logger.exception("Search error [%s]: %s", action, exc)
        await update.effective_chat.send_message(
            "⚠️ <b>Error</b>\n\nAn error occurred. Please try again later.\n\n"
            "🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )

    finally:
        # Step 4 — Delete loading placeholder only
        await _safe_delete(ctx.bot, chat_id, loading.message_id)
