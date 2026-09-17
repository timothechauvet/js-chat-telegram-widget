import aiosqlite
import logging
from contextlib import asynccontextmanager
from .config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db


async def init_db() -> None:
    async with get_db() as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            website_name TEXT,
            calling_url TEXT,
            created_at INTEGER NOT NULL,
            last_active INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT,
            media_type TEXT,
            media_url TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS admin_subscribers (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            authenticated_at INTEGER NOT NULL
        );
        """)

        # Check sessions columns and add website_name / calling_url if missing
        cursor_sess = await db.execute("PRAGMA table_info(sessions);")
        sess_cols = [row["name"] for row in await cursor_sess.fetchall()]
        if "website_name" not in sess_cols:
            await db.execute("ALTER TABLE sessions ADD COLUMN website_name TEXT;")
        if "calling_url" not in sess_cols:
            await db.execute("ALTER TABLE sessions ADD COLUMN calling_url TEXT;")

        # Check telegram_map schema and migrate if needed
        cursor = await db.execute("PRAGMA table_info(telegram_map);")
        columns = [row["name"] for row in await cursor.fetchall()]
        if not columns:
            await db.execute("""
            CREATE TABLE telegram_map (
                telegram_message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL DEFAULT 0,
                session_id TEXT NOT NULL,
                media_type TEXT,
                original_text TEXT,
                website_name TEXT,
                calling_url TEXT,
                is_replied INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (telegram_message_id, chat_id)
            );
            """)
        elif "chat_id" not in columns:
            await db.executescript("""
            CREATE TABLE telegram_map_new (
                telegram_message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL DEFAULT 0,
                session_id TEXT NOT NULL,
                media_type TEXT,
                original_text TEXT,
                website_name TEXT,
                calling_url TEXT,
                is_replied INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (telegram_message_id, chat_id)
            );
            INSERT OR IGNORE INTO telegram_map_new (telegram_message_id, session_id, created_at)
            SELECT telegram_message_id, session_id, created_at FROM telegram_map;
            DROP TABLE telegram_map;
            ALTER TABLE telegram_map_new RENAME TO telegram_map;
            """)
        else:
            if "media_type" not in columns:
                await db.execute("ALTER TABLE telegram_map ADD COLUMN media_type TEXT;")
            if "original_text" not in columns:
                await db.execute("ALTER TABLE telegram_map ADD COLUMN original_text TEXT;")
            if "website_name" not in columns:
                await db.execute("ALTER TABLE telegram_map ADD COLUMN website_name TEXT;")
            if "calling_url" not in columns:
                await db.execute("ALTER TABLE telegram_map ADD COLUMN calling_url TEXT;")
            if "is_replied" not in columns:
                await db.execute("ALTER TABLE telegram_map ADD COLUMN is_replied INTEGER DEFAULT 0;")

        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_tg_map_session ON telegram_map(session_id);")
        await db.commit()
        logger.info(f"Database initialized at {settings.db_path}")
