from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)


# ── Permanent admin bottom navigation (ReplyKeyboard) ─────────────────────────

def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛠 Bot Control"),    KeyboardButton("💎 Grant Premium")],
            [KeyboardButton("🚫 Revoke Premium"), KeyboardButton("❌ Remove User")],
            [KeyboardButton("👥 Users Summary"),  KeyboardButton("📊 Live Statistics")],
            [KeyboardButton("📢 Broadcast"),       KeyboardButton("📋 Premium Users")],
            [KeyboardButton("🔄 Lifetime Update"), KeyboardButton("🧹 Clear Database")],
            [KeyboardButton("🔐 Ban User"),        KeyboardButton("✅ Unban User")],
            [KeyboardButton("⚡ Server Status"),   KeyboardButton("📂 Export Users")],
            [KeyboardButton("📝 Logs"),            KeyboardButton("🔙 User Panel")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ── Inline keyboards (submenus & actions) ─────────────────────────────────────

def bot_control_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶ Start Bot",    callback_data="adm_ctrl_start"),
            InlineKeyboardButton("⏹ Stop Bot",     callback_data="adm_ctrl_stop"),
        ],
        [
            InlineKeyboardButton("🔄 Restart Bot", callback_data="adm_ctrl_restart"),
            InlineKeyboardButton("🛠 Maintenance", callback_data="adm_ctrl_maint"),
        ],
        [InlineKeyboardButton("🔙 Back",           callback_data="adm_back")],
    ])


def logs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑 Clear Logs",   callback_data="adm_clear_logs"),
            InlineKeyboardButton("📥 Export Logs",  callback_data="adm_export_logs"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Logs", callback_data="adm_refresh_logs"),
            InlineKeyboardButton("🔙 Back",         callback_data="adm_back"),
        ],
    ])


def freeze_keyboard(is_frozen: bool) -> InlineKeyboardMarkup:
    if is_frozen:
        toggle = InlineKeyboardButton("▶ Resume Premium Timer", callback_data="adm_freeze_off")
    else:
        toggle = InlineKeyboardButton("⏸ Freeze Premium Timer", callback_data="adm_freeze_on")
    return InlineKeyboardMarkup([
        [toggle],
        [InlineKeyboardButton("📊 Premium Time Report", callback_data="adm_prem_report")],
        [InlineKeyboardButton("🔙 Back",                callback_data="adm_back")],
    ])


def confirm_keyboard(yes_cb: str, no_cb: str = "adm_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=yes_cb),
            InlineKeyboardButton("❌ Cancel",  callback_data=no_cb),
        ]
    ])


def payment_review_keyboard(txn_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"adm_pay_ok_{txn_id}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"adm_pay_no_{txn_id}"),
        ]
    ])


def back_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_back")]
    ])
