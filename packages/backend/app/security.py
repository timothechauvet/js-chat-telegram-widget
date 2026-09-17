import re
import time
from collections import defaultdict
from typing import Optional
from fastapi import Header, HTTPException, Request, status

RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30     # max requests per window
_rate_limits: dict[str, list[float]] = defaultdict(list)


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename and blocks path traversal attempts."""
    clean = re.sub(r'[^\w\.-]', '_', filename)
    clean = clean.lstrip('.').replace('..', '_')
    if not clean:
        clean = "attachment"
    return clean


def is_extension_safe(filename: str) -> bool:
    """Rejects dangerous executables and scripts."""
    dangerous = {
        '.exe', '.bat', '.cmd', '.sh', '.bash', '.bin', '.dll',
        '.so', '.com', '.msi', '.vbs', '.js', '.mjs', '.php'
    }
    ext = re.search(r'\.[a-zA-Z0-9]+$', filename.lower())
    if ext and ext.group(0) in dangerous:
        return False
    return True


def verify_session_token(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> str:
    """Extracts and validates session token from Authorization header or cookies."""
    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        # Fallback to cookie persistence
        for cookie_name, cookie_val in request.cookies.items():
            if (cookie_name == "tg_chat_token" or cookie_name.startswith("tg_chat_token_")) and cookie_val:
                token = cookie_val.strip()
                break

    if not token:
        # Fallback to query parameter (needed for <img>, <video>, <audio>, <a> media streams)
        query_token = request.query_params.get("token")
        if query_token:
            token = query_token.strip()

    if not token or len(token) > 128:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed session token",
        )
    return token


def check_rate_limit(session_id: str) -> None:
    """In-memory rate limiter: 30 requests per minute per session."""
    now = time.time()
    timestamps = _rate_limits[session_id]
    _rate_limits[session_id] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]

    if len(_rate_limits[session_id]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending more messages.",
        )

    _rate_limits[session_id].append(now)
