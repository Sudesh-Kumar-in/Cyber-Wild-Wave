"""
API service — uses a single persistent aiohttp session with connection
pooling so each lookup reuses existing TCP/TLS connections instead of
creating a new handshake per request.
"""
from __future__ import annotations

import aiohttp
import asyncio
import logging
import os
import re
from config import (
    API_NUMBER_LOOKUP, API_TELEGRAM_LOOKUP, API_AADHAAR_LOOKUP,
    API_FAMILY_LOOKUP, API_PINCODE_LOOKUP, API_IFSC_LOOKUP,
    API_VEHICLE_LOOKUP, API_KEY
)
from services import cache_service

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=15, connect=8)

# ── Global persistent session ─────────────────────────────────────────────────
_session: aiohttp.ClientSession | None = None
_session_lock: asyncio.Lock | None = None


def _substitute(url: str, value: str) -> str:
    """Replace any common query placeholder in a URL template with the actual value.

    Handles all known patterns: {query} {mobile} {num} {number} {q}
    {aadhaar} {ifsc} {pincode} {vehicle} {reg} {username} {id} {name}
    """
    for ph in (
        "{query}", "{mobile}", "{num}", "{number}", "{q}",
        "{aadhaar}", "{ifsc}", "{pincode}", "{vehicle}", "{reg}",
        "{username}", "{id}", "{name}",
    ):
        url = url.replace(ph, value)
    return url


def _build_headers() -> dict:
    key = API_KEY or os.getenv("API_KEY", "")
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
        headers["X-API-Key"] = key
    return headers


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
                limit=100,
                limit_per_host=20,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
                keepalive_timeout=30,
            )
            _session = aiohttp.ClientSession(
                timeout=TIMEOUT,
                headers=_build_headers(),
                connector=connector,
                connector_owner=True,
                raise_for_status=False,
            )
            logger.info("aiohttp session created. API_KEY present: %s", bool(API_KEY))
    return _session


