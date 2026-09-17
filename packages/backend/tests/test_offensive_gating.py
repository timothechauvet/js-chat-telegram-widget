import os
import tempfile
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

# Ensure test uses an isolated temporary database directory
temp_data_dir = tempfile.mkdtemp()
os.environ["DATA_DIR"] = temp_data_dir
os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:MOCK_TEST_BOT_TOKEN_ABCXYZ"
os.environ["TELEGRAM_ADMIN_CHAT_ID"] = "1001"
os.environ["TELEGRAM_AUTH_SECRET"] = "admin-secret-key-123"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "super-webhook-secret-token"

from app.config import settings
from app.main import app
from app.database import init_db, get_db
from app.telegram import telegram_service


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    yield


@pytest.mark.asyncio
async def test_telegram_admin_auth_and_status():
    """Tests admin registration via /auth, command parsing, /status, and /deauth."""
    transport = ASGITransport(app=app)

    with patch.object(telegram_service, "send_message_to_chat", new=AsyncMock(return_value=111)) as mock_send:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM_WEBHOOK_SECRET}

            # 1. Unknown user sends invalid secret
            fail_payload = {
                "update_id": 1,
                "message": {
                    "message_id": 10,
                    "chat": {"id": 99901},
                    "from": {"id": 99901, "username": "bad_actor"},
                    "text": "/auth wrong-password",
                },
            }
            res = await client.post("/api/v1/telegram-webhook", headers=headers, json=fail_payload)
            assert res.status_code == 200
            assert res.json()["status"] == "auth_failed"

            # 2. Legitimate admin sends correct /auth
            auth_payload = {
                "update_id": 2,
                "message": {
                    "message_id": 11,
                    "chat": {"id": 99901},
                    "from": {"id": 99901, "username": "support_hero", "first_name": "Hero"},
                    "text": f"/auth {settings.TELEGRAM_AUTH_SECRET}",
                },
            }
            res = await client.post("/api/v1/telegram-webhook", headers=headers, json=auth_payload)
            assert res.status_code == 200
            assert res.json()["status"] == "authenticated"

            # Verify admin is stored in admin_subscribers
            async with get_db() as db:
                cursor = await db.execute("SELECT * FROM admin_subscribers WHERE chat_id = 99901;")
                admin_row = await cursor.fetchone()
                assert admin_row is not None
                assert admin_row["username"] == "support_hero"

            # 3. Check /status
            status_payload = {
                "update_id": 3,
                "message": {
                    "message_id": 12,
                    "chat": {"id": 99901},
                    "from": {"id": 99901, "username": "support_hero"},
                    "text": "/status",
                },
            }
            res = await client.post("/api/v1/telegram-webhook", headers=headers, json=status_payload)
            assert res.status_code == 200
            assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_multi_admin_broadcast_and_emoji_update():
    """Tests that visitor messages broadcast to all admins, and admin answers sync with emoji status updates."""
    transport = ASGITransport(app=app)
    session_id = "test-session-multi-admin-xyz"

    # Pre-seed two authenticated admins: Admin1 (chat 8001) and Admin2 (chat 8002)
    async with get_db() as db:
        await db.execute("INSERT OR REPLACE INTO admin_subscribers (chat_id, username, first_name, authenticated_at) VALUES (8001, 'admin_one', 'One', 1000);")
        await db.execute("INSERT OR REPLACE INTO admin_subscribers (chat_id, username, first_name, authenticated_at) VALUES (8002, 'admin_two', 'Two', 1000);")
        await db.commit()

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_message", new=AsyncMock(side_effect=[5001, 5002, 5003])) as mock_send, \
         patch.object(telegram_service, "send_message_to_chat", new=AsyncMock(return_value=999)) as mock_send_to_chat, \
         patch.object(telegram_service, "set_message_reaction", new=AsyncMock(return_value=True)) as mock_reaction, \
         patch.object(telegram_service, "edit_message_text", new=AsyncMock(return_value=True)) as mock_edit_text:

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Visitor sends a message -> should broadcast to admins
            res = await client.post(
                "/api/v1/send",
                headers={"Authorization": f"Bearer {session_id}"},
                data={"site_id": "store-us", "text": "Need urgent refund!"},
            )
            assert res.status_code == 200

            # Verify both admin mappings exist in telegram_map
            async with get_db() as db:
                cursor = await db.execute("SELECT * FROM telegram_map WHERE session_id = ?;", (session_id,))
                mapped_rows = await cursor.fetchall()
                assert len(mapped_rows) >= 2

            # 2. Admin 1 (chat 8001) replies to message 5001
            reply_payload = {
                "update_id": 50,
                "message": {
                    "message_id": 6001,
                    "chat": {"id": 8001},
                    "from": {"id": 8001, "username": "admin_one"},
                    "reply_to_message": {"message_id": 5001},
                    "text": "Refund approved and processed! ✅",
                },
            }
            wh_res = await client.post(
                "/api/v1/telegram-webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM_WEBHOOK_SECRET},
                json=reply_payload,
            )
            assert wh_res.status_code == 200
            assert wh_res.json()["status"] == "ok"

            sync_calls = [c for c in mock_send_to_chat.call_args_list if c.kwargs.get("chat_id") == 8002]
            assert len(sync_calls) >= 1
            sync_text = sync_calls[0].kwargs["text"]
            assert "💬 <b>[@admin_one replied on Store Us]</b>" in sync_text
            assert "🌐 Website: [<b>Store Us</b>]" in sync_text
            assert "Refund approved and processed! ✅" in sync_text

            # 3. Visitor fetches messages and receives Admin 1's reply
            msgs_res = await client.get("/api/v1/messages", headers={"Authorization": f"Bearer {session_id}"})
            msgs = msgs_res.json()
            assert len(msgs) == 2
            assert msgs[1]["sender"] == "admin"
            assert "Refund approved" in msgs[1]["text"]


