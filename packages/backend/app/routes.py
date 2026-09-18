import html
import logging
import mimetypes
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import uuid
from typing import Optional
from urllib.parse import urlparse
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .config import settings
from .database import get_db
from .security import (
    check_rate_limit,
    is_extension_safe,
    sanitize_filename,
    verify_session_token,
)
from .telegram import telegram_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


class MessageOut(BaseModel):
    id: str
    session_id: str
    sender: str
    text: Optional[str] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    created_at: int


def resolve_site_info(
    request: Request,
    site_id: str,
    page_url: Optional[str] = None,
    page_title: Optional[str] = None,
) -> tuple[str, str]:
    """
    Resolves the website name configured by backend knowing which URL called from frontend.
    Returns: (website_name, calling_url)
    """
    header_page_url = request.headers.get("x-page-url") or ""
    origin = request.headers.get("origin") or ""
    referer = request.headers.get("referer") or ""
    host = request.headers.get("host") or ""

    if page_url and page_url.strip():
        raw_calling_url = page_url.strip()
    elif header_page_url and header_page_url.strip():
        raw_calling_url = header_page_url.strip()
    elif origin and origin.strip():
        raw_calling_url = origin.strip()
    elif referer and referer.strip():
        raw_calling_url = referer.strip()
    elif host and host.strip():
        raw_calling_url = f"http://{host.strip()}"
    else:
        raw_calling_url = site_id or "local"

    calling_url = raw_calling_url
    if "?" in calling_url:
        calling_url = calling_url.split("?")[0]
    if "#" in calling_url:
        calling_url = calling_url.split("#")[0]
    if calling_url.endswith("/") and len(calling_url) > 8:
        calling_url = calling_url.rstrip("/")

    candidates: list[str] = []
    for u in [raw_calling_url, calling_url, origin, referer]:
        if not u:
            continue
        u_clean = u.strip().rstrip("/")
        candidates.append(u_clean)
        try:
            p = urlparse(u)
            if p.netloc:
                candidates.append(f"{p.scheme}://{p.netloc}")
                candidates.append(p.netloc)
                if p.port:
                    if p.hostname in ["localhost", "127.0.0.1"]:
                        alt_host = "127.0.0.1" if p.hostname == "localhost" else "localhost"
                        candidates.append(f"{alt_host}:{p.port}")
                        candidates.append(f"{p.scheme}://{alt_host}:{p.port}")
                if p.hostname:
                    candidates.append(p.hostname)
                    if p.hostname in ["localhost", "127.0.0.1"]:
                        candidates.append("localhost")
                        candidates.append("127.0.0.1")
        except Exception:
            pass

    if site_id:
        candidates.append(site_id)
        candidates.append(site_id.lower())

    configured_mapping = settings.site_names
    normalized_mapping = {str(k).lower().rstrip("/"): str(v) for k, v in configured_mapping.items()}

    website_name: Optional[str] = None
    for cand in candidates:
        if not cand:
            continue
        cand_lower = cand.lower().rstrip("/")
        if cand_lower in normalized_mapping:
            website_name = normalized_mapping[cand_lower]
            break

    if not website_name:
        if page_title and page_title.strip() and page_title.strip().lower() not in ["document", "untitled", "demo"]:
            website_name = page_title.strip()
        elif site_id and site_id.lower() not in ["localhost", "127.0.0.1", "default", "undefined", "null"]:
            website_name = site_id.replace("-", " ").replace("_", " ").title()
        elif origin or referer:
            try:
                p = urlparse(origin or referer)
                hostname = p.hostname or p.netloc
                if p.port:
                    website_name = f"{hostname.capitalize()} ({p.port})"
                else:
                    website_name = hostname.capitalize()
            except Exception:
                website_name = "Live Chat Support"
        else:
            website_name = "Live Chat Support"

    return website_name, calling_url


async def get_active_admin_chats() -> list[int | str]:
    """Retrieves list of all authenticated admin chat IDs."""
    chats: list[int | str] = []
    async with get_db() as db:
        cursor = await db.execute("SELECT chat_id FROM admin_subscribers;")
        rows = await cursor.fetchall()
        for row in rows:
            chats.append(row["chat_id"])

    if settings.TELEGRAM_ADMIN_CHAT_ID:
        try:
            default_id = int(settings.TELEGRAM_ADMIN_CHAT_ID)
        except ValueError:
            default_id = settings.TELEGRAM_ADMIN_CHAT_ID
        if default_id and default_id not in chats:
            chats.append(default_id)

    return chats


