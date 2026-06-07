"""
API service — uses a single persistent aiohttp session with connection
pooling so each lookup reuses existing TCP/TLS connections instead of
creating a new handshake per request.
"""
import aiohttp
import asyncio
import logging
from config import (
    API_NUMBER_LOOKUP, API_TELEGRAM_LOOKUP, API_AADHAAR_LOOKUP,
    API_FAMILY_LOOKUP, API_PINCODE_LOOKUP, API_IFSC_LOOKUP,
    API_VEHICLE_LOOKUP, API_KEY
)
from services import cache_service

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=12, connect=5)
_HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    _HEADERS["Authorization"] = f"Bearer {API_KEY}"

# ── Global persistent session (created lazily, reused across all requests) ────
_session: aiohttp.ClientSession | None = None
_session_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _session_lock
    if _session_lock is None:
        _session_lock = asyncio.Lock()
    return _session_lock


async def get_session() -> aiohttp.ClientSession:
    """Return the shared aiohttp session, creating it if needed."""
    global _session
    if _session is not None and not _session.closed:
        return _session
    async with _get_lock():
        if _session is None or _session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,               # max total open connections
                limit_per_host=20,       # max per host
                ttl_dns_cache=300,       # cache DNS 5 min
                enable_cleanup_closed=True,
                keepalive_timeout=30,
            )
            _session = aiohttp.ClientSession(
                timeout=TIMEOUT,
                headers=_HEADERS,
                connector=connector,
                connector_owner=True,
                raise_for_status=False,
            )
    return _session


async def close_session():
    """Gracefully close the shared session (call on bot shutdown)."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


# ── Core HTTP helper ──────────────────────────────────────────────────────────

async def _get(url: str) -> dict | list | None:
    """GET `url`, return parsed JSON or None on any error."""
    try:
        session = await get_session()
        async with session.get(url) as resp:
            if resp.status == 200:
                ct = resp.content_type or ""
                if "json" in ct or "javascript" in ct:
                    return await resp.json(content_type=None)
                text = await resp.text()
                import json
                return json.loads(text)
            logger.warning("API %s → HTTP %s", url, resp.status)
            return None
    except asyncio.TimeoutError:
        logger.error("API timeout: %s", url)
        return None
    except Exception as exc:
        logger.error("API error %s: %s", url, exc)
        return None


# ── Field normaliser for number/aadhaar/family records ───────────────────────

def _normalize_record(rec: dict) -> dict:
    def _pick(*keys):
        for k in keys:
            v = rec.get(k)
            if v not in (None, "", [], {}):
                return str(v).strip()
        return None

    return {
        "name":    _pick("name"),
        "father":  _pick("father_name", "father"),
        "mobile":  _pick("mobile", "phone", "number"),
        "alt":     _pick("alt", "alternate", "alt_mobile", "alt_number"),
        "aadhar":  _pick("id", "aadhar", "aadhaar", "uid", "aadhar_number"),
        "email":   _pick("email"),
        "circle":  _pick("circle", "operator", "telecom"),
        "address": _pick("address"),
    }


# ── Lookup functions ──────────────────────────────────────────────────────────

async def lookup_number(mobile: str) -> list[dict] | None:
    key = cache_service.cache_key("number", mobile)

    async def _fetch():
        if not API_NUMBER_LOOKUP:
            return None
        url = API_NUMBER_LOOKUP.replace("{query}", mobile).replace("{mobile}", mobile)
        raw = await _get(url)
        if not raw or not isinstance(raw, dict):
            return None
        status = str(raw.get("status", "")).lower()
        if status and status not in ("success", "ok", "true", "1", "200"):
            return None
        payload = raw.get("data") or raw.get("result") or raw.get("results") or raw.get("records")
        if isinstance(payload, dict):
            payload = [payload]
        elif not isinstance(payload, list):
            return None
        records = [_normalize_record(r) for r in payload if isinstance(r, dict)]
        records = [r for r in records if any(v for v in r.values())]
        return records or None

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_telegram(username_or_id: str) -> dict | None:
    key = cache_service.cache_key("telegram", username_or_id)

    async def _fetch():
        if not API_TELEGRAM_LOOKUP:
            return _demo_telegram(username_or_id)
        return await _get(API_TELEGRAM_LOOKUP.replace("{query}", username_or_id))

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_aadhaar(aadhaar: str) -> dict | None:
    key = cache_service.cache_key("aadhaar", aadhaar)

    async def _fetch():
        if not API_AADHAAR_LOOKUP:
            return _demo_aadhaar(aadhaar)
        return await _get(API_AADHAAR_LOOKUP.replace("{query}", aadhaar))

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_family(aadhaar_or_name: str) -> dict | None:
    key = cache_service.cache_key("family", aadhaar_or_name)

    async def _fetch():
        if not API_FAMILY_LOOKUP:
            return _demo_family(aadhaar_or_name)
        return await _get(API_FAMILY_LOOKUP.replace("{query}", aadhaar_or_name))

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_pincode(pincode: str) -> dict | None:
    key = cache_service.cache_key("pincode", pincode)

    async def _fetch():
        if API_PINCODE_LOOKUP:
            return await _get(API_PINCODE_LOOKUP.replace("{query}", pincode))
        raw = await _get(f"https://api.postalpincode.in/pincode/{pincode}")
        if raw and isinstance(raw, list) and raw[0].get("Status") == "Success":
            offices = raw[0].get("PostOffice") or []
            first = offices[0] if offices else {}
            return {
                "pincode":  pincode,
                "state":    first.get("State", ""),
                "district": first.get("District", ""),
                "region":   first.get("Region", ""),
                "division": first.get("Division", ""),
                "offices":  offices,
            }
        return None

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_ifsc(ifsc: str) -> dict | None:
    ifsc = ifsc.upper()
    key = cache_service.cache_key("ifsc", ifsc)

    async def _fetch():
        if API_IFSC_LOOKUP:
            return await _get(API_IFSC_LOOKUP.replace("{query}", ifsc))
        return await _get(f"https://ifsc.razorpay.com/{ifsc}")

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_vehicle(reg_no: str) -> dict | None:
    reg_no = reg_no.upper()
    key = cache_service.cache_key("vehicle", reg_no)

    async def _fetch():
        if not API_VEHICLE_LOOKUP:
            return _demo_vehicle(reg_no)
        return await _get(API_VEHICLE_LOOKUP.replace("{query}", reg_no))

    return await cache_service.get_or_fetch(key, _fetch())


# ── Demo data (when no API is configured) ────────────────────────────────────

def _demo_telegram(q: str) -> dict:
    return {"name": "Demo User", "user_id": "123456789", "username": q,
            "phone": None, "joined": None, "lang": "en", "bio": None, "_demo": True}


def _demo_aadhaar(q: str) -> dict:
    return {"name": "Demo User", "aadhaar": q, "mobile": None, "dob": None,
            "gender": None, "father": None, "address": None, "_demo": True}


def _demo_family(q: str) -> dict:
    return {"head": "Demo Head", "aadhaar": q, "address": None,
            "members": [{"name": "Demo Member 1", "relation": "Son", "dob": "01-01-2000"}],
            "_demo": True}


def _demo_vehicle(reg_no: str) -> dict:
    return {"reg_no": reg_no, "owner": "Demo Owner", "make": "Demo", "model": "Car",
            "color": "White", "fuel_type": "Petrol", "_demo": True}
