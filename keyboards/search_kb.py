from telegram import InlineKeyboardButton, InlineKeyboardMarkup


  def search_menu_keyboard() -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [
              InlineKeyboardButton("📱 NUMBER LOOKUP",   callback_data="search_number"),
              InlineKeyboardButton("📞 TELEGRAM LOOKUP", callback_data="search_telegram"),
          ],
          [
              InlineKeyboardButton("🪪 AADHAAR LOOKUP",  callback_data="search_aadhaar"),
              InlineKeyboardButton("👨‍👩‍👧‍👦 FAMILY LOOKUP", callback_data="search_family"),
          ],
          [
              InlineKeyboardButton("📍 PINCODE LOOKUP",  callback_data="search_pincode"),
              InlineKeyboardButton("🏦 IFSC LOOKUP",     callback_data="search_ifsc"),
          ],
          [
              InlineKeyboardButton("🚗 VEHICLE LOOKUP",  callback_data="search_vehicle"),
          ],
          [
              InlineKeyboardButton("🔙 BACK",            callback_data="menu_back"),
          ],
      ])


  def back_to_search_keyboard() -> InlineKeyboardMarkup:
      return InlineKeyboardMarkup([
          [
              InlineKeyboardButton("🔍 NEW SEARCH", callback_data="menu_search"),
              InlineKeyboardButton("🏠 MAIN MENU",  callback_data="menu_back"),
          ]
      ])
  