from __future__ import annotations

import time
from collections import defaultdict
from config import RATE_LIMIT_SECONDS

_last_request: dict[int, float] = defaultdict(float)
_pending_actions: dict[int, str] = {}


def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    if now - _last_request[user_id] < RATE_LIMIT_SECONDS:
        return False
    _last_request[user_id] = now
    return True


def set_pending_action(user_id: int, action: str):
    _pending_actions[user_id] = action


def get_pending_action(user_id: int) -> str | None:
    return _pending_actions.get(user_id)


def clear_pending_action(user_id: int):
    _pending_actions.pop(user_id, None)
