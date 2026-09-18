import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .cleaner import cleaner_loop
from .config import settings
from .database import init_db
from .routes import router
from .telegram import telegram_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_chat_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    cleaner_task = asyncio.create_task(cleaner_loop())
    logger.info("Background cleaner task started.")

    polling_task = None
    if settings.TELEGRAM_POLLING_MODE:
        from .polling import telegram_polling_loop
        polling_task = asyncio.create_task(telegram_polling_loop())
        logger.info("Telegram long-polling task started.")
    elif settings.TELEGRAM_WEBHOOK_URL and settings.TELEGRAM_BOT_TOKEN:
        webhook_url = settings.TELEGRAM_WEBHOOK_URL.strip()
        if not webhook_url.endswith("/api/v1/telegram-webhook"):
            webhook_url = f"{webhook_url.rstrip('/')}/api/v1/telegram-webhook"
        secret = (
            settings.TELEGRAM_WEBHOOK_SECRET
            if settings.TELEGRAM_WEBHOOK_SECRET and settings.TELEGRAM_WEBHOOK_SECRET != "change-this-webhook-secret"
            else None
        )
        logger.info(f"Configuring Telegram webhook for {webhook_url}...")
        await telegram_service.set_webhook(webhook_url, secret_token=secret)

    yield
    # Shutdown
    cleaner_task.cancel()
    if polling_task:
        polling_task.cancel()
    try:
        await cleaner_task
        if polling_task:
            await polling_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Telegram Live Chat Backend",
    version="1.0.3",
    lifespan=lifespan,
)

# Configure CORS
origins = [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]
if "*" in origins:
    allow_origins = ["*"]
else:
    allow_origins = origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.3",
        "polling_mode": settings.TELEGRAM_POLLING_MODE,
        "webhook_url": settings.TELEGRAM_WEBHOOK_URL or None,
    }


@app.get("/api/v1/webhook-status")
async def webhook_status():
    """Returns Telegram webhook info for troubleshooting."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"configured": False, "detail": "Bot token not configured"}
    info = await telegram_service.get_webhook_info()
    return {
        "configured": True,
        "expected_url": settings.TELEGRAM_WEBHOOK_URL or None,
        "telegram_info": info,
    }