async def close_session():
    """Gracefully close the shared session (call on bot shutdown)."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


# ── Startup config validation ─────────────────────────────────────────────────

def log_api_config():
    """Log which API URLs are configured at startup (presence only, no values)."""
    configs = {
        "API_NUMBER_LOOKUP":   bool(API_NUMBER_LOOKUP),
        "API_TELEGRAM_LOOKUP": bool(API_TELEGRAM_LOOKUP),
        "API_AADHAAR_LOOKUP":  bool(API_AADHAAR_LOOKUP),
        "API_FAMILY_LOOKUP":   bool(API_FAMILY_LOOKUP),
        "API_PINCODE_LOOKUP":  bool(API_PINCODE_LOOKUP),
        "API_IFSC_LOOKUP":     bool(API_IFSC_LOOKUP),
        "API_VEHICLE_LOOKUP":  bool(API_VEHICLE_LOOKUP),
        "API_KEY":             bool(API_KEY),
    }
    present = [k for k, v in configs.items() if v]
    missing = [k for k, v in configs.items() if not v]
    if present:
        logger.info("API config SET     : %s", ", ".join(present))
    if missing:
        logger.warning(
            "API config MISSING : %s  (those lookups will return no data)",
            ", ".join(missing),
        )


async def test_api_connection(url_template: str, test_value: str) -> tuple[bool, str]:
    """Live-test a URL template. Returns (ok, short_message)."""
    if not url_template:
        return False, "URL not configured"
    url = _substitute(url_template, test_value)
    try:
        session = await get_session()
        async with session.get(url) as resp:
            body = await resp.text()
            if resp.status == 200:
                return True, f"HTTP 200 — {body[:80]}"
            return False, f"HTTP {resp.status} — {body[:80]}"
    except asyncio.TimeoutError:
        return False, "Timeout (>15 s)"
    except Exception as exc:
        return False, str(exc)[:120]


# ── Core HTTP helper ──────────────────────────────────────────────────────────

async def _get(url: str) -> dict | list | None:
    """GET `url`, return parsed JSON or None on any error."""
    try:
        session = await get_session()
        logger.info("API GET  → %s", url)
        async with session.get(url) as resp:
            body = await resp.text()
            logger.info("API RESP ← HTTP %s | %.400s", resp.status, body)
            if resp.status == 200:
                import json
                try:
                    return json.loads(body)
                except json.JSONDecodeError as exc:
                    logger.error("JSON decode error: %s | raw: %.300s", exc, body)
                    return None
            elif resp.status == 401:
                logger.error("401 Unauthorized — check API_KEY | url=%s", url)
            elif resp.status == 403:
                logger.error("403 Forbidden — API key invalid/expired | url=%s", url)
            elif resp.status == 404:
                logger.warning("404 Not Found — wrong URL template? | url=%s", url)
            elif resp.status == 429:
                logger.warning("429 Rate Limited | url=%s", url)
            elif resp.status >= 500:
                logger.error("Server error %s | url=%s | body=%.200s", resp.status, url, body)
            else:
                logger.warning("HTTP %s | url=%s | body=%.200s", resp.status, url, body)
            return None
    except asyncio.TimeoutError:
        logger.error("Timeout (>15 s): %s", url)
        return None
    except aiohttp.ClientConnectorError as exc:
        logger.error("Connection error %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error %s: %s", url, exc, exc_info=True)
        return None


# ── Field normaliser ──────────────────────────────────────────────────────────

def _normalize_record(rec: dict) -> dict:
    def _pick(*keys):
        for k in keys:
            v = rec.get(k)
            if v not in (None, "", [], {}, "N/A", "n/a", "null", "NULL"):
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


def _parse_number_response(raw) -> list[dict] | None:
    """
    Parse any number-lookup API response shape into normalised records.

    Handles:
      Shape 1 — list at root:           [{...}, ...]
      Shape 2 — dict with status field: {"status": "success", "data": [...]}
      Shape 3 — dict with wrapper key:  {"data"/"result"/"records"/...}
      Shape 4 — flat dict as one record: {"name": ..., "mobile": ...}
    """
    if raw is None:
        return None

    # Shape 1: list at root
    if isinstance(raw, list):
        records = [_normalize_record(r) for r in raw if isinstance(r, dict)]
        records = [r for r in records if any(v for v in r.values())]
        return records or None

    if not isinstance(raw, dict):
        logger.warning("lookup_number: unexpected top-level type %s", type(raw).__name__)
        return None

    # Shape 2: check status field — accept success-like values or absent status
    status = str(raw.get("status", "")).lower()
    if status and status not in ("success", "ok", "true", "1", "200", "found", ""):
        logger.warning("lookup_number: API status=%r — treating as failure", status)
        return None

    # Shape 3: look for standard wrapper fields
    payload = (
        raw.get("data")
        or raw.get("result")
        or raw.get("results")
        or raw.get("records")
        or raw.get("response")
        or raw.get("output")
    )
    if payload is not None:
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            logger.warning("lookup_number: payload type %s", type(payload).__name__)
            return None
        records = [_normalize_record(r) for r in payload if isinstance(r, dict)]
        records = [r for r in records if any(v for v in r.values())]
        return records or None

    # Shape 4: treat the entire dict as one record
    normalized = _normalize_record(raw)
    if any(v for v in normalized.values()):
        logger.info("lookup_number: using root dict as single record")
        return [normalized]

    logger.warning("lookup_number: no usable fields. Keys: %s", list(raw.keys()))
    return None


# ── Lookup functions ──────────────────────────────────────────────────────────

async def lookup_number(mobile: str) -> list[dict] | None:
    key = cache_service.cache_key("number", mobile)

    async def _fetch():
        if not API_NUMBER_LOOKUP:
            logger.warning("lookup_number: API_NUMBER_LOOKUP not set in environment")
            return None
        url = _substitute(API_NUMBER_LOOKUP, mobile)
        raw = await _get(url)
        return _parse_number_response(raw)

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_telegram(username_or_id: str) -> dict | None:
    key = cache_service.cache_key("telegram", username_or_id)

    async def _fetch():
        if not API_TELEGRAM_LOOKUP:
            logger.info("lookup_telegram: not configured — returning demo")
            return _demo_telegram(username_or_id)
        url = _substitute(API_TELEGRAM_LOOKUP, username_or_id)
        return await _get(url)

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_aadhaar(aadhaar: str) -> dict | None:
    key = cache_service.cache_key("aadhaar", aadhaar)

    async def _fetch():
        if not API_AADHAAR_LOOKUP:
            logger.info("lookup_aadhaar: not configured — returning demo")
            return _demo_aadhaar(aadhaar)
        url = _substitute(API_AADHAAR_LOOKUP, aadhaar)
        return await _get(url)

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_family(aadhaar_or_name: str) -> dict | None:
    key = cache_service.cache_key("family", aadhaar_or_name)

    async def _fetch():
        if not API_FAMILY_LOOKUP:
            logger.info("lookup_family: not configured — returning demo")
            return _demo_family(aadhaar_or_name)
        url = _substitute(API_FAMILY_LOOKUP, aadhaar_or_name)
        return await _get(url)

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_pincode(pincode: str) -> dict | None:
    key = cache_service.cache_key("pincode", pincode)

    async def _fetch():
        if API_PINCODE_LOOKUP:
            url = _substitute(API_PINCODE_LOOKUP, pincode)
            result = await _get(url)
            if result:
                return result
            logger.warning("lookup_pincode: custom API failed, falling back to postalpincode.in")
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
        logger.warning("lookup_pincode: no data for %s", pincode)
        return None

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_ifsc(ifsc: str) -> dict | None:
    ifsc = ifsc.upper()
    key = cache_service.cache_key("ifsc", ifsc)

    async def _fetch():
        if API_IFSC_LOOKUP:
            url = _substitute(API_IFSC_LOOKUP, ifsc)
            result = await _get(url)
            if result:
                return result
            logger.warning("lookup_ifsc: custom API failed, falling back to razorpay")
        return await _get(f"https://ifsc.razorpay.com/{ifsc}")

    return await cache_service.get_or_fetch(key, _fetch())


async def lookup_vehicle(reg_no: str) -> dict | None:
    reg_no = reg_no.upper()
    key = cache_service.cache_key("vehicle", reg_no)

    async def _fetch():
        if not API_VEHICLE_LOOKUP:
            logger.info("lookup_vehicle: not configured — returning demo")
            return _demo_vehicle(reg_no)
        url = _substitute(API_VEHICLE_LOOKUP, reg_no)
        return await _get(url)

    return await cache_service.get_or_fetch(key, _fetch())


# ── Demo / fallback data (when API not configured) ────────────────────────────

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
