from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)


# ── User panel (regular users) ─────────────────────────────────────────────────

def user_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔍 Search"),         KeyboardButton("💎 Premium")],
            [KeyboardButton("👤 My Account"),     KeyboardButton("📜 Remaining Credit")],
            [KeyboardButton("ℹ️ Help"),            KeyboardButton("🔄 Refresh")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ── Admin main keyboard (clean panel + single admin entry point) ───────────────

def admin_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔍 Search"),         KeyboardButton("💎 Premium")],
            [KeyboardButton("👤 My Account"),     KeyboardButton("📜 Remaining Credit")],
            [KeyboardButton("ℹ️ Help"),            KeyboardButton("🔄 Refresh")],
            [KeyboardButton("👑 Admin Panel")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ── Admin submenu keyboard (appears after clicking 👑 Admin Panel) ─────────────

def admin_submenu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛠 Bot Control"),      KeyboardButton("💎 Grant Premium")],
            [KeyboardButton("🚫 Revoke Premium"),   KeyboardButton("❌ Remove User")],
            [KeyboardButton("👥 Users Summary"),    KeyboardButton("📊 Live Statistics")],
            [KeyboardButton("📢 Broadcast"),         KeyboardButton("📋 Premium Users")],
            [KeyboardButton("🔄 Lifetime Update"),  KeyboardButton("🧹 Clear Database")],
            [KeyboardButton("🔐 Ban User"),          KeyboardButton("✅ Unban User")],
            [KeyboardButton("⚡ Server Status"),     KeyboardButton("📂 Export Users")],
            [KeyboardButton("📝 Logs"),              KeyboardButton("🔙 Back")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ── Search submenu keyboard (replaces keyboard when user taps 🔍 Search) ────────

def search_submenu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    base_kb = admin_main_keyboard() if is_admin else user_panel_keyboard()
    _ = base_kb   # used only for the back button target
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📱 Number Lookup"),   KeyboardButton("📞 Telegram Lookup")],
            [KeyboardButton("🪪 Aadhaar Lookup"),  KeyboardButton("👨‍👩‍👧‍👦 Family Lookup")],
            [KeyboardButton("📍 Pincode Lookup"),  KeyboardButton("🏦 IFSC Lookup")],
            [KeyboardButton("🚗 Vehicle Lookup"),  KeyboardButton("🔙 Back")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ── Backward-compat alias ─────────────────────────────────────────────────────

def combined_keyboard() -> ReplyKeyboardMarkup:
    return admin_main_keyboard()


# ── Inline keyboards ──────────────────────────────────────────────────────────

def disclaimer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ I Agree", callback_data="disclaimer_agree"),
            InlineKeyboardButton("❌ Exit",    callback_data="disclaimer_exit"),
        ]
    ])


def join_channel_keyboard(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=invite_link)],
        [InlineKeyboardButton("✅ I've Joined — Verify", callback_data="verify_join")],
    ])


def home_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="menu_back")]
    ])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return home_inline_keyboard()
