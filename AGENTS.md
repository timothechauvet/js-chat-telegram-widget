# AGENTS.md - Repository Guide for AI Agents & Developers

This document provides a comprehensive, exhaustive technical reference for AI agents and developers working on the `js-chat-telegram-widget` repository. Consult this file to understand the architecture, design choices, file locations, data flows, security rules, and testing workflows.

---

## 1. System Mission & Core Philosophy

The repository implements a production-grade, multi-tenant live chat system connecting static or dynamic websites directly to a Telegram Bot/Chat.

### Key Pillars:
1. **Zero-Dependency Frontend Widget (`packages/widget`)**:
   - Native Web Component (`<telegram-chat-widget>`) packaged with Shadow DOM isolation.
   - Framework-agnostic: embeds into HTML, React, Next.js, Vue, Nuxt, Svelte, Angular, Hugo, Jekyll, WordPress, or Shopify.
   - Auto-growing multiline composer (120px max height limit), responsive mobile sheet (`100dvh`), custom support agent avatars, and embedded audio chime notifications.
2. **Fast Async Backend Gateway (`packages/backend`)**:
   - FastAPI + Uvicorn + aiosqlite acting as an encrypted reverse proxy and bridge to Telegram Bot API.
   - Dual-mode operation: Webhook mode (production HTTPS) and Autonomous Long-Polling mode (tunnel-free local dev).
   - Multi-tenant site origin detection: maps visitor page URLs to friendly store/site names.
   - Strict session isolation, anti-spam rate limiting, authenticated media streaming, and background retention pruning.
3. **Enterprise Kubernetes Deployment (`k8s/`)**:
   - Complete production Kubernetes manifests (Namespace, Deployment, Service, Ingress with cert-manager TLS, PVC, ConfigMap, and Kustomization).

---

## 2. Exhaustive Directory & File Map

```text
.
├── .github/
│   └── workflows/
│       ├── publish-backend.yml       # GitHub Actions: builds Docker container & pushes to GHCR
│       └── publish-widget.yml        # GitHub Actions: runs vitest, builds bundle & publishes to npm
├── .gitignore                        # Global ignore: .env, data/, node_modules/, dist/, venvs
├── Makefile                          # Unified task runner (make dev, test, build, clean)
├── package.json                      # Workspace root package definition
├── README.md                         # Developer-facing overview, API docs, and setup instructions
├── AGENTS.md                         # This file: exhaustive internal documentation for agents
├── k8s/                              # Kubernetes production manifests
│   ├── namespace.yaml                # Namespace: telegram-chat
│   ├── deployment.yaml               # Deployment with health checks, resource limits & securityContext
│   ├── service.yaml                  # ClusterIP service exposing port 8000
│   ├── ingress.yaml                  # Ingress with TLS & cert-manager annotations
│   ├── pvc.yaml                      # PersistentVolumeClaim for /data SQLite storage
│   ├── configmap.yaml                # Non-sensitive runtime configuration
│   ├── secret.example.yaml           # Template for Telegram bot tokens and secrets (real secret.yaml is gitignored)
│   ├── kustomization.yaml            # Kustomize aggregation
│   └── README.md                     # Kubernetes deployment guide
├── packages/
│   ├── widget/                       # Frontend Web Component
│   │   ├── package.json              # Package manifest ("js-chat-telegram-widget")
│   │   ├── tsconfig.json             # TypeScript compiler options
│   │   ├── vite.config.ts            # Vite library build config (ESM + CJS output)
│   │   ├── index.html                # Interactive developer showcase with testing controls
│   │   ├── chime.mp3                 # Binary notification sound asset (33KB)
│   │   ├── public/
│   │   │   └── chime.mp3             # Static asset copy
│   │   ├── src/
│   │   │   ├── index.ts              # Custom element registration: customElements.define('telegram-chat-widget', ...)
│   │   │   ├── widget.ts             # Core Custom Element class: TelegramChatWidget
│   │   │   ├── styles.ts             # Shadow DOM CSS styles, responsive queries & animations
│   │   │   ├── api.ts                # Client API SDK (ChatApi), token & cookie synchronization
│   │   │   └── chime.ts              # Base64 embedded chime audio player & autoplay unlocker
│   │   └── test/
│   │       └── widget.test.ts        # 12 Vitest tests covering all widget features
│   └── backend/                      # Python FastAPI Gateway
│       ├── Dockerfile                # Multi-stage non-root container build (python:3.12-slim)
│       ├── docker-compose.yml        # Local/production Docker Compose definition
│       ├── requirements.txt          # Production dependencies (fastapi, uvicorn, aiosqlite, etc.)
│       ├── pytest.ini                # Pytest configuration (asyncio mode = strict)
│       ├── .env.example              # Sanitized environment template
│       ├── app/
│       │   ├── __init__.py           # Package marker
│       │   ├── main.py               # FastAPI app, lifespan setup, cleaner & polling tasks
│       │   ├── config.py             # Pydantic Settings class & dynamic site_names mapping
│       │   ├── database.py           # SQLite schema init, migrations & aiosqlite context manager
│       │   ├── routes.py             # Endpoints: /send, /messages, /media/{id}, /telegram-webhook
│       │   ├── telegram.py           # TelegramService: dispatches, edits, replies, reactions
│       │   ├── polling.py            # Long-polling loop for tunnel-free local testing
│       │   ├── cleaner.py            # Background retention cleanup task
│       │   └── security.py           # Rate limiting, token validation & MIME type checks
│       └── tests/
│           ├── test_api.py           # 5 API route integration tests
│           └── test_offensive_gating.py # 7 offensive security, IDOR & session isolation tests
```

---

## 3. Detailed Component Reference

### 3.1 Frontend Widget (`packages/widget/src/`)

#### `widget.ts` (`TelegramChatWidget`)
- Custom element extending `HTMLElement`.
- Mounts open Shadow DOM (`this.attachShadow({ mode: 'open' })`).
- Observed attributes:
  - `backend-url`, `site-id`, `primary-color`, `accent-color`, `bg-color`, `font-family`, `font-url`, `title`, `placeholder`, `poll-interval`, `profile-pic`, `avatar-url`, `chime-url`.
- **Multiline auto-expanding composer**:
  - Uses `<textarea class="tg-input-field" rows="1">`.
  - On `input` event: calls `adjustTextareaHeight(textarea)` which clamps `scrollHeight` between `38px` and `120px`.
  - On `keydown`: `Enter` (without Shift) calls `handleSend()`; `Shift + Enter` allows natural newlines (`\n`).
  - Automatically shrinks back to `38px` single-line height upon message send.
  - Collapses 3+ consecutive newlines to maximum 2 (`text.trim().replace(/\n{3,}/g, '\n\n')`).
- **Avatar & Status Indicator**:
  - `DEFAULT_AVATAR_SVG`: Default customer support agent avatar with headset.
  - Launcher button renders `.tg-launcher-avatar` with active green `.tg-launcher-online-dot`.
  - When opened, `.tg-launcher-online-dot` scales down and hides, smoothly morphing into the close cross button.
  - Overridable via `profile-pic` or `avatar-url` HTML attributes with live update via `updateAvatar()`.
- **Audio Chime Integration**:
  - Unlocks audio (`unlockAudio()`) on launcher click, chatbox click, or textarea focus to comply with modern browser autoplay policies.
  - Calls `playChime(this.getAttribute('chime-url'))` during `pollMessages()` when new messages arrive from `admin`.
- **Attachments & Media**:
  - Handles file staging via paperclip button or drag-and-drop overlay (`.tg-dropzone-overlay`).
  - Supports clipboard paste of image screenshots (`paste` listener on textarea).
  - Lightbox modal for enlarged image previewing (`.tg-lightbox`).

#### `styles.ts`
- Pure CSS string rendered inside Shadow DOM `<style>`.
- Tokenized via CSS variables: `--primary`, `--accent`, `--bg`, `--font-stack`, etc.
- **Bubble Text Formatting Rule**:
  - `.tg-bubble-content`: container for media and text.
  - `.tg-bubble-text`: specifically styled with `white-space: pre-wrap; word-break: break-word;`.
  - *Note*: Keep `white-space: pre-wrap` on `.tg-bubble-text`, NOT on the outer template wrapper to avoid rendering HTML indentation spaces.
- **Mobile Responsiveness (`@media (max-width: 640px)`)**:
  - Full-screen sheet: `height: 100dvh !important; width: 100vw !important; border-radius: 0 !important;`.
  - Prevents iOS Safari auto-zoom by enforcing `font-size: 16px !important;` on the textarea.
  - Safe-area insets: uses `env(safe-area-inset-top)` on header and `env(safe-area-inset-bottom)` on composer.
  - Guaranteed accessible touch targets: minimum 40–44px on interactive buttons.

#### `api.ts` (`ChatApi`)
- Handles all HTTP communication with backend.
- **Session Token Persistence**:
  - Generates or retrieves UUID token.
  - Synchronizes token across both `SameSite=Lax` cookies (`tg_chat_token_<site_id>`, `tg_chat_token`) and `localStorage`.
- **Origin & URL Tracking**:
  - Transmits `page_url` (`window.location.href`), `page_title` (`document.title`), and header `X-Page-Url` on every message dispatch.

#### `chime.ts`
- Self-contained notification audio system.
- `DEFAULT_CHIME_BASE64`: Data URI of `packages/widget/chime.mp3`, allowing the widget to work out-of-the-box on any CDN/domain without 404s.
- `playChime(customUrl)`: Plays the chime audio safely with promise rejection handling.
- `unlockAudio()`: Plays muted audio on initial user gesture to unlock the Web Audio context.

---

### 3.2 Backend Gateway (`packages/backend/app/`)

#### `config.py` (`Settings`)
- Pydantic Settings reading environment variables and `.env`.
- Default values for secrets are strictly empty or placeholders (`TELEGRAM_BOT_TOKEN = ""`, `TELEGRAM_ADMIN_CHAT_ID = ""`).
- `site_names`: Dynamic dictionary mapping hostnames, URLs, and site IDs to human-readable names (e.g., `{"http://localhost:5173": "Demo Store"}`).

#### `database.py`
- Asynchronous SQLite database managed via `aiosqlite`.
- Path determined by `settings.db_path` (`DATA_DIR/chat.db`).
- Schema tables:
  - `sessions`: `(session_id TEXT PRIMARY KEY, site_id TEXT, created_at INTEGER, last_active_at INTEGER)`
  - `messages`: `(id TEXT PRIMARY KEY, session_id TEXT, sender TEXT, text TEXT, media_type TEXT, media_url TEXT, telegram_message_id INTEGER, created_at INTEGER)`
  - `media`: `(id TEXT PRIMARY KEY, session_id TEXT, filename TEXT, mime_type TEXT, file_path TEXT, created_at INTEGER)`
  - `rate_limits`: `(session_id TEXT, timestamp INTEGER)`
- Database indexes on `session_id`, `created_at`, and `telegram_message_id`.

#### `routes.py`
- `POST /api/v1/send`:
  - Validates session token, rate limits, and payload size.
  - Saves message & staged attachment.
  - Dispatches formatted notification to Telegram with site name, calling URL, session ID, and status badge.
- `GET /api/v1/messages`:
  - Returns historical messages strictly filtered by `session_id = :visitor_token`.
- `GET /api/v1/media/{media_id}`:
  - Streams media files after verifying requesting session ownership (IDOR protection).
- `POST /api/v1/telegram-webhook`:
  - Processes updates from Telegram.
  - Handles direct replies to visitor messages (adds `✅ Replied by @Admin` reaction and edits original message).
  - Broadcasts replies to other admins in supergroups.
  - Supports `/reply <session_id> <text>` and `/auth <secret>` commands.
- `GET /health` & `GET /stats`.

#### `telegram.py` (`TelegramService`)
- Asynchronous HTTP client communicating with `https://api.telegram.org/bot<TOKEN>/`.
- Methods: `send_message`, `send_photo`, `send_document`, `send_video`, `send_audio`, `edit_message_text`, `set_message_reaction`, `get_updates`.

#### `polling.py`
- Activated when `TELEGRAM_POLLING_MODE=true`.
- Runs background long-polling loop calling `getUpdates`, allowing full Telegram reply and command functionality during local development without ngrok or public tunnels.

#### `cleaner.py`
- Background asyncio task running every 60 minutes.
- Purges sessions, messages, and attachment files older than `HISTORY_RETENTION_HOURS` (default: 72 hours).

#### `security.py`
- Rate limiting: sliding window memory store (30 requests/minute per session).
- Token verification: extracts Bearer token or cookie `tg_chat_token`.
- Attachment inspection: validates MIME types (images, videos, audio, PDF, TXT, ZIP) and blocks executables/scripts.

---

## 4. Testing & Quality Assurance

### Widget Test Suite (`packages/widget`)
Run via:
```bash
cd packages/widget && npm run test:run
```
Tests in `test/widget.test.ts` verify:
1. Registration in `customElements` registry.
2. Open Shadow DOM root, launcher, and chatbox presence.
3. CSS custom property application (`--tg-primary`, `--tg-accent`, `--tg-bg`).
4. Launcher toggle and `aria-expanded` state tracking.
5. Dynamic attribute mutations (`title`, `placeholder`).
6. Light dismiss via `Escape` key.
7. Session token cookie and `localStorage` persistence.
8. Default customer support avatar and online dot rendering.
9. Custom avatar override via `profile-pic` and `avatar-url`.
10. Multiline textarea auto-expansion up to 120px limit.
11. Textarea scroll behavior (`overflow-y: auto` when exceeding 120px).
12. Key events: `Enter` sends message; `Shift + Enter` inserts newline.

### Backend Test Suite (`packages/backend`)
Run via:
```bash
cd packages/backend && pytest
```
Tests verify:
- `test_api.py`: Message dispatches, origin detection, site name resolution, Telegram webhook reply processing, and cookie setting.
- `test_offensive_gating.py`: Cross-session IDOR isolation, forged session attacks, directory traversal path-injection on media endpoints, rate limit exhaustion, and oversized attachment rejection.

---

## 5. Build, Packaging & CI/CD

### 5.1 npm Registry Publishing
- **Workflow**: `.github/workflows/publish-widget.yml`
- **Package Name**: `js-chat-telegram-widget`
- **Build Output**: `packages/widget/dist/`
  - `dist/index.mjs` (ES Module)
  - `dist/index.js` (CommonJS)
  - `dist/index.d.ts` (TypeScript type declarations)
- **Secret**: `NPM_TOKEN` stored in GitHub repository secrets.
- **Trigger**: Push to tag `v*.*.*` or manual `workflow_dispatch`.

### 5.2 GitHub Container Registry (GHCR)
- **Workflow**: `.github/workflows/publish-backend.yml`
- **Image Target**: `ghcr.io/<owner>/js-chat-telegram-widget-backend`
- **Build Context**: `packages/backend` using multi-stage Dockerfile.
- **Secret**: `${{ secrets.GITHUB_TOKEN }}` (built-in GitHub Actions token).
- **Trigger**: Push to tag `v*.*.*` or manual `workflow_dispatch`.

---

## 6. Development Rules & Secret Hygiene

> [!IMPORTANT]
> **Strict Secret Isolation**:
> - NEVER commit `.env`, `data/`, `chat.db`, or `k8s/secret.yaml`.
> - Always verify `.gitignore` before adding new files.
> - Defaults in `config.py` and Kubernetes `configmap.yaml` must only contain dummy placeholders.

> [!TIP]
> **Extending Widget Styles**:
> - When modifying bubble layout in `packages/widget/src/styles.ts`, ensure `white-space: pre-wrap;` is restricted to `.tg-bubble-text`. Applying it to parent template containers will cause HTML indentation spaces to render as visible blank lines.

> [!TIP]
> **Mobile Compatibility**:
> - Never set `font-size < 16px` on `<textarea>` or `<input>` in mobile CSS viewports (`@media (max-width: 640px)`). Doing so triggers iOS Safari's automatic viewport zoom, breaking mobile sheet positioning.

---

## 7. Credits & Acknowledgements

- Architecture and code developed with assistance from **Gemini**.
- UI animation heuristics, micro-interactions, and mobile responsiveness benchmarked with **Appllama**.
