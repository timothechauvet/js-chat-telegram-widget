import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .cleaner import cleaner_loop
from .config import settings
from .database import init_db
from .routes import router

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
    version="1.0.0",
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
    return {"status": "healthy"}
