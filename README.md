# Telegram Live Chat Widget & Gateway

A lightweight, multi-tenant live chat system that connects visitors directly to a Telegram bot or group. Built for zero-dependency embedding on client sites with a secure, dockerized Python gateway.

- **Frontend Widget (`packages/widget`)**: Zero-dependency Web Component (`<telegram-chat-widget>`) packaged with Shadow DOM isolation, multi-line expandable composer, custom avatars, sound notifications, and full mobile viewport responsiveness.
- **Backend Gateway (`packages/backend`)**: Async FastAPI service handling bi-directional Telegram bridging (Webhook and long-polling modes), session tokens, media streaming, anti-spam throttling, and message lifecycle pruning.

---

## Quick Start (Local Development)

The project includes a unified `Makefile` for local development and testing:

```bash
# Start both backend and frontend concurrently
make dev
```

*(Alternatively, run `npm start` from the project root).*

### Available Commands

| Command | Description |
|---|---|
| `make dev` | Launches backend (`:8000`) and frontend demo (`:5173`) concurrently |
| `make backend` | Starts only the FastAPI backend with hot-reload |
| `make frontend` | Starts only the Vite widget demo |
| `make test` | Runs backend `pytest` and widget `vitest` suites |
| `make build` | Compiles the widget production bundle to `packages/widget/dist` |
| `make clean` | Removes build artifacts, caches, and virtual environments |

When running `make dev`:
- **Widget Demo**: [http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- **FastAPI Backend**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## System Architecture

```text
Visitor Browser (<telegram-chat-widget>)
       │
       ▼ (HTTP / Cookie / Session Token)
FastAPI Backend Gateway (:8000)
  ├── SQLite Database (Encrypted Session Store)
  ├── Retention Pruner (Auto-cleanup after N hours)
  └── Rate Limiter (In-memory per session)
       │
       ▼ (HTTPS Webhook or Polling)
Telegram Bot API
       │
       ▼
Support Team (Telegram Chat / Group)
```

---

## 1. Telegram Bot Setup

1. **Create Bot**: Open Telegram, chat with [@BotFather](https://t.me/BotFather), run `/newbot`, and save your API token.
2. **Get Chat ID**:
   - For direct messaging: start the bot, then send a message to [@userinfobot](https://t.me/userinfobot) to get your numerical chat ID.
   - For a support group: add the bot to your group and grant message permissions. Group chat IDs begin with `-100`.
3. **Configure Webhook** (Production):
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{
          "url": "https://chat.yourdomain.com/api/v1/telegram-webhook",
          "secret_token": "your-secure-webhook-secret"
        }'
   ```
   *(For local development, set `TELEGRAM_POLLING_MODE=true` in `.env` to receive updates without tunnels).*

---

## 2. Backend Deployment

### Docker Compose

```yaml
services:
  telegram-chat-backend:
    image: ghcr.io/timothechauvet/js-chat-telegram-widget-backend:latest
    container_name: tg-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - chat_data:/data

volumes:
  chat_data:
```

### Environment Configuration (`.env`)

```env
TELEGRAM_BOT_TOKEN="your-bot-token-from-botfather"
TELEGRAM_ADMIN_CHAT_ID="your-chat-or-group-id"
TELEGRAM_WEBHOOK_SECRET="random-string-for-webhook-auth"
TELEGRAM_AUTH_SECRET="secret-for-admin-commands"
BACKEND_SECRET_KEY="internal-token-for-admin"
HISTORY_RETENTION_HOURS=72
MAX_UPLOAD_SIZE_MB=25
CORS_ALLOW_ORIGINS="*"
DATA_DIR="/data"
TELEGRAM_POLLING_MODE=false

# Optional: Map incoming origin URLs/hostnames to friendly website labels
SITE_NAMES_MAPPING='{"http://localhost:5173": "Demo Store", "example.com": "Production Store"}'
```

---

## 3. Frontend Widget Integration

### Installation via npm

```bash
npm install js-chat-telegram-widget
```

### Static HTML / Script Tag

```html
<script type="module" src="https://unpkg.com/js-chat-telegram-widget/dist/index.mjs"></script>

<telegram-chat-widget
  backend-url="https://chat.yourdomain.com"
  site-id="my-site"
  primary-color="#151946"
  accent-color="#7C170D"
  bg-color="#EBE1D5"
  title="Customer Support"
  placeholder="Write a message..."
  poll-interval="3000">
</telegram-chat-widget>
```

### Framework Integration (React / Next.js)

```tsx
import { useEffect } from 'react';

export default function LiveChat() {
  useEffect(() => {
    import('js-chat-telegram-widget');
  }, []);

  return (
    // @ts-ignore
    <telegram-chat-widget
      backend-url="https://chat.yourdomain.com"
      site-id="react-storefront"
    />
  );
}
```

---

## 4. Widget Custom Element API

### HTML Attributes

| Attribute | Type | Default | Description |
|---|---|---|---|
| `backend-url` | String | `""` | Base URL of the deployed FastAPI service |
| `site-id` | String | Hostname | Site identifier attached to session headers |
| `primary-color` | Hex/CSS | `#151946` | Header background, launcher color, visitor bubble |
| `accent-color` | Hex/CSS | `#7C170D` | Action buttons, badges, drag-and-drop borders |
| `bg-color` | Hex/CSS | `#EBE1D5` | Message canvas background |
| `font-family` | String | System font | Custom typography font-family |
| `font-url` | String | None | Optional Google Fonts stylesheet URL |
| `title` | String | `Chat with us` | Chat card header title |
| `placeholder` | String | `Write a message...`| Composer placeholder text |
| `poll-interval` | Number | `3000` | Polling frequency in milliseconds |
| `profile-pic` | URL | Default Avatar | Custom image URL for launcher button and header |
| `avatar-url` | URL | Default Avatar | Alias for `profile-pic` |
| `chime-url` | URL | Embedded Audio | Custom audio URL for message arrival notifications |

---

## 5. Security & Isolation

- **Session Partitioning**: Every visitor receives a cryptographically generated UUID stored in both `localStorage` and `SameSite=Lax` cookies. SQL queries filter exclusively by `session_id = :visitor_token`.
- **Media Access Control**: Telegram bot tokens are never sent to the client. File attachments and media downloads are proxied through `/api/v1/media/{id}` after verifying the requesting session's ownership.
- **Anti-Spam Throttling**: Built-in sliding window rate limiting (default: 30 requests/minute per session).
- **Safe HTML Rendering**: All message text is escaped before insertion; line breaks are preserved with CSS `white-space: pre-wrap` on `.tg-bubble-text` without HTML injection risks.
- **Automated Pruning**: Background scheduler removes messages and media files exceeding `HISTORY_RETENTION_HOURS`.

---

## 6. CI/CD & Automated Publishing

The repository includes GitHub Actions workflows configured for release tags (`v*.*.*`):

1. **`.github/workflows/publish-widget.yml`**:
   - Builds TypeScript distribution (`dist/index.mjs`, `dist/index.js`, `dist/index.d.ts`).
   - Runs full Vitest suite.
   - Publishes `js-chat-telegram-widget` to the npm registry using `NPM_TOKEN`.
2. **`.github/workflows/publish-backend.yml`**:
   - Builds production Docker image using multi-stage non-root container.
   - Pushes to GitHub Container Registry (`ghcr.io/<owner>/js-chat-telegram-widget-backend`).

---

## Acknowledgements

- Architecture and code developed with assistance from **Gemini**.
- UI animation heuristics, micro-interactions, and mobile responsiveness benchmarked with **Appllama**.

---

## License

MIT
