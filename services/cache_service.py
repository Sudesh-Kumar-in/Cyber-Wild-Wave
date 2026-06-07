"""
LRU cache with TTL and in-flight request deduplication.
- Prevents duplicate simultaneous API calls for the same key
- Evicts least-recently-used entries when max size is reached
- Each entry has a TTL; expired entries are evicted lazily
"""
import time
import asyncio
from collections import OrderedDict
from config import CACHE_TTL

_MAX_SIZE = 2000


class _LRUCache:
    __slots__ = ("_store", "_max", "_ttl")

    def __init__(self, max_size: int, ttl: int):
        self._store: OrderedDict[str, tuple] = OrderedDict()
        self._max = max_size
        self._ttl = ttl

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, ts = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, time.monotonic())
        if len(self._store) > self._max:
            self._store.popitem(last=False)

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


_cache = _LRUCache(max_size=_MAX_SIZE, ttl=CACHE_TTL)

# In-flight dedup: key → asyncio.Future
# If two coroutines request the same key simultaneously, the second
# awaits the first's result instead of making a duplicate API call.
_in_flight: dict[str, asyncio.Future] = {}


def get(key: str):
    return _cache.get(key)


def set(key: str, value):
    _cache.set(key, value)


def delete(key: str):
    _cache.delete(key)


def clear():
    _cache.clear()


def cache_key(*parts) -> str:
    return ":".join(str(p).lower() for p in parts)


async def get_or_fetch(key: str, fetch_coro):
    """
    Return cached value immediately, or run `fetch_coro` exactly once
    even if called concurrently with the same key.
    """
    cached = _cache.get(key)
    if cached is not None:
        return cached

    if key in _in_flight:
        try:
            return await asyncio.shield(_in_flight[key])
        except Exception:
            return None

    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _in_flight[key] = fut

    try:
        result = await fetch_coro
        if result is not None:
            _cache.set(key, result)
        fut.set_result(result)
        return result
    except Exception as exc:
        if not fut.done():
            fut.set_exception(exc)
        return None
    finally:
        _in_flight.pop(key, None)
