import asyncio
import logging
import time
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from utils.logger import setup_logging
setup_logging()

import database as db
from config import BOT_TOKEN, BOT_NAME, BOT_VERSION
from keyboards.main_kb import admin_main_keyboard, user_panel_keyboard
from handlers.start import (
    start_handler, disclaimer_callback, verify_join_callback,
    menu_back_callback, help_callback, credits_callback,
    handle_user_panel_button, USER_PANEL_BUTTONS,
)
from handlers.search import (
    search_menu_callback, search_type_callback,
    handle_search_text, handle_search_kb_button, SEARCH_KB_BUTTONS,
)
from handlers.premium import (
    premium_menu_callback, premium_status_callback, premium_expiry_callback,
    buy_premium_callback, buy_plan_selected_callback, paid_callback,
    redeem_key_callback, handle_key_redeem_text
)
from handlers.account import account_callback
from handlers.admin import (
    admin_command, admin_callback, handle_admin_text,
    handle_admin_panel_button, ADMIN_PANEL_BUTTONS, ADMIN_SUBMENU_BUTTONS, is_admin,
    apistatus_command,
)
from handlers.payment import handle_screenshot, admin_approve_payment, admin_reject_payment
from utils.rate_limiter import get_pending_action
from utils.msg_tracker import track

logger = logging.getLogger(__name__)


async def _handle_back(update: Update, ctx):
    """
    🔙 Back — returns user to their main keyboard.
    Called from both search submenu and admin submenu.
    """
    user = update.effective_user
    kb   = admin_main_keyboard() if is_admin(user.id) else user_panel_keyboard()
    ctx.user_data["_kbd_mode"] = "main"
    sent = await update.message.reply_text(
        "🏠 <b>Main Menu</b>\n\n📲 Use the buttons below ↓",
        parse_mode="HTML",
        reply_markup=kb
    )
    track(ctx, sent)


async def handle_all_text(update: Update, ctx):
    user = update.effective_user
    if not user:
        return

    text = (update.message.text or "").strip()

    # ── 1. Universal "🔙 Back" — works from any submenu ────────────────────────
    if text == "🔙 BACK":
        await _handle_back(update, ctx)
        return

    # ── 2. Admin entry-point and submenu buttons ──────────────────────────────
    if is_admin(user.id) and text == "👑 ADMIN PANEL":
        ctx.user_data["_kbd_mode"] = "admin"
        await handle_admin_panel_button(update, ctx)
        return

    if is_admin(user.id) and text in ADMIN_SUBMENU_BUTTONS:
        await handle_admin_panel_button(update, ctx)
        return

    # ── 3. Search submenu keyboard buttons ────────────────────────────────────
    if text in SEARCH_KB_BUTTONS:
        await handle_search_kb_button(update, ctx)
        return

    # ── 4. Main user-panel buttons ────────────────────────────────────────────
    if text in USER_PANEL_BUTTONS:
        await handle_user_panel_button(update, ctx)
        return

    # ── 5. Pending text input (search query / key / admin action) ─────────────
    action = get_pending_action(user.id)
    if not action:
        return

    if action.startswith("search_"):
        await handle_search_text(update, ctx)
    elif action == "redeem_key":
        await handle_key_redeem_text(update, ctx)
    elif action.startswith("admin_"):
        await handle_admin_text(update, ctx)


async def handle_all_photos(update: Update, ctx):
    user = update.effective_user
    if not user:
        return
    action = get_pending_action(user.id)
    if action and action.startswith("screenshot_"):
        await handle_screenshot(update, ctx)
    elif action and action.startswith("admin_broadcast"):
        await handle_admin_text(update, ctx)


async def _heartbeat_loop():
    while True:
        await asyncio.sleep(30)
        await db.set_setting("last_heartbeat", str(int(time.time())))


async def post_init(app):
    try:
        await db.init_db()

        from services.api_service import get_session, log_api_config
        log_api_config()
        await get_session()

        last_hb = await db.get_setting("last_heartbeat")
        if last_hb:
            gap = int(time.time()) - int(last_hb)
            if gap > 120:
                await db.extend_all_premium(gap)
                logger.info("⏸ Freeze recovery: extended all premiums by %ds (%.1f min offline)",
                            gap, gap / 60)

        await db.set_setting("last_heartbeat", str(int(time.time())))
        asyncio.create_task(_heartbeat_loop())
        logger.info("✅ %s v%s started", BOT_NAME, BOT_VERSION)
    except Exception as exc:
        logger.critical("💥 post_init FAILED — bot cannot start: %s", exc, exc_info=True)
        raise

async def post_shutdown(app):
    from services.api_service import close_session
    await close_session()
    logger.info("🛑 %s shutdown complete", BOT_NAME)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set in environment variables.")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("apistatus", apistatus_command))

    # Disclaimer / channel gate
    app.add_handler(CallbackQueryHandler(disclaimer_callback,  pattern="^disclaimer_"))
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^verify_join$"))

    # Main menu inline navigation
    app.add_handler(CallbackQueryHandler(menu_back_callback,   pattern="^menu_back$"))
    app.add_handler(CallbackQueryHandler(help_callback,        pattern="^menu_help$"))
    app.add_handler(CallbackQueryHandler(credits_callback,     pattern="^menu_credits$"))
    app.add_handler(CallbackQueryHandler(menu_back_callback,   pattern="^menu_refresh$"))
    app.add_handler(CallbackQueryHandler(account_callback,     pattern="^menu_account$"))

    # Search flow (inline legacy + keyboard-based)
    app.add_handler(CallbackQueryHandler(search_menu_callback,  pattern="^menu_search$"))
    app.add_handler(CallbackQueryHandler(search_type_callback,
                    pattern="^search_(number|telegram|aadhaar|family|pincode|ifsc|vehicle)$"))

    # Premium flow
    app.add_handler(CallbackQueryHandler(premium_menu_callback,      pattern="^menu_premium$"))
    app.add_handler(CallbackQueryHandler(premium_status_callback,    pattern="^prem_status$"))
    app.add_handler(CallbackQueryHandler(premium_expiry_callback,    pattern="^prem_expiry$"))
    app.add_handler(CallbackQueryHandler(buy_premium_callback,       pattern="^prem_buy$"))
    app.add_handler(CallbackQueryHandler(buy_plan_selected_callback, pattern="^buyplan_"))
    app.add_handler(CallbackQueryHandler(paid_callback,              pattern="^paid_"))
    app.add_handler(CallbackQueryHandler(redeem_key_callback,        pattern="^prem_redeem$"))

    # Payment approvals
    app.add_handler(CallbackQueryHandler(admin_approve_payment, pattern="^adm_pay_ok_"))
    app.add_handler(CallbackQueryHandler(admin_reject_payment,  pattern="^adm_pay_no_"))

    # All other admin inline callbacks
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm_"))

    # Text and photo
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_all_photos))

    logger.info("🤖 Starting %s v%s...", BOT_NAME, BOT_VERSION)
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
