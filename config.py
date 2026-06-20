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

# ── API Key ────────────────────────────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "")

# ── Legacy API_URL support ─────────────────────────────────────────────────────
# Railway was configured with API_URL (base URL) + API_KEY as separate variables.
# We auto-construct the full numbered lookup URL from them so Railway needs no changes.
_API_URL_BASE = os.getenv("API_URL", "").rstrip("/")

def _build_from_base(path_and_params: str) -> str:
    """Return full URL from API_URL base + path, or empty string if base not set."""
    if not _API_URL_BASE:
        return ""
    return f"{_API_URL_BASE}{path_and_params}"

# ── API endpoint URL templates ─────────────────────────────────────────────────
# Priority: explicit API_*_LOOKUP var → auto-built from API_URL → empty (no lookup)
# Placeholders in URLs: {query} {num} {mobile} {number} {q} all work interchangeably.
#
# The paid-flix API uses: ?num={query}&key=YOUR_KEY
# So if API_URL = https://paid-flix-num-info-api.alphamovies.workers.dev/
# and API_KEY  = yash_special_key
# → API_NUMBER_LOOKUP becomes:
#   https://paid-flix-num-info-api.alphamovies.workers.dev/?num={query}&key=yash_special_key

API_NUMBER_LOOKUP = (
    os.getenv("API_NUMBER_LOOKUP", "")
    or _build_from_base(f"?num={{query}}&key={API_KEY}")
)
API_TELEGRAM_LOOKUP = (
    os.getenv("API_TELEGRAM_LOOKUP", "")
    or _build_from_base(f"?telegram={{query}}&key={API_KEY}")
)
API_AADHAAR_LOOKUP = (
    os.getenv("API_AADHAAR_LOOKUP", "")
    or _build_from_base(f"?aadhaar={{query}}&key={API_KEY}")
)
API_FAMILY_LOOKUP = (
    os.getenv("API_FAMILY_LOOKUP", "")
    or _build_from_base(f"?family={{query}}&key={API_KEY}")
)
API_PINCODE_LOOKUP = (
    os.getenv("API_PINCODE_LOOKUP", "")
    # pincode has a free public fallback — don't guess base URL params for it
)
API_IFSC_LOOKUP = (
    os.getenv("API_IFSC_LOOKUP", "")
    # IFSC has a free public fallback — don't guess base URL params for it
)
API_VEHICLE_LOOKUP = (
    os.getenv("API_VEHICLE_LOOKUP", "")
    or _build_from_base(f"?vehicle={{query}}&key={API_KEY}")
)

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

BOT_VERSION = "2.1.1"
BOT_NAME = "CYBER WILD WAVE"

MAINTENANCE_MODE = False
