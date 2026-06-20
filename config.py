import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK", "https://t.me/yourchannel")

FREE_DAILY_SEARCHES = int(os.getenv("FREE_DAILY_SEARCHES", "5"))
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "3"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

# ── API endpoint URL templates ─────────────────────────────────────────────────
# Each URL must contain a placeholder for the search term.
# Supported placeholders: {query} {num} {mobile} {number} {q} and lookup-specific ones.
# Example: https://api.example.com/number?num={query}&key=abc123
#
# API_NUMBER_LOOKUP   — mobile number lookup
# API_TELEGRAM_LOOKUP — Telegram username/ID lookup
# API_AADHAAR_LOOKUP  — Aadhaar number lookup
# API_FAMILY_LOOKUP   — family/household lookup
# API_PINCODE_LOOKUP  — PIN code (auto-falls back to postalpincode.in if blank)
# API_IFSC_LOOKUP     — IFSC code (auto-falls back to razorpay if blank)
# API_VEHICLE_LOOKUP  — vehicle registration lookup
# API_KEY             — shared key sent as Authorization: Bearer and X-Api-Key headers
API_NUMBER_LOOKUP   = os.getenv("API_NUMBER_LOOKUP", "")
API_TELEGRAM_LOOKUP = os.getenv("API_TELEGRAM_LOOKUP", "")
API_AADHAAR_LOOKUP  = os.getenv("API_AADHAAR_LOOKUP", "")
API_FAMILY_LOOKUP   = os.getenv("API_FAMILY_LOOKUP", "")
API_PINCODE_LOOKUP  = os.getenv("API_PINCODE_LOOKUP", "")
API_IFSC_LOOKUP     = os.getenv("API_IFSC_LOOKUP", "")
API_VEHICLE_LOOKUP  = os.getenv("API_VEHICLE_LOOKUP", "")
API_KEY             = os.getenv("API_KEY", "")

PREMIUM_PLANS = {
    "1day":    {"label": "1 Day",     "price": 49,   "days": 1},
    "3days":   {"label": "3 Days",    "price": 99,   "days": 3},
    "7days":   {"label": "7 Days",    "price": 149,  "days": 7},
    "15days":  {"label": "15 Days",   "price": 199,  "days": 15},
    "1month":  {"label": "1 Month",   "price": 299,  "days": 30},
    "2months": {"label": "2 Months",  "price": 449,  "days": 60},
    "3months": {"label": "3 Months",  "price": 599,  "days": 90},
    "6months": {"label": "6 Months",  "price": 799,  "days": 180},
    "1year":   {"label": "1 Year",    "price": 1199, "days": 365},
}

BOT_VERSION = "2.1.0"
BOT_NAME = "CYBER WILD WAVE"

MAINTENANCE_MODE = False
