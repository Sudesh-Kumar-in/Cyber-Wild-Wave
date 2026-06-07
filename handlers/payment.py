import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards.admin_kb import payment_review_keyboard
from utils.rate_limiter import get_pending_action, clear_pending_action
from config import ADMIN_IDS, PREMIUM_PLANS

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = "assets/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


async def handle_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    action = get_pending_action(user.id)
    if not action or not action.startswith("screenshot_"):
        return

    plan_key = action.replace("screenshot_", "")
    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        return

    if not update.message.photo:
        await update.message.reply_text(
            "📸 Please send a <b>photo</b> of your payment screenshot.",
            parse_mode=ParseMode.HTML,
        )
        return

    clear_pending_action(user.id)

    photo = update.message.photo[-1]
    file_id = photo.file_id

    txn_id = await db.create_transaction(user.id, plan_key, plan["price"], file_id)

    await update.message.reply_text(
        f"✅ <b>Screenshot Received!</b>\n\n"
        f"📌 Transaction ID: <code>#{txn_id}</code>\n"
        f"💳 Plan: <b>{plan['label']}</b> — ₹{plan['price']}\n"
        f"⏳ Status: <b>Pending Verification</b>\n\n"
        f"Our team will verify your payment and activate premium within 1-2 hours.\n"
        f"<i>Thank you for your patience!</i>\n\n"
        f"🔥 <b>CYBER WILD WAVE</b>",
        parse_mode=ParseMode.HTML,
    )

    from utils.helpers import get_user_display_name
    name = get_user_display_name(user)
    username = f"@{user.username}" if user.username else "N/A"

    notify_text = (
        f"💳 <b>NEW PAYMENT REQUEST</b>\n\n"
        f"👤 User: <b>{name}</b>\n"
        f"📛 Username: {username}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"📌 Plan: <b>{plan['label']}</b> — ₹{plan['price']}\n"
        f"🔢 Transaction: <code>#{txn_id}</code>\n\n"
        f"🔥 <b>CYBER WILD WAVE</b>"
    )

    for admin_id in ADMIN_IDS:
        try:
            await ctx.bot.send_photo(
                chat_id=admin_id, photo=file_id,
                caption=notify_text, parse_mode=ParseMode.HTML,
                reply_markup=payment_review_keyboard(txn_id)
            )
        except Exception as e:
            logger.warning("Could not notify admin %s: %s", admin_id, e)


async def admin_approve_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized", show_alert=True)
        return

    txn_id = int(query.data.replace("adm_pay_ok_", ""))
    await db.update_transaction_status(txn_id, "approved", query.from_user.id)

    import aiosqlite
    import config as cfg
    async with aiosqlite.connect(cfg.DATABASE_PATH) as dbc:
        dbc.row_factory = aiosqlite.Row
        async with dbc.execute("SELECT * FROM transactions WHERE id=?", (txn_id,)) as cur:
            txn = await cur.fetchone()

    if txn:
        plan = PREMIUM_PLANS.get(txn["plan_key"])
        days = plan["days"] if plan else 30
        label = plan["label"] if plan else "Premium"
        await db.grant_premium(txn["user_id"], days, query.from_user.id, txn["plan_key"])

        try:
            await ctx.bot.send_message(
                chat_id=txn["user_id"],
                text=(
                    f"✅ <b>Payment Approved!</b>\n\n"
                    f"🎉 Your premium has been activated!\n"
                    f"📅 Plan: <b>{label}</b>\n"
                    f"💎 Enjoy unlimited searches and VIP access!\n\n"
                    f"🔥 <b>CYBER WILD WAVE</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.warning("Could not notify user %s: %s", txn["user_id"], e)

    try:
        await query.edit_message_caption(
            caption=(query.message.caption or "") + "\n\n✅ <b>APPROVED</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass


async def admin_reject_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized", show_alert=True)
        return

    txn_id = int(query.data.replace("adm_pay_no_", ""))
    await db.update_transaction_status(txn_id, "rejected", query.from_user.id)

    import aiosqlite
    import config as cfg
    async with aiosqlite.connect(cfg.DATABASE_PATH) as dbc:
        dbc.row_factory = aiosqlite.Row
        async with dbc.execute("SELECT * FROM transactions WHERE id=?", (txn_id,)) as cur:
            txn = await cur.fetchone()

    if txn:
        try:
            await ctx.bot.send_message(
                chat_id=txn["user_id"],
                text=(
                    f"❌ <b>Payment Rejected</b>\n\n"
                    f"Your payment screenshot could not be verified.\n\n"
                    f"If you believe this is an error, please contact admin.\n\n"
                    f"🔥 <b>CYBER WILD WAVE</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.warning("Could not notify user %s: %s", txn["user_id"], e)

    try:
        await query.edit_message_caption(
            caption=(query.message.caption or "") + "\n\n❌ <b>REJECTED</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass
