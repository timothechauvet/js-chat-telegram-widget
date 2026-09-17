import asyncio
import logging
import time
from .config import settings
from .database import get_db

logger = logging.getLogger(__name__)


async def prune_old_records() -> None:
    """Deletes messages, telegram mappings, and orphaned sessions older than retention limit."""
    if settings.HISTORY_RETENTION_HOURS <= 0:
        logger.info("Data retention set to 0. Pruning disabled.")
        return

    cutoff = int(time.time()) - (settings.HISTORY_RETENTION_HOURS * 3600)
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM messages WHERE created_at < ?;", (cutoff,))
            await db.execute("DELETE FROM telegram_map WHERE created_at < ?;", (cutoff,))
            await db.execute(
                "DELETE FROM sessions WHERE id NOT IN (SELECT DISTINCT session_id FROM messages);"
            )
            await db.commit()
            logger.info(f"Automated pruning completed. Records before timestamp {cutoff} removed.")
    except Exception as e:
        logger.error(f"Error during automated pruning: {e}")


async def cleaner_loop() -> None:
    """Runs data pruning every 1 hour (3600s)."""
    while True:
        await prune_old_records()
        await asyncio.sleep(3600)