@pytest.mark.asyncio
async def test_offensive_idor_cross_session_message_snoop():
    """Attacker attempts to query or leak messages belonging to a victim's session."""
    transport = ASGITransport(app=app)
    alice_session = "alice-session-secret-999"
    bob_session = "bob-attacker-session-111"

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_message", new=AsyncMock(return_value=12345)):

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Alice posts confidential data
            await client.post(
                "/api/v1/send",
                headers={"Authorization": f"Bearer {alice_session}"},
                data={"site_id": "finance", "text": "Top secret financial statement 2026"},
            )

            # Bob queries messages with Bob's token
            bob_res = await client.get(
                "/api/v1/messages",
                headers={"Authorization": f"Bearer {bob_session}"},
            )
            assert bob_res.status_code == 200
            bob_msgs = bob_res.json()
            assert len(bob_msgs) == 0  # Zero leakage of Alice's messages

            # Bob tries query tampering with session_id parameter
            bob_tamper_res = await client.get(
                f"/api/v1/messages?session_id={alice_session}",
                headers={"Authorization": f"Bearer {bob_session}"},
            )
            assert bob_tamper_res.status_code == 200
            assert len(bob_tamper_res.json()) == 0


@pytest.mark.asyncio
async def test_offensive_idor_cross_session_media_theft():
    """Attacker attempts to download an attachment belonging to another visitor session."""
    transport = ASGITransport(app=app)
    alice_session = "alice-confidential-session-777"
    bob_session = "bob-attacker-session-222"

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_media", new=AsyncMock(return_value=(99001, "photo"))):

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Alice uploads an image
            fake_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            alice_send = await client.post(
                "/api/v1/send",
                headers={"Authorization": f"Bearer {alice_session}"},
                data={"site_id": "secure-docs", "text": "Passport copy"},
                files={"file": ("passport.png", fake_image_bytes, "image/png")},
            )
            assert alice_send.status_code == 200

            # Alice gets her message and media_url
            alice_msgs = (await client.get("/api/v1/messages", headers={"Authorization": f"Bearer {alice_session}"})).json()
            media_url = alice_msgs[0]["media_url"]
            file_id = media_url.replace("/api/v1/media/", "")

            # Alice can access her file
            alice_file_res = await client.get(f"/api/v1/media/{file_id}", headers={"Authorization": f"Bearer {alice_session}"})
            assert alice_file_res.status_code == 200

            # Bob (Attacker) tries to access Alice's file_id using Bob's Bearer token
            bob_file_res = await client.get(f"/api/v1/media/{file_id}", headers={"Authorization": f"Bearer {bob_session}"})
            assert bob_file_res.status_code == 404  # Strictly rejected (unauthorized for Bob)

            # Bob tries using Bob's cookie
            bob_cookie_res = await client.get(f"/api/v1/media/{file_id}", cookies={"tg_chat_token": bob_session})
            assert bob_cookie_res.status_code == 404


@pytest.mark.asyncio
async def test_offensive_path_traversal_defense():
    """Attacker attempts path traversal tricks to read arbitrary files or upload executables."""
    transport = ASGITransport(app=app)
    session_id = "attacker-traversal-session"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Attempt to download /etc/passwd via media endpoint
        traversal_res1 = await client.get(
            "/api/v1/media/../../../../etc/passwd",
            headers={"Authorization": f"Bearer {session_id}"},
        )
        assert traversal_res1.status_code in [404, 400]

        # 2. Attempt URL encoded path traversal
        traversal_res2 = await client.get(
            "/api/v1/media/..%2f..%2f..%2fdata%2fchat.db",
            headers={"Authorization": f"Bearer {session_id}"},
        )
        assert traversal_res2.status_code in [404, 400]

        # 3. Attempt to upload dangerous executable file (.exe, .sh, .php)
        bad_upload_res = await client.post(
            "/api/v1/send",
            headers={"Authorization": f"Bearer {session_id}"},
            data={"site_id": "test", "text": "shell upload"},
            files={"file": ("../../reverse_shell.sh", b"#!/bin/sh\necho pwned", "application/x-sh")},
        )
        assert bad_upload_res.status_code == 400
        assert "not permitted for security reasons" in bad_upload_res.json()["detail"]


@pytest.mark.asyncio
async def test_offensive_webhook_forgery_defense():
    """Attacker attempts to forge Telegram webhooks without valid secret token."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request without header
        no_header_res = await client.post(
            "/api/v1/telegram-webhook",
            json={"update_id": 999, "message": {"text": "spoofed"}},
        )
        assert no_header_res.status_code == 403

        # Request with forged header
        wrong_header_res = await client.post(
            "/api/v1/telegram-webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "hacker-guessed-token"},
            json={"update_id": 999, "message": {"text": "spoofed"}},
        )
        assert wrong_header_res.status_code == 403


@pytest.mark.asyncio
async def test_offensive_rate_limiting_defense():
    """Attacker attempts to flood the gateway with spam."""
    transport = ASGITransport(app=app)
    session_id = "spammer-session-rate-limit-test"

    with patch.object(telegram_service, "send_chat_action", new=AsyncMock()), \
         patch.object(telegram_service, "send_message", new=AsyncMock(return_value=99999)):

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            statuses = []
            for i in range(35):
                res = await client.post(
                    "/api/v1/send",
                    headers={"Authorization": f"Bearer {session_id}"},
                    data={"site_id": "spam-site", "text": f"Spam message {i}"},
                )
                statuses.append(res.status_code)

            # First 30 should succeed, subsequent ones blocked with 429
            assert 200 in statuses
            assert 429 in statuses
            assert statuses[-1] == 429
