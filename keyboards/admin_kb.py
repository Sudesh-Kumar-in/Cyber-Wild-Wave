from telegram import (
      InlineKeyboardButton, InlineKeyboardMarkup,
      ReplyKeyboardMarkup, KeyboardButton,
  )


  # ── Permanent admin bottom navigation (ReplyKeyboard) ─────────────────────────

  def admin_panel_keyboard() -> ReplyKeyboardMarkup:
      return ReplyKeyboardMarkup(
          [
              [KeyboardButton("🛠 BOT CONTROL"),    KeyboardButton("💎 GRANT PREMIUM")],
              [KeyboardButton("🚫 REVOKE PREMIUM"), KeyboardButton("❌ REMOVE USER")],
              [KeyboardButton("👥 USERS SUMMARY"),  KeyboardButton("📊 LIVE STATISTICS")],
              [KeyboardButton("📢 BROADCAST"),       KeyboardButton("📋 PREMIUM USERS")],
              [KeyboardButton("🔄 LIFETIME UPDATE"), KeyboardButton("🧹 CLEAR DATABASE")],
              [KeyboardButton("🔐 BAN USER"),        KeyboardButton("✅ UNBAN USER")],
              [KeyboardButton("⚡ SERVER STATUS"),   KeyboardButton("📂 EXPORT USERS")],
              [KeyboardButton("📝 LOGS"),            KeyboardButton("🔙 USER PANEL")],
          ],
          resize_keyboard=True,
          is_persistent=True,
      )


  # ── Inline keyboards (submenus & actions) ─────────────────────────────────────

  def bot_control_keyboard() -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [
              InlineKeyboardButton("▶ START BOT",    callback_data="adm_ctrl_start"),
              InlineKeyboardButton("⏹ STOP BOT",     callback_data="adm_ctrl_stop"),
          ],
          [
              InlineKeyboardButton("🔄 RESTART BOT", callback_data="adm_ctrl_restart"),
              InlineKeyboardButton("🛠 MAINTENANCE", callback_data="adm_ctrl_maint"),
          ],
          [InlineKeyboardButton("🔙 BACK",           callback_data="adm_back")],
      ])


  def logs_keyboard() -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [
              InlineKeyboardButton("🗑 CLEAR LOGS",   callback_data="adm_clear_logs"),
              InlineKeyboardButton("📥 EXPORT LOGS",  callback_data="adm_export_logs"),
          ],
          [
              InlineKeyboardButton("🔄 REFRESH LOGS", callback_data="adm_refresh_logs"),
              InlineKeyboardButton("🔙 BACK",         callback_data="adm_back"),
          ],
      ])


  def freeze_keyboard(is_frozen: bool) -> InlineKeyboardMarkup:
      if is_frozen:
          toggle = InlineKeyboardButton("▶ RESUME PREMIUM TIMER", callback_data="adm_freeze_off")
      else:
          toggle = InlineKeyboardButton("⏸ FREEZE PREMIUM TIMER", callback_data="adm_freeze_on")
      return InlineKeyboardMarkup([
          [toggle],
          [InlineKeyboardButton("📊 PREMIUM TIME REPORT", callback_data="adm_prem_report")],
          [InlineKeyboardButton("🔙 BACK",                callback_data="adm_back")],
      ])


  def confirm_keyboard(yes_cb: str, no_cb: str = "adm_back") -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [
              InlineKeyboardButton("✅ CONFIRM", callback_data=yes_cb),
              InlineKeyboardButton("❌ CANCEL",  callback_data=no_cb),
          ]
      ])


  def payment_review_keyboard(txn_id: int) -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [
              InlineKeyboardButton("✅ APPROVE", callback_data=f"adm_pay_ok_{txn_id}"),
              InlineKeyboardButton("❌ REJECT",  callback_data=f"adm_pay_no_{txn_id}"),
          ]
      ])


  def back_admin_keyboard() -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [InlineKeyboardButton("🔙 BACK TO ADMIN", callback_data="adm_back")]
      ])
  