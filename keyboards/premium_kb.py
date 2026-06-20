from telegram import InlineKeyboardButton, InlineKeyboardMarkup
  from config import PREMIUM_PLANS


  def premium_menu_keyboard() -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [
              InlineKeyboardButton("⭐ PREMIUM STATUS", callback_data="prem_status"),
              InlineKeyboardButton("💳 BUY PREMIUM",    callback_data="prem_buy"),
          ],
          [
              InlineKeyboardButton("🎟 REDEEM KEY",     callback_data="prem_redeem"),
              InlineKeyboardButton("📅 EXPIRY DATE",    callback_data="prem_expiry"),
          ],
          [InlineKeyboardButton("🔙 BACK",              callback_data="menu_back")],
      ])


  def buy_plans_keyboard() -> InlineKeyboardMarkup:
      rows = []
      keys = list(PREMIUM_PLANS.keys())
      for i in range(0, len(keys), 2):
          row = []
          for k in keys[i:i+2]:
              p = PREMIUM_PLANS[k]
              row.append(InlineKeyboardButton(
                  f"{p['label'].upper()} — ₹{p['price']}",
                  callback_data=f"buyplan_{k}"
              ))
          rows.append(row)
      rows.append([InlineKeyboardButton("🔙 BACK", callback_data="menu_premium")])
      return InlineKeyboardMarkup(rows)


  def payment_confirm_keyboard(plan_key: str) -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [InlineKeyboardButton("✅ I'VE PAID — SEND SCREENSHOT", callback_data=f"paid_{plan_key}")],
          [InlineKeyboardButton("🔙 BACK TO PLANS", callback_data="prem_buy")],
      ])
  