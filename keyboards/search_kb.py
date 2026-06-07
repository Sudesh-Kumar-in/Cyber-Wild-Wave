from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def search_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 Number Lookup",   callback_data="search_number"),
            InlineKeyboardButton("📞 Telegram Lookup", callback_data="search_telegram"),
        ],
        [
            InlineKeyboardButton("🪪 Aadhaar Lookup",  callback_data="search_aadhaar"),
            InlineKeyboardButton("👨‍👩‍👧‍👦 Family Lookup", callback_data="search_family"),
        ],
        [
            InlineKeyboardButton("📍 Pincode Lookup",  callback_data="search_pincode"),
            InlineKeyboardButton("🏦 IFSC Lookup",     callback_data="search_ifsc"),
        ],
        [
            InlineKeyboardButton("🚗 Vehicle Lookup",  callback_data="search_vehicle"),
        ],
        [
            InlineKeyboardButton("🔙 Back",            callback_data="menu_back"),
        ],
    ])


def back_to_search_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 New Search", callback_data="menu_search"),
            InlineKeyboardButton("🏠 Main Menu",  callback_data="menu_back"),
        ]
    ])
