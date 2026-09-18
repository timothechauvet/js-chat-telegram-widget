import os
import tempfile
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

# Ensure test uses a clean temporary database directory
temp_data_dir = tempfile.mkdtemp()
os.environ["DATA_DIR"] = temp_data_dir
os.environ["TELEGRAM_BOT_TOKEN"] = "mock_token"
os.environ["TELEGRAM_ADMIN_CHAT_ID"] = "12345"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test_secret"
os.environ["SITE_NAMES_MAPPING"] = '{"http://localhost:5173": "Local Demo Store"}'

from app.main import app
from app.database import init_db
from app.telegram import telegram_service


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    yield


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
        assert res.json()["version"] == "1.2.0"


@pytest.mark.asyncio
async def test_status_endpoint_always_online():
    transport = ASGITransport(app=app)
    session_id = "test-session-status-online"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/status",
            headers={"Authorization": f"Bearer {session_id}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_online"] is True
        assert data["is_night"] is False



@pytest.mark.asyncio
async def test_webhook_status_endpoint():
    transport = ASGITransport(app=app)
    with patch.object(telegram_service, "get_webhook_info", new=AsyncMock(return_value={"url": "https://example.com/webhook"})):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/webhook-status")
            assert res.status_code == 200
            data = res.json()
            assert data["configured"] is True
            assert data["telegram_info"]["url"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_send_and_retrieve_messages():
    transport = ASGITransport(app=app)
    session_id = "test-session-1234-uuid"

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_message", new=AsyncMock(return_value=99999)):

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send message
            send_res = await client.post(
                "/api/v1/send",
                headers={"Authorization": f"Bearer {session_id}"},
                data={"site_id": "test-site", "text": "Hello world!"},
            )
            assert send_res.status_code == 200
            data = send_res.json()
            assert data["status"] == "ok"
            assert "message_id" in data

            # Retrieve messages for this session
            get_res = await client.get(
                "/api/v1/messages",
                headers={"Authorization": f"Bearer {session_id}"},
            )
            assert get_res.status_code == 200
            messages = get_res.json()
            assert len(messages) == 1
            assert messages[0]["text"] == "Hello world!"
            assert messages[0]["sender"] == "visitor"

            # Verify session isolation: another session gets 0 messages
            other_res = await client.get(
                "/api/v1/messages",
                headers={"Authorization": "Bearer other-session-5678"},
            )
            assert other_res.status_code == 200
            assert len(other_res.json()) == 0


@pytest.mark.asyncio
async def test_telegram_webhook_reply():
    transport = ASGITransport(app=app)
    session_id = "test-session-webhook-abc"

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_message", new=AsyncMock(return_value=88888)):

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Visitor sends a message mapping tg_id 88888 -> session_id
            await client.post(
                "/api/v1/send",
                headers={"Authorization": f"Bearer {session_id}"},
                data={"site_id": "test-site", "text": "Inquiry"},
            )

            # 2. Telegram webhook delivers admin reply to msg 88888
            webhook_payload = {
                "update_id": 100,
                "message": {
                    "message_id": 88889,
                    "reply_to_message": {
                        "message_id": 88888,
                    },
                    "text": "Admin reply here!",
                },
            }

            wh_res = await client.post(
                "/api/v1/telegram-webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
                json=webhook_payload,
            )
            assert wh_res.status_code == 200
            assert wh_res.json()["status"] == "ok"

            # 3. Visitor fetches messages and receives admin reply
            msgs_res = await client.get(
                "/api/v1/messages",
                headers={"Authorization": f"Bearer {session_id}"},
            )
            msgs = msgs_res.json()
            assert len(msgs) == 2
            assert msgs[1]["sender"] == "admin"
            assert msgs[1]["text"] == "Admin reply here!"


@pytest.mark.asyncio
async def test_cookie_persistence_and_auth():
    transport = ASGITransport(app=app)
    session_id = "test-cookie-session-uuid"

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_message", new=AsyncMock(side_effect=[77777, 77778])):

        # 1. Send message with Bearer token, verify cookie is set in response
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            send_res = await client.post(
                "/api/v1/send",
                headers={"Authorization": f"Bearer {session_id}"},
                data={"site_id": "test-site", "text": "Testing cookie setup"},
            )
            assert send_res.status_code == 200
            assert "tg_chat_token" in send_res.cookies
            assert send_res.cookies["tg_chat_token"] == session_id

        # 2. In a brand new client with ONLY the cookie and NO Authorization header, fetch messages
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"tg_chat_token": session_id}) as cookie_client:
            cookie_get_res = await cookie_client.get("/api/v1/messages")
            assert cookie_get_res.status_code == 200
            msgs = cookie_get_res.json()
            assert len(msgs) >= 1
            assert msgs[0]["text"] == "Testing cookie setup"

            # 3. Send message using ONLY cookie authentication
            cookie_send_res = await cookie_client.post(
                "/api/v1/send",
                data={"site_id": "test-site", "text": "Cookie authenticated message"},
            )
            assert cookie_send_res.status_code == 200
            assert cookie_send_res.json()["status"] == "ok"

            # 4. Verify both messages are present
            all_msgs = await cookie_client.get("/api/v1/messages")
            assert len(all_msgs.json()) == 2


@pytest.mark.asyncio
async def test_website_name_resolution_and_display():
    transport = ASGITransport(app=app)
    session_id = "test-session-site-name-resolution"

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_message", new=AsyncMock(return_value=123456)) as mock_send, \
         patch.object(telegram_service, "edit_message_text", new=AsyncMock(return_value=True)) as mock_edit, \
         patch.object(telegram_service, "set_message_reaction", new=AsyncMock(return_value=True)) as mock_react:

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Calling from frontend URL http://localhost:5173 with page_url
            send_res = await client.post(
                "/api/v1/send",
                headers={
                    "Authorization": f"Bearer {session_id}",
                    "Origin": "http://localhost:5173",
                },
                data={
                    "site_id": "demo-site",
                    "page_url": "http://localhost:5173/shop/products?item=42",
                    "page_title": "Interactive Demo Store",
                    "text": "Do you have this in size 42?",
                },
            )
            assert send_res.status_code == 200

            # Verify dispatched Telegram message contains configured website name
            assert mock_send.called
            dispatched_text = mock_send.call_args_list[0][0][0]
            assert "🌐 Website: [<b>Local Demo Store</b>]" in dispatched_text
            assert "🔗 Source: <code>http://localhost:5173/shop/products</code>" in dispatched_text
            assert "⏳ Status: <b>Pending Reply</b>" in dispatched_text
            assert "Do you have this in size 42?" in dispatched_text

            # 2. Admin replies -> verify edited message PRESERVES website name and URL!
            reply_payload = {
                "update_id": 99,
                "message": {
                    "message_id": 9999,
                    "chat": {"id": 12345},
                    "from": {"id": 12345, "username": "SupportAgent"},
                    "reply_to_message": {"message_id": 123456},
                    "text": "Yes, size 42 is in stock!",
                },
            }
            wh_res = await client.post(
                "/api/v1/telegram-webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
                json=reply_payload,
            )
            assert wh_res.status_code == 200

            # Verify edit_message_text was called with the preserved website name
            assert mock_edit.called
            edited_text = mock_edit.call_args.kwargs["new_text"]
            assert "🌐 Website: [<b>Local Demo Store</b>]" in edited_text
            assert "🔗 Source: <code>http://localhost:5173/shop/products</code>" in edited_text
            assert "✅ Status: <b>Replied by @SupportAgent</b>" in edited_text
            assert "Do you have this in size 42?" in edited_text
            assert mock_react.called