@router.post("/send")
async def send_message(
    request: Request,
    response: Response,
    site_id: str = Form(...),
    page_url: Optional[str] = Form(None),
    page_title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    session_id: str = Depends(verify_session_token),
):
    check_rate_limit(session_id)

    if not text and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must include text or an attachment.",
        )

    file_bytes: Optional[bytes] = None
    clean_name: Optional[str] = None
    content_type: Optional[str] = None

    if file:
        file_bytes = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

        original_name = file.filename or "attachment"
        if not is_extension_safe(original_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type is not permitted for security reasons.",
            )

        clean_name = sanitize_filename(original_name)
        content_type = file.content_type or mimetypes.guess_type(clean_name)[0] or "application/octet-stream"

    now = int(time.time())
    message_uuid = str(uuid.uuid4())

    website_name, calling_url = resolve_site_info(
        request, site_id, page_url=page_url, page_title=page_title
    )

    # 1. Upsert session with resolved website information
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO sessions (id, site_id, website_name, calling_url, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_active = excluded.last_active,
                website_name = COALESCE(excluded.website_name, sessions.website_name),
                calling_url = COALESCE(excluded.calling_url, sessions.calling_url);
            """,
            (session_id, site_id, website_name, calling_url, now, now),
        )
        await db.commit()

    # 2. Dispatch to Telegram (Broadcast to all authenticated admins)
    short_session = session_id[:8]
    safe_site = html.escape(website_name)
    safe_url = html.escape(calling_url)
    safe_text = html.escape(text) if text else ""
    header_caption = (
        f"🌐 Website: [<b>{safe_site}</b>]\n"
        f"🔗 Source: <code>{safe_url}</code>\n"
        f"🆔 Session: [<code>{short_session}</code>]\n"
        f"⏳ Status: <b>Pending Reply</b>\n"
        f"──────────────────\n"
    )

    media_type: Optional[str] = None
    media_url: Optional[str] = None

    if file and file_bytes and clean_name and content_type:
        local_media_name = f"{message_uuid}_{clean_name}"
        media_file_path = settings.data_path / local_media_name
        media_file_path.write_bytes(file_bytes)
        media_url = f"/api/v1/media/{local_media_name}"

    target_chats = await get_active_admin_chats()
    tg_dispatched: list[tuple[int | str, int]] = []

    if target_chats:
        for chat_id in target_chats:
            try:
                if file and file_bytes and clean_name and content_type:
                    caption = f"{header_caption}{safe_text}"
                    tg_msg_id, m_type = await telegram_service.send_media(
                        media_bytes=file_bytes,
                        filename=clean_name,
                        content_type=content_type,
                        caption=caption,
                        chat_id=chat_id,
                    )
                    media_type = m_type
                    tg_dispatched.append((chat_id, tg_msg_id))
                else:
                    await telegram_service.send_chat_action("typing", chat_id=chat_id)
                    full_text = f"{header_caption}{safe_text}"
                    tg_msg_id = await telegram_service.send_message(full_text, chat_id=chat_id)
                    tg_dispatched.append((chat_id, tg_msg_id))
            except Exception as e:
                logger.error(f"Failed to dispatch message to Telegram admin chat {chat_id}: {e}")
    else:
        logger.warning("No authenticated Telegram admin chats available. Message saved locally.")

    # 3. Store visitor message & mapping for each receiving admin
    async with get_db() as db:
        for chat_id, tg_msg_id in tg_dispatched:
            await db.execute(
                """
                INSERT OR REPLACE INTO telegram_map (telegram_message_id, chat_id, session_id, media_type, original_text, website_name, calling_url, is_replied, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?);
                """,
                (tg_msg_id, int(chat_id) if str(chat_id).lstrip("-").isdigit() else 0, session_id, media_type, safe_text, website_name, calling_url, now),
            )
        await db.execute(
            """
            INSERT INTO messages (id, session_id, sender, text, media_type, media_url, created_at)
            VALUES (?, ?, 'visitor', ?, ?, ?, ?);
            """,
            (message_uuid, session_id, text, media_type, media_url, now),
        )
        await db.commit()

    # Set cookie for persistence
    is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        key="tg_chat_token",
        value=session_id,
        max_age=31536000,
        path="/",
        samesite="none" if is_secure else "lax",
        secure=is_secure,
    )
    return {"status": "ok", "message_id": message_uuid}


@router.get("/status")
async def get_status(
    request: Request,
    session_id: str = Depends(verify_session_token),
):
    now_de = datetime.now(ZoneInfo("Europe/Berlin"))
    hour = now_de.hour
    is_night = hour >= settings.NIGHT_START or hour < settings.NIGHT_END

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT created_at FROM messages WHERE sender = 'admin' AND session_id = ? ORDER BY created_at DESC LIMIT 1;",
            (session_id,),
        )
        row = await cursor.fetchone()
        last_admin_msg = row["created_at"] if row else 0
        is_active = (int(time.time()) - last_admin_msg) < 900

    return {
        "is_online": is_active and not is_night,
        "is_night": is_night,
        "is_active": is_active,
        "offline_message": settings.OFFLINE_MESSAGE,
    }


@router.get("/messages", response_model=list[MessageOut])
async def get_messages(
    request: Request,
    response: Response,
    since: Optional[int] = None,
    session_id: str = Depends(verify_session_token),
):
    """Retrieves messages strictly belonging to the authenticated session."""
    is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        key="tg_chat_token",
        value=session_id,
        max_age=31536000,
        path="/",
        samesite="none" if is_secure else "lax",
        secure=is_secure,
    )
    query = """
        SELECT id, session_id, sender, text, media_type, media_url, created_at
        FROM messages
        WHERE session_id = ?
    """
    params = [session_id]

    if since is not None:
        query += " AND created_at > ?"
        params.append(since)

    query += " ORDER BY created_at ASC;"

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/media/{file_id}")
async def get_media_file(
    file_id: str,
    session_id: str = Depends(verify_session_token),
):
    """Streams file securely ensuring session ownership and preventing directory traversal."""
    clean_id = sanitize_filename(file_id)

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM messages WHERE session_id = ? AND media_url LIKE ?;",
            (session_id, f"%{clean_id}"),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media file not found or unauthorized.",
            )

    local_path = (settings.data_path / clean_id).resolve()
    if not str(local_path).startswith(str(settings.data_path.resolve())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )

    if local_path.is_file():
        mime = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"

        def iterfile():
            with open(local_path, mode="rb") as f:
                yield from f

        return StreamingResponse(iterfile(), media_type=mime)

    try:
        tg_file_path = await telegram_service.get_file_path(file_id)
        mime = mimetypes.guess_type(tg_file_path)[0] or "application/octet-stream"
        return StreamingResponse(
            telegram_service.stream_file(tg_file_path),
            media_type=mime,
        )
    except Exception as e:
        logger.error(f"Error fetching remote Telegram file: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not accessible.",
        )


@router.post("/telegram-webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """Receives webhook updates from Telegram with secret token verification."""
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET.strip() if settings.TELEGRAM_WEBHOOK_SECRET else ""
    if expected_secret and expected_secret != "change-this-webhook-secret":
        if x_telegram_bot_api_secret_token != expected_secret:
            logger.warning(
                f"Unauthorized telegram-webhook call. Header: {x_telegram_bot_api_secret_token!r} does not match expected secret."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Telegram secret token.",
            )

    try:
        payload = await request.json()
    except Exception as e:
        logger.warning(f"Malformed JSON payload in telegram-webhook: {e}")
        return {"status": "ignored"}

    try:
        return await process_telegram_update(payload)
    except Exception as e:
        logger.error(f"Error processing Telegram webhook update: {e}", exc_info=True)
        # Always return 200 OK so Telegram does not retry indefinitely and disable webhook
        return {"status": "error", "detail": str(e)}


async def process_telegram_update(payload: dict) -> dict:
    """Processes a single Telegram update payload (from webhook or polling)."""
    message = payload.get("message")
    if not message:
        return {"status": "ignored"}

    chat_id = message.get("chat", {}).get("id", 0)
    from_user = message.get("from", {})
    username = from_user.get("username") or ""
    first_name = from_user.get("first_name") or "Agent"
    agent_tag = f"@{username}" if username else first_name
    text_content = (message.get("text") or message.get("caption") or "").strip()

    reply_to = message.get("reply_to_message")

    # =========================================================================
    # Case A: Direct message / Admin commands (Authentication / Registration)
    # =========================================================================
    if not reply_to:
        if text_content.startswith("/"):
            parts = text_content.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ["/auth", "/login", "/start"]:
                expected_secrets = [settings.TELEGRAM_AUTH_SECRET, settings.BACKEND_SECRET_KEY]
                if arg and any(arg == s for s in expected_secrets if s):
                    now = int(time.time())
                    async with get_db() as db:
                        await db.execute(
                            """
                            INSERT INTO admin_subscribers (chat_id, username, first_name, authenticated_at)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(chat_id) DO UPDATE SET
                                username = excluded.username,
                                first_name = excluded.first_name,
                                authenticated_at = excluded.authenticated_at;
                            """,
                            (chat_id, username, first_name, now),
                        )
                        await db.commit()

                    await telegram_service.send_message_to_chat(
                        chat_id=chat_id,
                        text="✅ <b>Authentication successful!</b>\n"
                             "You are now subscribed to live visitor chat broadcasts.\n"
                             "Reply directly to any visitor message to chat with them.",
                    )
                    return {"status": "authenticated"}
                elif cmd == "/start" and not arg:
                    await telegram_service.send_message_to_chat(
                        chat_id=chat_id,
                        text="👋 <b>Welcome to Telegram Live Chat Support Gateway!</b>\n\n"
                             "To authenticate and receive visitor chat messages, send:\n"
                             "<code>/auth YOUR_SECRET_KEY</code>",
                    )
                    return {"status": "prompted_auth"}
                else:
                    await telegram_service.send_message_to_chat(
                        chat_id=chat_id,
                        text="❌ <b>Authentication failed.</b>\nInvalid secret token. Please use <code>/auth &lt;secret&gt;</code>.",
                    )
                    return {"status": "auth_failed"}

            elif cmd in ["/deauth", "/logout"]:
                async with get_db() as db:
                    await db.execute("DELETE FROM admin_subscribers WHERE chat_id = ?;", (chat_id,))
                    await db.commit()
                await telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    text="👋 <b>Unsubscribed.</b> You will no longer receive live chat messages.",
                )
                return {"status": "unsubscribed"}

            elif cmd == "/status":
                async with get_db() as db:
                    cursor = await db.execute("SELECT COUNT(*) as count FROM admin_subscribers WHERE chat_id = ?;", (chat_id,))
                    row = await cursor.fetchone()
                    is_sub = bool(row and row["count"] > 0)

                    cursor_all = await db.execute("SELECT COUNT(*) as count FROM admin_subscribers;")
                    row_all = await cursor_all.fetchone()
                    total_agents = row_all["count"] if row_all else 0

                status_str = "Subscribed (Active Agent)" if is_sub else "Not subscribed (Guest)"
                await telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    text=f"ℹ️ <b>Live Chat System Status</b>\n"
                         f"Your Status: <b>{status_str}</b>\n"
                         f"Total Active Agents: <b>{total_agents}</b>",
                )
                return {"status": "ok"}

            elif cmd == "/reply":
                target_sess: Optional[str] = None
                admin_reply_text: str = ""
                w_name: str = "Live Chat"
                c_url: str = ""
                tokens = arg.split(maxsplit=1) if arg else []
                async with get_db() as db:
                    if len(tokens) >= 2:
                        possible_sess = tokens[0].strip()
                        cur = await db.execute(
                            "SELECT id, site_id, website_name, calling_url FROM sessions WHERE id LIKE ? ORDER BY last_active DESC LIMIT 1;",
                            (f"{possible_sess}%",),
                        )
                        s_match = await cur.fetchone()
                        if s_match:
                            target_sess = s_match["id"]
                            admin_reply_text = tokens[1].strip()
                            w_name = s_match["website_name"] or settings.site_names.get(s_match["site_id"]) or s_match["site_id"]
                            c_url = s_match["calling_url"] or ""

                    if not target_sess and arg:
                        now_ts = int(time.time())
                        cur = await db.execute(
                            "SELECT id, site_id, website_name, calling_url FROM sessions WHERE last_active > ? ORDER BY last_active DESC LIMIT 2;",
                            (now_ts - 1800,),
                        )
                        active_rows = await cur.fetchall()
                        if len(active_rows) == 1:
                            target_sess = active_rows[0]["id"]
                            admin_reply_text = arg
                            w_name = active_rows[0]["website_name"] or settings.site_names.get(active_rows[0]["site_id"]) or active_rows[0]["site_id"]
                            c_url = active_rows[0]["calling_url"] or ""

                if target_sess and admin_reply_text:
                    now = int(time.time())
                    message_uuid = str(uuid.uuid4())
                    async with get_db() as db:
                        await db.execute(
                            "INSERT INTO messages (id, session_id, sender, text, created_at) VALUES (?, ?, 'admin', ?, ?);",
                            (message_uuid, target_sess, admin_reply_text, now),
                        )
                        await db.commit()

                    await telegram_service.send_message_to_chat(
                        chat_id=chat_id,
                        text=f"✅ <b>Sent to visitor session [<code>{target_sess[:8]}</code>] on 🌐 {html.escape(w_name)}!</b>",
                    )
                    return {"status": "ok", "message_id": message_uuid}

        active_chats = await get_active_admin_chats()
        if chat_id in active_chats:
            recent_sessions = []
            async with get_db() as db:
                sess_cur = await db.execute(
                    """
                    SELECT DISTINCT session_id, website_name, calling_url
                    FROM telegram_map
                    ORDER BY created_at DESC LIMIT 5;
                    """
                )
                for s in await sess_cur.fetchall():
                    s_short = s["session_id"][:8]
                    s_name = s["website_name"] or "Website"
                    s_url = s["calling_url"] or ""
                    recent_sessions.append(f"• 🌐 <b>{html.escape(s_name)}</b> (<code>{html.escape(s_url)}</code>) — Session: [<code>{s_short}</code>]")

            sess_block = "\n".join(recent_sessions) if recent_sessions else "None currently active"
            try:
                await telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    text="💡 <b>Hint</b>: Please <b>reply directly</b> to a visitor's message (swipe or right-click → Reply) to send your answer to that session.\n"
                         "Or send: <code>/reply &lt;session_id&gt; &lt;your message&gt;</code>\n\n"
                         f"<b>Recent Active Sessions:</b>\n{sess_block}",
                )
            except Exception as e:
                logger.warning(f"Failed to send hint to chat {chat_id}: {e}")
        else:
            try:
                await telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    text="ℹ️ To subscribe to live chat messages, send: <code>/auth YOUR_SECRET</code>.",
                )
            except Exception as e:
                logger.warning(f"Failed to send auth prompt to chat {chat_id}: {e}")
        return {"status": "unrecognized_command"}

    # =========================================================================
    # Case B: Admin replying to a visitor message
    # =========================================================================
    reply_msg_id = reply_to.get("message_id")

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT session_id, media_type, original_text, website_name, calling_url, is_replied
            FROM telegram_map
            WHERE telegram_message_id = ? AND (chat_id = ? OR chat_id = 0)
            LIMIT 1;
            """,
            (reply_msg_id, chat_id),
        )
        row = await cursor.fetchone()
        if not row:
            cursor_fb = await db.execute(
                "SELECT session_id, media_type, original_text, website_name, calling_url, is_replied FROM telegram_map WHERE telegram_message_id = ? LIMIT 1;",
                (reply_msg_id,),
            )
            row = await cursor_fb.fetchone()

    if not row:
        logger.warning(f"No active session found for replied Telegram message {reply_msg_id}")
        try:
            await telegram_service.send_message_to_chat(
                chat_id=chat_id,
                text="⚠️ Error: Original session not found or expired.",
            )
        except Exception:
            pass
        return {"status": "session_not_found"}

    session_id = row["session_id"]
    orig_media_type = row["media_type"]
    orig_text = row["original_text"] or ""
    website_name = row["website_name"] or ""
    calling_url = row["calling_url"] or ""

    if not website_name or website_name == "Website":
        async with get_db() as db:
            s_cur = await db.execute("SELECT site_id, website_name, calling_url FROM sessions WHERE id = ?;", (session_id,))
            s_row = await s_cur.fetchone()
            if s_row:
                website_name = s_row["website_name"] or settings.site_names.get(s_row["site_id"]) or s_row["site_id"]
                if not calling_url:
                    calling_url = s_row["calling_url"] or ""

    if not website_name or website_name == "Website":
        website_name = "Live Chat Support"

    now = int(time.time())
    message_uuid = str(uuid.uuid4())

    admin_text = message.get("text") or message.get("caption")
    media_type: Optional[str] = None
    media_url: Optional[str] = None

    if "photo" in message:
        media_type = "photo"
        photo_sizes = message["photo"]
        file_id = photo_sizes[-1]["file_id"]
        media_url = f"/api/v1/media/{file_id}"
    elif "video" in message:
        media_type = "video"
        file_id = message["video"]["file_id"]
        media_url = f"/api/v1/media/{file_id}"
    elif "voice" in message:
        media_type = "audio"
        file_id = message["voice"]["file_id"]
        media_url = f"/api/v1/media/{file_id}"
    elif "audio" in message:
        media_type = "audio"
        file_id = message["audio"]["file_id"]
        media_url = f"/api/v1/media/{file_id}"
    elif "document" in message:
        media_type = "document"
        file_id = message["document"]["file_id"]
        media_url = f"/api/v1/media/{file_id}"

    # 2. Persist admin message in database for the visitor session
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO messages (id, session_id, sender, text, media_type, media_url, created_at)
            VALUES (?, ?, 'admin', ?, ?, ?, ?);
            """,
            (message_uuid, session_id, admin_text, media_type, media_url, now),
        )
        await db.execute(
            "UPDATE telegram_map SET is_replied = 1 WHERE session_id = ?;",
            (session_id,),
        )
        map_cursor = await db.execute(
            "SELECT telegram_message_id, chat_id FROM telegram_map WHERE session_id = ?;",
            (session_id,),
        )
        all_mapped = await map_cursor.fetchall()
        await db.commit()

    # 3. Emoji & Status update on the original Telegram message(s) with Website Name preserved!
    short_session = session_id[:8]
    safe_site = html.escape(website_name)
    safe_url = html.escape(calling_url)
    updated_banner = (
        f"🌐 Website: [<b>{safe_site}</b>]\n"
        f"🔗 Source: <code>{safe_url}</code>\n"
        f"🆔 Session: [<code>{short_session}</code>]\n"
        f"✅ Status: <b>Replied by {agent_tag}</b>\n"
        f"──────────────────\n"
        f"{orig_text}"
    )
    for mapped in all_mapped:
        m_id = mapped["telegram_message_id"]
        c_id = mapped["chat_id"]
        if c_id != 0:
            await telegram_service.set_message_reaction(chat_id=c_id, message_id=m_id, emoji="✅")
            if orig_media_type in ["photo", "video", "audio", "document"]:
                await telegram_service.edit_message_caption(chat_id=c_id, message_id=m_id, new_caption=updated_banner)
            else:
                await telegram_service.edit_message_text(chat_id=c_id, message_id=m_id, new_text=updated_banner)

    # 4. Multi-agent Broadcast: notify all OTHER subscribed admins displaying website name
    other_admins = [c for c in await get_active_admin_chats() if c != chat_id]
    sync_notice = (
        f"💬 <b>[{agent_tag} replied on {safe_site}]</b>\n"
        f"🌐 Website: [<b>{safe_site}</b>]\n"
        f"🔗 Source: <code>{safe_url}</code>\n"
        f"🆔 Session: [<code>{short_session}</code>]\n"
        f"──────────────────\n"
        f"{admin_text or '[Media attachment]'}"
    )
    for other_chat in other_admins:
        try:
            peer_tg_id = await telegram_service.send_message_to_chat(chat_id=other_chat, text=sync_notice)
            if peer_tg_id:
                async with get_db() as db:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO telegram_map (telegram_message_id, chat_id, session_id, media_type, original_text, website_name, calling_url, is_replied, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?);
                        """,
                        (peer_tg_id, int(other_chat) if str(other_chat).lstrip("-").isdigit() else 0, session_id, None, admin_text, website_name, calling_url, now),
                    )
                    await db.commit()
        except Exception as e:
            logger.warning(f"Failed to sync admin reply to admin chat {other_chat}: {e}")

    return {"status": "ok", "message_id": message_uuid}
