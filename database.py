from __future__ import annotations

import aiosqlite
import asyncio
import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

os.makedirs(os.path.dirname(DATABASE_PATH) if os.path.dirname(DATABASE_PATH) else ".", exist_ok=True)

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT,
    first_name     TEXT,
    last_name      TEXT,
    joined_at      TEXT DEFAULT (datetime('now')),
    is_banned      INTEGER DEFAULT 0,
    agreed_disclaimer INTEGER DEFAULT 0,
    total_searches INTEGER DEFAULT 0,
    last_seen      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS premium_users (
    user_id      INTEGER PRIMARY KEY,
    activated_at TEXT DEFAULT (datetime('now')),
    expires_at   TEXT,
    granted_by   INTEGER,
    plan_key     TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER,
    plan_key           TEXT,
    amount             INTEGER,
    status             TEXT DEFAULT 'pending',
    screenshot_file_id TEXT,
    created_at         TEXT DEFAULT (datetime('now')),
    reviewed_at        TEXT,
    reviewed_by        INTEGER
);

CREATE TABLE IF NOT EXISTS search_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER,
    username     TEXT,
    full_name    TEXT,
    search_type  TEXT,
    query        TEXT,
    result_found INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_searches (
    user_id     INTEGER,
    search_date TEXT,
    count       INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, search_date)
);

CREATE TABLE IF NOT EXISTS banned_users (
    user_id   INTEGER PRIMARY KEY,
    reason    TEXT,
    banned_at TEXT DEFAULT (datetime('now')),
    banned_by INTEGER
);

CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    level      TEXT,
    message    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS keys (
    key_code   TEXT PRIMARY KEY,
    plan_key   TEXT,
    used_by    INTEGER,
    used_at    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

# Indexes for fast lookups
_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sh_user       ON search_history(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sh_created    ON search_history(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_prem_expires  ON premium_users(expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_users_seen    ON users(last_seen)",
    "CREATE INDEX IF NOT EXISTS idx_txn_status    ON transactions(status)",
    "CREATE INDEX IF NOT EXISTS idx_ds_user_date  ON daily_searches(user_id, search_date)",
]

# ── Hot in-memory caches (avoid DB round-trips for frequent checks) ────────────
# (user_id) → (result: bool, timestamp: float)
_premium_cache: dict[int, tuple[bool, float]] = {}
_ban_cache:     dict[int, tuple[bool, float]] = {}
_HOT_TTL = 30.0   # seconds — short enough to stay accurate


def _hot_get(cache: dict, user_id: int) -> bool | None:
    entry = cache.get(user_id)
    if entry and time.monotonic() - entry[1] < _HOT_TTL:
        return entry[0]
    return None


def _hot_set(cache: dict, user_id: int, value: bool):
    cache[user_id] = (value, time.monotonic())


def _hot_invalidate(user_id: int):
    _premium_cache.pop(user_id, None)
    _ban_cache.pop(user_id, None)


# ── DB connection helper with performance pragmas ──────────────────────────────

@asynccontextmanager
async def _connect():
    """Open an aiosqlite connection with WAL mode and performance pragmas."""
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA cache_size=-20000")    # 20 MB page cache
        await conn.execute("PRAGMA temp_store=MEMORY")
        await conn.execute("PRAGMA mmap_size=134217728")  # 128 MB mmap I/O
        yield conn


# ── Init ───────────────────────────────────────────────────────────────────────

async def init_db():
    async with _connect() as db:
        for stmt in CREATE_TABLES.strip().split(";"):
            s = stmt.strip()
            if s:
                await db.execute(s)
        for idx in _INDEXES:
            await db.execute(idx)
        await db.commit()
        # Column migrations
        for col, typedef in [("username", "TEXT"), ("full_name", "TEXT")]:
            try:
                await db.execute(f"ALTER TABLE search_history ADD COLUMN {col} {typedef}")
                await db.commit()
            except Exception:
                pass
    logger.info("Database initialized.")


# ── Settings ───────────────────────────────────────────────────────────────────

async def set_setting(key: str, value: str):
    async with _connect() as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()


async def get_setting(key: str, default: str = None) -> str:
    async with _connect() as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


async def delete_setting(key: str):
    async with _connect() as db:
        await db.execute("DELETE FROM settings WHERE key=?", (key,))
        await db.commit()


# ── Users ──────────────────────────────────────────────────────────────────────

async def get_user(user_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()


async def upsert_user(user_id: int, username: str, first_name: str, last_name: str):
    async with _connect() as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                last_seen=datetime('now')
        """, (user_id, username, first_name, last_name))
        await db.commit()


async def set_disclaimer_agreed(user_id: int):
    async with _connect() as db:
        await db.execute("UPDATE users SET agreed_disclaimer=1 WHERE user_id=?", (user_id,))
        await db.commit()


# ── Ban ────────────────────────────────────────────────────────────────────────

async def is_banned(user_id: int) -> bool:
    cached = _hot_get(_ban_cache, user_id)
    if cached is not None:
        return cached
    async with _connect() as db:
        async with db.execute("SELECT 1 FROM banned_users WHERE user_id=?", (user_id,)) as cur:
            result = await cur.fetchone() is not None
    _hot_set(_ban_cache, user_id, result)
    return result


async def ban_user(user_id: int, reason: str, banned_by: int):
    async with _connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO banned_users (user_id, reason, banned_by) VALUES (?,?,?)",
            (user_id, reason, banned_by)
        )
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        await db.commit()
    _hot_invalidate(user_id)


async def unban_user(user_id: int):
    async with _connect() as db:
        await db.execute("DELETE FROM banned_users WHERE user_id=?", (user_id,))
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
        await db.commit()
    _hot_invalidate(user_id)


# ── Premium ────────────────────────────────────────────────────────────────────

async def is_premium(user_id: int) -> bool:
    cached = _hot_get(_premium_cache, user_id)
    if cached is not None:
        return cached
    async with _connect() as db:
        async with db.execute(
            "SELECT 1 FROM premium_users WHERE user_id=? AND expires_at > datetime('now')",
            (user_id,)
        ) as cur:
            result = await cur.fetchone() is not None
    _hot_set(_premium_cache, user_id, result)
    return result


async def get_premium_info(user_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM premium_users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()


async def grant_premium(user_id: int, days: int, granted_by: int, plan_key: str = "manual"):
    expires = datetime.utcnow() + timedelta(days=days)
    async with _connect() as db:
        await db.execute("""
            INSERT INTO premium_users (user_id, expires_at, granted_by, plan_key)
            VALUES (?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                expires_at=excluded.expires_at,
                granted_by=excluded.granted_by,
                plan_key=excluded.plan_key,
                activated_at=datetime('now')
        """, (user_id, expires.strftime("%Y-%m-%d %H:%M:%S"), granted_by, plan_key))
        await db.commit()
    _hot_invalidate(user_id)


async def revoke_premium(user_id: int):
    async with _connect() as db:
        await db.execute("DELETE FROM premium_users WHERE user_id=?", (user_id,))
        await db.commit()
    _hot_invalidate(user_id)


async def get_premium_users_list():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.user_id, u.username, u.first_name, u.last_name,
                   p.expires_at, p.plan_key, p.activated_at
            FROM premium_users p JOIN users u ON p.user_id=u.user_id
            WHERE p.expires_at > datetime('now')
            ORDER BY p.expires_at DESC
        """) as cur:
            return await cur.fetchall()


async def extend_all_premium(seconds: int):
    if seconds <= 0:
        return
    async with _connect() as db:
        await db.execute(
            "UPDATE premium_users SET expires_at = "
            "datetime(expires_at, '+' || CAST(? AS TEXT) || ' seconds') "
            "WHERE expires_at > datetime('now')",
            (seconds,)
        )
        await db.commit()
    _premium_cache.clear()   # invalidate all premium cache entries
    logger.info("Extended all active premium by %d seconds.", seconds)


async def get_premium_time_report():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT p.user_id, p.expires_at, p.plan_key, p.activated_at,
                   COALESCE(u.first_name || COALESCE(' ' || u.last_name, ''), 'Unknown') AS full_name,
                   COALESCE(u.username, '') AS username,
                   CAST((julianday(p.expires_at) - julianday('now')) * 86400 AS INTEGER) AS seconds_remaining
            FROM premium_users p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.expires_at > datetime('now')
            ORDER BY p.expires_at ASC
        """) as cur:
            return await cur.fetchall()


# ── Premium Freeze ─────────────────────────────────────────────────────────────

async def freeze_premium_start():
    await set_setting("freeze_start_time", str(int(time.time())))
    await set_setting("premium_frozen", "1")


async def freeze_premium_end():
    freeze_start = await get_setting("freeze_start_time")
    if freeze_start:
        gap = int(time.time()) - int(freeze_start)
        await extend_all_premium(gap)
        await delete_setting("freeze_start_time")
        logger.info("Maintenance freeze ended. Extended premiums by %ds.", gap)
    await set_setting("premium_frozen", "0")


async def is_premium_frozen() -> bool:
    val = await get_setting("premium_frozen", "0")
    return val == "1"


async def get_freeze_info() -> dict:
    frozen = await is_premium_frozen()
    freeze_start = await get_setting("freeze_start_time")
    frozen_secs = 0
    if frozen and freeze_start:
        frozen_secs = int(time.time()) - int(freeze_start)
    return {"frozen": frozen, "frozen_since": freeze_start, "frozen_secs": frozen_secs}


# ── Search Logs ────────────────────────────────────────────────────────────────

async def log_search(user_id: int, search_type: str, query: str, result_found: bool,
                     username: str = None, full_name: str = None):
    async with _connect() as db:
        await db.execute(
            "INSERT INTO search_history "
            "(user_id, username, full_name, search_type, query, result_found) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, username, full_name, search_type, query, 1 if result_found else 0)
        )
        await db.commit()


async def get_search_logs(limit: int = 10):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sh.id, sh.user_id, sh.search_type, sh.query,
                   sh.result_found, sh.created_at,
                   COALESCE(sh.full_name,
                       NULLIF(TRIM(COALESCE(u.first_name,'') || ' ' || COALESCE(u.last_name,'')), ''),
                       'Unknown') AS full_name,
                   COALESCE(sh.username, u.username, '') AS username
            FROM search_history sh
            LEFT JOIN users u ON sh.user_id = u.user_id
            ORDER BY sh.created_at DESC
            LIMIT ?
        """, (limit,)) as cur:
            return await cur.fetchall()


async def clear_search_logs():
    async with _connect() as db:
        await db.execute("DELETE FROM search_history")
        await db.commit()


async def export_search_logs():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT sh.id, sh.user_id, sh.search_type, sh.query,
                   sh.result_found, sh.created_at,
                   COALESCE(sh.full_name,
                       NULLIF(TRIM(COALESCE(u.first_name,'') || ' ' || COALESCE(u.last_name,'')), ''),
                       'Unknown') AS full_name,
                   COALESCE(sh.username, u.username, '') AS username
            FROM search_history sh
            LEFT JOIN users u ON sh.user_id = u.user_id
            ORDER BY sh.created_at DESC
        """) as cur:
            return await cur.fetchall()


# ── Daily Searches ─────────────────────────────────────────────────────────────

async def get_daily_search_count(user_id: int) -> int:
    today = date.today().isoformat()
    async with _connect() as db:
        async with db.execute(
            "SELECT count FROM daily_searches WHERE user_id=? AND search_date=?",
            (user_id, today)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def increment_daily_search(user_id: int):
    today = date.today().isoformat()
    async with _connect() as db:
        await db.execute("""
            INSERT INTO daily_searches (user_id, search_date, count) VALUES (?,?,1)
            ON CONFLICT(user_id, search_date) DO UPDATE SET count=count+1
        """, (user_id, today))
        await db.execute("UPDATE users SET total_searches=total_searches+1 WHERE user_id=?", (user_id,))
        await db.commit()


# ── Transactions ───────────────────────────────────────────────────────────────

async def create_transaction(user_id: int, plan_key: str, amount: int, screenshot_file_id: str) -> int:
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO transactions (user_id, plan_key, amount, screenshot_file_id) VALUES (?,?,?,?)",
            (user_id, plan_key, amount, screenshot_file_id)
        )
        await db.commit()
        return cur.lastrowid


async def update_transaction_status(txn_id: int, status: str, reviewed_by: int):
    async with _connect() as db:
        await db.execute(
            "UPDATE transactions SET status=?, reviewed_at=datetime('now'), reviewed_by=? WHERE id=?",
            (status, reviewed_by, txn_id)
        )
        await db.commit()


async def get_pending_transactions():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM transactions WHERE status='pending' ORDER BY created_at DESC"
        ) as cur:
            return await cur.fetchall()


# ── Stats ──────────────────────────────────────────────────────────────────────

async def get_stats():
    async with _connect() as db:
        stats = {}
        queries = [
            ("total_users",     "SELECT COUNT(*) FROM users"),
            ("premium_users",   "SELECT COUNT(*) FROM premium_users WHERE expires_at > datetime('now')"),
            ("today_searches",  "SELECT COUNT(*) FROM search_history WHERE date(created_at)=date('now')"),
            ("total_searches",  "SELECT COUNT(*) FROM search_history"),
            ("active_today",    "SELECT COUNT(*) FROM users WHERE date(last_seen)=date('now')"),
            ("banned_users",    "SELECT COUNT(*) FROM banned_users"),
            ("pending_payments","SELECT COUNT(*) FROM transactions WHERE status='pending'"),
        ]
        for key, sql in queries:
            async with db.execute(sql) as cur:
                stats[key] = (await cur.fetchone())[0]
        return stats


async def get_all_users():
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY joined_at DESC") as cur:
            return await cur.fetchall()


async def delete_user(user_id: int):
    async with _connect() as db:
        for table in ("users", "premium_users", "search_history", "daily_searches"):
            await db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        await db.commit()
    _hot_invalidate(user_id)


async def clear_database():
    async with _connect() as db:
        for table in ["users", "premium_users", "transactions", "search_history",
                      "daily_searches", "banned_users", "logs", "keys"]:
            await db.execute(f"DELETE FROM {table}")
        await db.commit()
    _premium_cache.clear()
    _ban_cache.clear()


# ── Keys ───────────────────────────────────────────────────────────────────────

async def create_key(key_code: str, plan_key: str):
    async with _connect() as db:
        await db.execute("INSERT OR IGNORE INTO keys (key_code, plan_key) VALUES (?,?)", (key_code, plan_key))
        await db.commit()


async def redeem_key(key_code: str, user_id: int):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM keys WHERE key_code=? AND used_by IS NULL", (key_code,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        await db.execute(
            "UPDATE keys SET used_by=?, used_at=datetime('now') WHERE key_code=?",
            (user_id, key_code)
        )
        await db.commit()
        return row


# ── Admin Logs ─────────────────────────────────────────────────────────────────

async def log_admin_action(admin_id: int, action: str):
    async with _connect() as db:
        await db.execute(
            "INSERT INTO logs (level, message) VALUES ('ADMIN', ?)",
            (f"Admin {admin_id}: {action}",)
        )
        await db.commit()
