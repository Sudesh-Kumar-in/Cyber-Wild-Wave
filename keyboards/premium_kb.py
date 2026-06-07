from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PREMIUM_PLANS


def premium_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ Premium Status", callback_data="prem_status"),
            InlineKeyboardButton("💳 Buy Premium",    callback_data="prem_buy"),
        ],
        [
            InlineKeyboardButton("🎟 Redeem Key",     callback_data="prem_redeem"),
            InlineKeyboardButton("📅 Expiry Date",    callback_data="prem_expiry"),
        ],
        [InlineKeyboardButton("🔙 Back",              callback_data="menu_back")],
    ])


def buy_plans_keyboard() -> InlineKeyboardMarkup:
    rows = []
    keys = list(PREMIUM_PLANS.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            p = PREMIUM_PLANS[k]
            row.append(InlineKeyboardButton(
                f"{p['label']} — ₹{p['price']}",
                callback_data=f"buyplan_{k}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu_premium")])
    return InlineKeyboardMarkup(rows)


def payment_confirm_keyboard(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I've Paid — Send Screenshot", callback_data=f"paid_{plan_key}")],
        [InlineKeyboardButton("🔙 Back to Plans", callback_data="prem_buy")],
    ])
