from telegram import (
      InlineKeyboardButton, InlineKeyboardMarkup,
      ReplyKeyboardMarkup, KeyboardButton,
  )


  # ── User panel (regular users) ─────────────────────────────────────────────────

  def user_panel_keyboard() -> ReplyKeyboardMarkup:
      return ReplyKeyboardMarkup(
          [
              [KeyboardButton("🔍 SEARCH"),         KeyboardButton("💎 PREMIUM")],
              [KeyboardButton("👤 MY ACCOUNT"),     KeyboardButton("📜 REMAINING CREDIT")],
              [KeyboardButton("ℹ️ HELP"),            KeyboardButton("🔄 REFRESH")],
          ],
          resize_keyboard=True,
          is_persistent=True,
      )


  # ── Admin main keyboard (clean panel + single admin entry point) ───────────────

  def admin_main_keyboard() -> ReplyKeyboardMarkup:
      return ReplyKeyboardMarkup(
          [
              [KeyboardButton("🔍 SEARCH"),         KeyboardButton("💎 PREMIUM")],
              [KeyboardButton("👤 MY ACCOUNT"),     KeyboardButton("📜 REMAINING CREDIT")],
              [KeyboardButton("ℹ️ HELP"),            KeyboardButton("🔄 REFRESH")],
              [KeyboardButton("👑 ADMIN PANEL")],
          ],
          resize_keyboard=True,
          is_persistent=True,
      )


  # ── Admin submenu keyboard (appears after clicking 👑 ADMIN PANEL) ─────────────

  def admin_submenu_keyboard() -> ReplyKeyboardMarkup:
      return ReplyKeyboardMarkup(
          [
              [KeyboardButton("🛠 BOT CONTROL"),      KeyboardButton("💎 GRANT PREMIUM")],
              [KeyboardButton("🚫 REVOKE PREMIUM"),   KeyboardButton("❌ REMOVE USER")],
              [KeyboardButton("👥 USERS SUMMARY"),    KeyboardButton("📊 LIVE STATISTICS")],
              [KeyboardButton("📢 BROADCAST"),         KeyboardButton("📋 PREMIUM USERS")],
              [KeyboardButton("🔄 LIFETIME UPDATE"),  KeyboardButton("🧹 CLEAR DATABASE")],
              [KeyboardButton("🔐 BAN USER"),          KeyboardButton("✅ UNBAN USER")],
              [KeyboardButton("⚡ SERVER STATUS"),     KeyboardButton("📂 EXPORT USERS")],
              [KeyboardButton("📝 LOGS"),              KeyboardButton("🔙 BACK")],
          ],
          resize_keyboard=True,
          is_persistent=True,
      )


  # ── Search submenu keyboard (replaces keyboard when user taps 🔍 SEARCH) ────────

  def search_submenu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
      base_kb = admin_main_keyboard() if is_admin else user_panel_keyboard()
      _ = base_kb   # used only for the back button target
      return ReplyKeyboardMarkup(
          [
              [KeyboardButton("📱 NUMBER LOOKUP"),   KeyboardButton("📞 TELEGRAM LOOKUP")],
              [KeyboardButton("🪪 AADHAAR LOOKUP"),  KeyboardButton("👨‍👩‍👧‍👦 FAMILY LOOKUP")],
              [KeyboardButton("📍 PINCODE LOOKUP"),  KeyboardButton("🏦 IFSC LOOKUP")],
              [KeyboardButton("🚗 VEHICLE LOOKUP"),  KeyboardButton("🔙 BACK")],
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
              InlineKeyboardButton("✅ I AGREE", callback_data="disclaimer_agree"),
              InlineKeyboardButton("❌ EXIT",    callback_data="disclaimer_exit"),
          ]
      ])


  def join_channel_keyboard(invite_link: str) -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [InlineKeyboardButton("📢 JOIN CHANNEL", url=invite_link)],
          [InlineKeyboardButton("✅ I'VE JOINED — VERIFY", callback_data="verify_join")],
      ])


  def home_inline_keyboard() -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [InlineKeyboardButton("🔙 BACK", callback_data="menu_back")]
      ])


  def main_menu_keyboard() -> InlineKeyboardMarkup:
      return home_inline_keyboard()
  