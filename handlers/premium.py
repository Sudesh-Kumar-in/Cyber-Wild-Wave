import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards.premium_kb import premium_menu_keyboard, buy_plans_keyboard, payment_confirm_keyboard
from keyboards.main_kb import user_panel_keyboard
from utils.rate_limiter import set_pending_action, get_pending_action, clear_pending_action
from config import PREMIUM_PLANS, BOT_NAME

logger = logging.getLogger(__name__)

PREMIUM_MENU_TEXT = """
💎 <b>PREMIUM MENU</b>
━━━━━━━━━━━━━━━━━━━━━━

✅ <b>Premium Benefits:</b>
  • ⚡ Faster responses
  • 🔓 Unlimited searches
  • 🌟 Premium APIs access
  • 👑 VIP Badge
  • 🎯 Priority access
  • 📊 Advanced analytics

🔥 <b>CYBER WILD WAVE</b> — Upgrade now ↓
""".strip()

BUY_PLANS_TEXT = """
🔰 <b>PREMIUM MEMBERSHIP PLANS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

• 1 Day      — ₹49
• 3 Days     — ₹99
• 7 Days     — ₹149
• 15 Days    — ₹199
• 1 Month    — ₹299
• 2 Months   — ₹449
• 3 Months   — ₹599
• 6 Months   — ₹799
• 1 Year     — ₹1199

━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 <b>CYBER WILD WAVE</b>

Select a plan to continue:
""".strip()

PAYMENT_INSTRUCTIONS = """
💳 <b>PAYMENT INSTRUCTIONS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>Plan:</b> {plan_label} — ₹{price}

━━━━━━━━━━━━━━━━━━━━━━━━━

💳 <b>HOW TO PAY:</b>
1️⃣ Scan the QR Code and pay ₹{price}
2️⃣ Take a <b>screenshot</b> of your payment
3️⃣ Click the button below and <b>send the screenshot</b>
4️⃣ Your payment will be verified and premium activated

━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Note:</b>
• Fake payments will be rejected.
• Send screenshot only ONCE.
• Activation within 1-2 hours after verification.

🔥 <b>CYBER WILD WAVE</b>
""".strip()


async def premium_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        PREMIUM_MENU_TEXT, parse_mode=ParseMode.HTML,
        reply_markup=premium_menu_keyboard()
    )


async def premium_status_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    premium = await db.is_premium(user.id)
    info = await db.get_premium_info(user.id)
    from utils.helpers import fmt_date

    if premium and info:
        text = (
            f"⭐ <b>PREMIUM STATUS</b>\n\n"
            f"✅ Status: <b>ACTIVE</b>\n"
            f"👑 Plan: <b>{info['plan_key'].upper()}</b>\n"
            f"📅 Activated: <b>{fmt_date(info['activated_at'])}</b>\n"
            f"⏳ Expires: <b>{fmt_date(info['expires_at'])}</b>\n\n"
            f"💎 You have full VIP access!\n\n"
            f"🔥 <b>CYBER WILD WAVE</b>"
        )
    else:
        text = (
            f"⭐ <b>PREMIUM STATUS</b>\n\n"
            f"❌ Status: <b>NOT ACTIVE</b>\n\n"
            f"💎 Upgrade now to unlock unlimited searches and VIP benefits!\n\n"
            f"🔥 <b>CYBER WILD WAVE</b>"
        )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                   reply_markup=premium_menu_keyboard())


async def premium_expiry_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    info = await db.get_premium_info(user.id)
    from utils.helpers import fmt_date
    from datetime import datetime

    if info and info["expires_at"]:
        expires = datetime.strptime(info["expires_at"][:19], "%Y-%m-%d %H:%M:%S")
        now = datetime.utcnow()
        remaining = (expires - now).days
        if remaining >= 0:
            text = (
                f"📅 <b>EXPIRY DATE</b>\n\n"
                f"⏳ Expires On: <b>{fmt_date(info['expires_at'])}</b>\n"
                f"📆 Days Remaining: <b>{remaining} day(s)</b>\n\n"
                f"✅ Your premium is active!\n\n"
                f"🔥 <b>CYBER WILD WAVE</b>"
            )
        else:
            text = (
                f"📅 <b>EXPIRY DATE</b>\n\n"
                f"❌ Your premium has <b>expired</b>.\n\n"
                f"Upgrade to continue enjoying benefits!\n\n"
                f"🔥 <b>CYBER WILD WAVE</b>"
            )
    else:
        text = (
            f"📅 <b>EXPIRY DATE</b>\n\n"
            f"❌ You are not a premium member.\n\n"
            f"🔥 <b>CYBER WILD WAVE</b>"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                   reply_markup=premium_menu_keyboard())


async def buy_premium_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        BUY_PLANS_TEXT, parse_mode=ParseMode.HTML,
        reply_markup=buy_plans_keyboard()
    )


async def buy_plan_selected_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("buyplan_", "")
    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        await query.answer("❌ Invalid plan.", show_alert=True)
        return

    ctx.user_data["pending_plan"] = plan_key
    text = PAYMENT_INSTRUCTIONS.format(plan_label=plan["label"], price=plan["price"])

    import os
    qr_path = "payment_qr/qr.jpg"
    if os.path.exists(qr_path):
        await query.message.reply_photo(
            photo=open(qr_path, "rb"),
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=payment_confirm_keyboard(plan_key)
        )
        try:
            await query.delete_message()
        except Exception:
            pass
    else:
        await query.edit_message_text(
            text + "\n\n📌 <i>QR Code not configured. Contact admin for payment details.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=payment_confirm_keyboard(plan_key)
        )


async def paid_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("paid_", "")
    plan = PREMIUM_PLANS.get(plan_key)
    if not plan:
        await query.answer("❌ Invalid plan.", show_alert=True)
        return

    set_pending_action(query.from_user.id, f"screenshot_{plan_key}")

    await query.message.reply_text(
        f"📸 <b>Send Payment Screenshot</b>\n\n"
        f"Please send a <b>clear screenshot</b> of your payment for:\n"
        f"📌 Plan: <b>{plan['label']}</b> — ₹{plan['price']}\n\n"
        f"<i>Send the screenshot as a photo message now.</i>\n\n"
        f"🔥 <b>CYBER WILD WAVE</b>",
        parse_mode=ParseMode.HTML,
    )


async def redeem_key_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    set_pending_action(query.from_user.id, "redeem_key")
    await query.edit_message_text(
        "🎟 <b>REDEEM KEY</b>\n\n"
        "Enter your activation key code below:\n\n"
        "<i>Send the key as a text message.</i>\n\n"
        "🔥 <b>CYBER WILD WAVE</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=premium_menu_keyboard()
    )


async def handle_key_redeem_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    action = get_pending_action(user.id)
    if action != "redeem_key":
        return

    key_code = (update.message.text or "").strip()
    if not key_code:
        return

    clear_pending_action(user.id)

    # Delete user's key message (sensitive)
    try:
        await update.message.delete()
    except Exception:
        pass

    from config import ADMIN_IDS
    from keyboards.main_kb import admin_main_keyboard
    kb = admin_main_keyboard() if user.id in ADMIN_IDS else user_panel_keyboard()

    row = await db.redeem_key(key_code, user.id)

    if not row:
        await update.effective_chat.send_message(
            "❌ <b>Invalid or Already Used Key</b>\n\n"
            "This key is invalid or has already been redeemed.\n\n"
            "🔥 <b>CYBER WILD WAVE</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return

    plan = PREMIUM_PLANS.get(row["plan_key"])
    days = plan["days"] if plan else 30
    label = plan["label"] if plan else "30 Days"
    await db.grant_premium(user.id, days, 0, row["plan_key"])

    await update.effective_chat.send_message(
        f"✅ <b>Key Redeemed Successfully!</b>\n\n"
        f"🎉 <b>Premium Activated!</b>\n"
        f"📅 Plan: <b>{label}</b>\n"
        f"💎 Enjoy unlimited searches and VIP access!\n\n"
        f"🔥 <b>CYBER WILD WAVE</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
