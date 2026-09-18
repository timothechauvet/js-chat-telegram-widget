import httpx
import logging
from typing import Any, Optional
from .config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN.strip('"').strip("'").strip()
        self.default_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID.strip('"').strip("'").strip()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.file_url = f"https://api.telegram.org/file/bot{self.bot_token}"

    async def send_chat_action(self, action: str = "typing", chat_id: Optional[int | str] = None) -> None:
        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.post(
                    f"{self.base_url}/sendChatAction",
                    json={"chat_id": target_chat, "action": action},
                )
            except Exception as e:
                logger.warning(f"Failed to sendChatAction to Telegram: {e}")

    async def send_message_to_chat(self, chat_id: int | str, text: str, parse_mode: str = "HTML") -> int:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
            )
            data = res.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram sendMessage failed for chat {chat_id}: {data.get('description')}")
            return data["result"]["message_id"]

    async def send_message(self, text: str, chat_id: Optional[int | str] = None) -> int:
        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            raise RuntimeError("No Telegram admin chat_id available to receive message.")
        return await self.send_message_to_chat(target_chat, text)

    async def send_media_to_chat(
        self,
        chat_id: int | str,
        media_bytes: bytes,
        filename: str,
        content_type: str,
        caption: str = "",
    ) -> tuple[int, str]:
        """Dispatches media file to appropriate Telegram Bot API method."""
        method = "sendDocument"
        field_name = "document"
        media_type = "document"

        if content_type.startswith("image/"):
            method = "sendPhoto"
            field_name = "photo"
            media_type = "photo"
        elif content_type.startswith("video/"):
            method = "sendVideo"
            field_name = "video"
            media_type = "video"
        elif content_type.startswith("audio/"):
            method = "sendAudio"
            field_name = "audio"
            media_type = "audio"

        files = {field_name: (filename, media_bytes, content_type)}
        data: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{self.base_url}/{method}",
                data=data,
                files=files,
            )
            res_data = res.json()
            if not res_data.get("ok"):
                raise RuntimeError(f"Telegram {method} failed for chat {chat_id}: {res_data.get('description')}")
            return res_data["result"]["message_id"], media_type

    async def send_media(
        self,
        media_bytes: bytes,
        filename: str,
        content_type: str,
        caption: str = "",
        chat_id: Optional[int | str] = None,
    ) -> tuple[int, str]:
        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            raise RuntimeError("No Telegram admin chat_id available to receive media.")
        return await self.send_media_to_chat(target_chat, media_bytes, filename, content_type, caption)

    async def edit_message_text(self, chat_id: int | str, message_id: int, new_text: str, parse_mode: str = "HTML") -> bool:
        """Edits an existing text message."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/editMessageText",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "text": new_text,
                        "parse_mode": parse_mode,
                    },
                )
                data = res.json()
                return bool(data.get("ok"))
            except Exception as e:
                logger.warning(f"Failed to edit Telegram message {message_id} in chat {chat_id}: {e}")
                return False

    async def edit_message_caption(self, chat_id: int | str, message_id: int, new_caption: str, parse_mode: str = "HTML") -> bool:
        """Edits an existing media caption."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/editMessageCaption",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "caption": new_caption,
                        "parse_mode": parse_mode,
                    },
                )
                data = res.json()
                return bool(data.get("ok"))
            except Exception as e:
                logger.warning(f"Failed to edit Telegram caption {message_id} in chat {chat_id}: {e}")
                return False

    async def set_message_reaction(self, chat_id: int | str, message_id: int, emoji: str = "✅") -> bool:
        """Sets an emoji reaction on a message in Telegram."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/setMessageReaction",
                    json={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "reaction": [{"type": "emoji", "emoji": emoji}],
                    },
                )
                data = res.json()
                return bool(data.get("ok"))
            except Exception as e:
                logger.warning(f"Failed to set Telegram message reaction {message_id} in chat {chat_id}: {e}")
                return False

    async def get_file_path(self, file_id: str) -> str:
        """Retrieves Telegram file_path using getFile."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(
                f"{self.base_url}/getFile",
                params={"file_id": file_id},
            )
            data = res.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram getFile failed: {data.get('description')}")
            return data["result"]["file_path"]

    async def stream_file(self, file_path: str):
        """Streams file content from Telegram without exposing bot token."""
        url = f"{self.file_url}/{file_path}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Telegram file stream failed with code {response.status_code}")
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 10) -> list[dict[str, Any]]:
        """Polls Telegram Bot API getUpdates for new messages/actions."""
        params: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        async with httpx.AsyncClient(timeout=timeout + 5.0) as client:
            try:
                res = await client.get(f"{self.base_url}/getUpdates", params=params)
                data = res.json()
                if data.get("ok"):
                    return data.get("result", [])
                else:
                    logger.warning(f"Telegram getUpdates returned error: {data.get('description')}")
            except Exception as e:
                logger.warning(f"Failed to fetch getUpdates from Telegram: {e}")
            return []


    async def set_webhook(self, url: str, secret_token: Optional[str] = None, drop_pending_updates: bool = False) -> bool:
        """Configures Telegram Bot API webhook."""
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN is not configured; skipping setWebhook.")
            return False
        payload: dict[str, Any] = {
            "url": url,
            "drop_pending_updates": drop_pending_updates,
        }
        if secret_token:
            payload["secret_token"] = secret_token
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.post(f"{self.base_url}/setWebhook", json=payload)
                data = res.json()
                if not data.get("ok"):
                    logger.error(f"Failed to set Telegram webhook to {url}: {data.get('description')}")
                    return False
                logger.info(f"Telegram webhook successfully registered to {url}")
                return True
            except Exception as e:
                logger.error(f"Exception setting Telegram webhook: {e}")
                return False

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        """Deletes Telegram Bot API webhook."""
        if not self.bot_token:
            return False
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/deleteWebhook",
                    json={"drop_pending_updates": drop_pending_updates},
                )
                data = res.json()
                return bool(data.get("ok"))
            except Exception as e:
                logger.warning(f"Failed to delete webhook: {e}")
                return False

    async def get_webhook_info(self) -> dict[str, Any]:
        """Fetches current webhook status from Telegram."""
        if not self.bot_token:
            return {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(f"{self.base_url}/getWebhookInfo")
                data = res.json()
                if data.get("ok"):
                    return data.get("result", {})
            except Exception as e:
                logger.warning(f"Failed to fetch getWebhookInfo: {e}")
            return {}


telegram_service = TelegramService()
