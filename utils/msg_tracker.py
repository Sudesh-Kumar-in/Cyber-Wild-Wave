"""
Tracks bot-generated message IDs per user so they can be bulk-deleted
before delivering a clean search result.

Usage:
    from utils.msg_tracker import track, cleanup_all

    sent = await chat.send_message(...)
    track(ctx, sent)

    # Before showing the final result:
    await cleanup_all(bot, chat_id, ctx)
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


def track(ctx, msg) -> None:
    """Add a bot message to the per-user cleanup list."""
    if msg and hasattr(msg, "message_id"):
        ctx.user_data.setdefault("_bot_msgs", []).append(msg.message_id)


async def cleanup_all(bot, chat_id: int, ctx) -> None:
    """Silently delete every tracked bot message for this user."""
    ids = ctx.user_data.pop("_bot_msgs", [])
    if not ids:
        return
    await asyncio.gather(
        *[_del(bot, chat_id, mid) for mid in ids],
        return_exceptions=True
    )


async def _del(bot, chat_id: int, msg_id: int) -> None:
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass
