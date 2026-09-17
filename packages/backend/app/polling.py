import asyncio
import logging
from .config import settings
from .routes import process_telegram_update
from .telegram import telegram_service

logger = logging.getLogger(__name__)


async def telegram_polling_loop() -> None:
    """Long-polling background worker for local development or non-webhook environments."""
    logger.info("Starting Telegram polling loop...")
    offset: int | None = None
    while True:
        try:
            updates = await telegram_service.get_updates(offset=offset, timeout=5)
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    await process_telegram_update(update)
                except Exception as err:
                    logger.error(f"Error processing Telegram update {update.get('update_id')}: {err}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("Telegram polling loop cancelled.")
            break
        except Exception as e:
            logger.warning(f"Telegram polling loop error: {e}")
            await asyncio.sleep(2)
