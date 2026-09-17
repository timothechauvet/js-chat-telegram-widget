export const getWidgetStyles = (): string => `
:host {
  --primary: var(--tg-primary, #151946);
  --accent: var(--tg-accent, #7C170D);
  --bg: var(--tg-bg, #EBE1D5);
  --text-dark: #0F172A;
  --text-muted: #64748B;
  --bubble-admin: #FFFFFF;
  --bubble-admin-text: #0F172A;
  --font-stack: var(--tg-font, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif);
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --shadow-elevation-1: 0 2px 8px rgba(21, 25, 70, 0.08), 0 1px 2px rgba(21, 25, 70, 0.04);
  --shadow-elevation-2: 0 16px 36px rgba(21, 25, 70, 0.18), 0 4px 12px rgba(21, 25, 70, 0.08);
  --shadow-launcher: 0 8px 24px rgba(21, 25, 70, 0.22), 0 2px 6px rgba(21, 25, 70, 0.12);
  --radius-window: 22px;
  --radius-bubble: 18px;
  --radius-control: 14px;

  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 2147483647;
  font-family: var(--font-stack);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  box-sizing: border-box;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

button {
  background: none;
  border: none;
  font: inherit;
  cursor: pointer;
  outline: none;
  -webkit-tap-highlight-color: transparent;
}

/* ==========================================================================
   Launcher Button
   ========================================================================== */
.tg-launcher {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary) 0%, color-mix(in srgb, var(--primary) 82%, #000) 100%);
  color: #FFFFFF;
  box-shadow: var(--shadow-launcher);
  transition: transform 220ms var(--ease-spring), box-shadow 220ms ease, background 150ms ease;
  position: relative;
  overflow: visible;
  user-select: none;
}

.tg-launcher:hover {
  transform: scale(1.08);
  box-shadow: 0 16px 36px rgba(21, 25, 70, 0.28);
}

.tg-launcher:active {
  transform: scale(0.92);
}

/* Smooth morphing rotation for launcher icons */
.tg-launcher .icon-chat,
.tg-launcher .icon-close {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 280ms var(--ease-spring), opacity 200ms ease;
  will-change: transform, opacity;
  border-radius: 50%;
  overflow: hidden;
}

.tg-launcher .icon-chat {
  transform: rotate(0deg) scale(1);
  opacity: 1;
}

.tg-launcher.is-open .icon-chat {
  transform: rotate(90deg) scale(0.2);
  opacity: 0;
  pointer-events: none;
}

.tg-launcher .icon-close {
  transform: rotate(-90deg) scale(0.2);
  opacity: 0;
  pointer-events: none;
  background: linear-gradient(135deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 85%, #000) 100%);
}

.tg-launcher.is-open .icon-close {
  transform: rotate(0deg) scale(1);
  opacity: 1;
  pointer-events: auto;
}

.tg-launcher svg {
  width: 26px;
  height: 26px;
  fill: currentColor;
}

.tg-launcher-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  display: block;
}

.tg-launcher-online-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 14px;
  height: 14px;
  background-color: #22C55E;
  border: 2.5px solid #FFFFFF;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  z-index: 5;
  transition: transform 200ms var(--ease-spring), opacity 180ms ease;
}

.tg-launcher.is-open .tg-launcher-online-dot {
  transform: scale(0.2);
  opacity: 0;
  pointer-events: none;
}

/* Unread Badge */
.tg-launcher-badge {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  background-color: var(--accent);
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 700;
  border-radius: 11px;
  border: 2px solid #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  animation: badge-pop 320ms var(--ease-bounce);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
  z-index: 10;
}

.tg-launcher.has-unread {
  animation: launcher-pulse 2.2s infinite ease-in-out;
}

@keyframes launcher-pulse {
  0%, 100% {
    box-shadow: var(--shadow-launcher);
  }
  50% {
    box-shadow: 0 0 0 8px color-mix(in srgb, var(--accent) 35%, transparent), var(--shadow-launcher);
  }
}

@keyframes badge-pop {
  0% { transform: scale(0); opacity: 0; }
  60% { transform: scale(1.25); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

/* ==========================================================================
   Chat Box Card
   ========================================================================== */
.tg-chat-box {
  position: fixed;
  bottom: 96px;
  right: 24px;
  width: 384px;
  max-width: calc(100vw - 32px);
  height: 600px;
  max-height: calc(100vh - 120px);
  background-color: var(--bg);
  border-radius: var(--radius-window);
  box-shadow: var(--shadow-elevation-2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(21, 25, 70, 0.08);
  opacity: 0;
  visibility: hidden;
  transform: translateY(20px) scale(0.95);
  transform-origin: bottom right;
  transition:
    opacity 260ms var(--ease-spring),
    transform 280ms var(--ease-spring),
    visibility 280ms;
  will-change: transform, opacity;
  z-index: 2147483646;
}

@starting-style {
  .tg-chat-box.is-open {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
}

.tg-chat-box.is-open {
  opacity: 1;
  visibility: visible;
  transform: translateY(0) scale(1);
}

/* ==========================================================================
   Header
   ========================================================================== */
.tg-header {
  background: linear-gradient(135deg, var(--primary) 0%, color-mix(in srgb, var(--primary) 85%, #000) 100%);
  color: #FFFFFF;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: relative;
}

.tg-header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tg-header-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.tg-header-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  display: block;
}

.tg-header-avatar svg {
  width: 22px;
  height: 22px;
  fill: #FFFFFF;
}

.tg-header-text {
  display: flex;
  flex-direction: column;
}

.tg-header-text h3 {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.tg-header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  opacity: 0.9;
  margin-top: 2px;
}

.tg-status-dot-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 10px;
  height: 10px;
}

.tg-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #22C55E;
  z-index: 2;
}

.tg-status-dot-pulse {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #22C55E;
  opacity: 0.75;
  animation: dot-ripple 2s infinite cubic-bezier(0, 0.2, 0.8, 1);
}

@keyframes dot-ripple {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(2.6); opacity: 0; }
}

.tg-close-btn {
  color: #FFFFFF;
  opacity: 0.85;
  padding: 8px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 150ms, background-color 150ms, transform 200ms var(--ease-spring);
}

.tg-close-btn:hover {
  opacity: 1;
  background-color: rgba(255, 255, 255, 0.15);
  transform: rotate(90deg);
}

.tg-close-btn svg {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

/* ==========================================================================
   Drag & Drop Overlay
   ========================================================================== */
.tg-dropzone-overlay {
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--bg) 92%, #FFFFFF);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 100;
  opacity: 0;
  pointer-events: none;
  transition: opacity 180ms ease;
  border: 2px dashed var(--accent);
  margin: 8px;
  border-radius: calc(var(--radius-window) - 8px);
}

.tg-dropzone-overlay.is-active {
  opacity: 1;
  pointer-events: auto;
}

.tg-dropzone-overlay svg {
  width: 48px;
  height: 48px;
  fill: var(--accent);
  animation: float-bounce 1.5s infinite ease-in-out;
}

@keyframes float-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.tg-dropzone-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-dark);
}

/* ==========================================================================
   Messages Stream
   ========================================================================== */
.tg-messages-canvas {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
  background: var(--bg);
}

.tg-messages-canvas::-webkit-scrollbar {
  width: 6px;
}

.tg-messages-canvas::-webkit-scrollbar-thumb {
  background: rgba(21, 25, 70, 0.16);
  border-radius: 4px;
}

.tg-messages-canvas::-webkit-scrollbar-thumb:hover {
  background: rgba(21, 25, 70, 0.28);
}

/* ==========================================================================
   Message Bubble
   ========================================================================== */
.tg-message {
  display: flex;
  flex-direction: column;
  max-width: 82%;
  animation: bubble-slide-in 220ms var(--ease-spring) forwards;
  will-change: transform, opacity;
}

@keyframes bubble-slide-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.tg-message.visitor {
  align-self: flex-end;
  align-items: flex-end;
}

.tg-message.admin {
  align-self: flex-start;
  align-items: flex-start;
}

.tg-bubble-content {
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.45;
  position: relative;
  box-shadow: var(--shadow-elevation-1);
}

.tg-bubble-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.tg-message.visitor .tg-bubble-content {
  background-color: var(--primary);
  color: #FFFFFF;
  border-radius: var(--radius-bubble) var(--radius-bubble) 4px var(--radius-bubble);
}

.tg-message.admin .tg-bubble-content {
  background-color: var(--bubble-admin);
  color: var(--bubble-admin-text);
  border-radius: var(--radius-bubble) var(--radius-bubble) var(--radius-bubble) 4px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.tg-message-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 3px;
  font-size: 10.5px;
}

.tg-message.visitor .tg-message-meta {
  color: #475569;
  justify-content: flex-end;
}

.tg-message.admin .tg-message-meta {
  color: #64748B;
  justify-content: flex-start;
}

.tg-check-icon {
  width: 14px;
  height: 14px;
  fill: currentColor;
  opacity: 0.8;
}

/* Media styling inside bubbles */
.tg-bubble-media {
  margin-bottom: 6px;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.tg-bubble-media img {
  max-width: 100%;
  max-height: 220px;
  display: block;
  object-fit: cover;
  cursor: pointer;
  transition: opacity 150ms ease, transform 200ms var(--ease-spring);
  border-radius: 10px;
}

.tg-bubble-media img:hover {
  opacity: 0.94;
  transform: scale(1.02);
}

.tg-bubble-media video {
  max-width: 100%;
  max-height: 240px;
  display: block;
  border-radius: 10px;
}

.tg-bubble-media audio {
  max-width: 100%;
  display: block;
  outline: none;
}

.tg-bubble-doc {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  padding: 8px 6px;
  color: inherit;
  border-radius: 8px;
  transition: background-color 150ms ease;
}

.tg-bubble-doc:hover {
  background-color: rgba(255, 255, 255, 0.12);
}

.tg-bubble-doc svg {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  fill: currentColor;
}

.tg-bubble-doc-info {
  display: flex;
  flex-direction: column;
}

.tg-bubble-doc-name {
  font-weight: 600;
  font-size: 13px;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* ==========================================================================
   Typing Wave Indicator
   ========================================================================== */
.tg-typing-row {
  display: flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding: 8px 14px;
  background-color: var(--bubble-admin);
  border-radius: var(--radius-bubble) var(--radius-bubble) var(--radius-bubble) 4px;
  box-shadow: var(--shadow-elevation-1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  animation: bubble-slide-in 200ms var(--ease-spring) forwards;
}

.tg-typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 14px;
}

.tg-typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--text-muted);
  animation: typing-wave 1.3s infinite ease-in-out;
}

.tg-typing-dot:nth-child(1) { animation-delay: 0ms; }
.tg-typing-dot:nth-child(2) { animation-delay: 180ms; }
.tg-typing-dot:nth-child(3) { animation-delay: 360ms; }

@keyframes typing-wave {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.35;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

/* ==========================================================================
   Empty State
   ========================================================================== */
.tg-empty-state {
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 36px 20px;
  color: var(--text-muted);
}

.tg-empty-state svg {
  width: 52px;
  height: 52px;
  fill: var(--text-muted);
  opacity: 0.45;
  margin-bottom: 14px;
}

.tg-empty-state p {
  font-size: 13.5px;
  max-width: 240px;
  line-height: 1.45;
}

/* ==========================================================================
   Staged Attachment Preview
   ========================================================================== */
.tg-attachment-preview-bar {
  background: #FFFFFF;
  border-top: 1px solid rgba(21, 25, 70, 0.08);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-dark);
  animation: slide-up-preview 200ms var(--ease-spring);
}

@keyframes slide-up-preview {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.tg-attachment-info {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tg-preview-thumbnail {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid rgba(0,0,0,0.08);
}

.tg-attachment-size {
  font-size: 11px;
  color: var(--text-muted);
  background: #F1F5F9;
  padding: 2px 6px;
  border-radius: 4px;
}

.tg-remove-attachment {
  color: var(--accent);
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background-color 150ms, transform 150ms;
}

.tg-remove-attachment:hover {
  background: rgba(124, 23, 13, 0.1);
  transform: scale(1.1);
}

.tg-remove-attachment svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

/* ==========================================================================
   Composer / Input Area
   ========================================================================== */
.tg-input-box {
  padding: 10px 14px;
  background-color: #FFFFFF;
  border-top: 1px solid rgba(21, 25, 70, 0.08);
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
  position: relative;
}

.tg-attach-btn {
  color: var(--text-muted);
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-bottom: 1px;
  transition: color 150ms, background-color 150ms, transform 150ms;
}

.tg-attach-btn:hover {
  color: var(--primary);
  background-color: rgba(21, 25, 70, 0.06);
  transform: scale(1.08);
}

.tg-input-wrapper {
  flex: 1;
  display: flex;
  align-items: flex-end;
}

.tg-input-field {
  width: 100%;
  min-height: 38px;
  max-height: 120px;
  height: 38px;
  resize: none;
  border: 1px solid rgba(21, 25, 70, 0.15);
  border-radius: 19px;
  padding: 8px 14px;
  font-size: 14px;
  line-height: 1.42;
  font-family: inherit;
  color: var(--text-dark);
  background-color: #F8FAFC;
  outline: none;
  overflow-y: hidden;
  box-sizing: border-box;
  transition: border-color 160ms ease, background-color 160ms ease, box-shadow 160ms ease;
}

.tg-input-field:focus {
  border-color: var(--primary);
  background-color: #FFFFFF;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary) 15%, transparent);
}

.tg-send-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary) 0%, color-mix(in srgb, var(--primary) 85%, #000) 100%);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 180ms var(--ease-spring), opacity 150ms, background 150ms, box-shadow 150ms;
  flex-shrink: 0;
  margin-bottom: 1px;
  box-shadow: 0 2px 6px rgba(21, 25, 70, 0.2);
}

.tg-send-btn:hover:not(:disabled) {
  background: var(--accent);
  transform: scale(1.08);
  box-shadow: 0 4px 10px rgba(124, 23, 13, 0.3);
}

.tg-send-btn:active:not(:disabled) {
  transform: scale(0.92);
}

.tg-send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* ==========================================================================
   Lightbox Modal
   ========================================================================== */
.tg-lightbox {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.82);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2147483647;
  opacity: 0;
  visibility: hidden;
  transition: opacity 220ms ease, visibility 220ms;
  padding: 24px;
}

.tg-lightbox.is-active {
  opacity: 1;
  visibility: visible;
}

.tg-lightbox img {
  max-width: 90vw;
  max-height: 88vh;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
  transform: scale(0.92);
  transition: transform 240ms var(--ease-spring);
}

.tg-lightbox.is-active img {
  transform: scale(1);
}

.tg-lightbox-close {
  position: absolute;
  top: 24px;
  right: 24px;
  color: #FFFFFF;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 150ms, transform 150ms;
}

.tg-lightbox-close:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.08);
}

/* ==========================================================================
   Mobile Sheet / Responsive (Optimized for smartphones)
   ========================================================================== */
@media (max-width: 640px) {
  :host {
    bottom: 0 !important;
    right: 0 !important;
  }
  .tg-launcher {
    bottom: max(16px, env(safe-area-inset-bottom, 16px)) !important;
    right: max(16px, env(safe-area-inset-right, 16px)) !important;
    width: 58px !important;
    height: 58px !important;
  }
  .tg-chat-box {
    position: fixed !important;
    inset: 0 !important;
    width: 100vw !important;
    height: 100% !important;
    height: 100dvh !important;
    max-width: 100vw !important;
    max-height: 100dvh !important;
    bottom: 0 !important;
    right: 0 !important;
    border-radius: 0 !important;
    border: none !important;
    box-shadow: none !important;
    transform-origin: bottom center !important;
    z-index: 2147483647 !important;
  }
  .tg-header {
    padding-top: max(14px, env(safe-area-inset-top, 14px)) !important;
    padding-left: max(16px, env(safe-area-inset-left, 16px)) !important;
    padding-right: max(16px, env(safe-area-inset-right, 16px)) !important;
    border-radius: 0 !important;
  }
  .tg-close-btn {
    width: 44px !important;
    height: 44px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }
  .tg-messages-canvas {
    padding: 14px 12px !important;
    gap: 10px !important;
  }
  .tg-message {
    max-width: 88% !important;
  }
  .tg-bubble-content {
    font-size: 15px !important;
    padding: 10px 14px !important;
  }
  .tg-input-box {
    padding-bottom: max(12px, env(safe-area-inset-bottom, 12px)) !important;
    padding-left: max(12px, env(safe-area-inset-left, 12px)) !important;
    padding-right: max(12px, env(safe-area-inset-right, 12px)) !important;
  }
  .tg-input-field {
    font-size: 16px !important; /* 16px prevents iOS Safari from automatically zooming in */
    padding: 8px 14px !important;
  }
  .tg-attach-btn,
  .tg-send-btn {
    min-width: 40px !important;
    min-height: 40px !important;
  }
}

/* ==========================================================================
   Accessibility: Reduced Motion
   ========================================================================== */
@media (prefers-reduced-motion: reduce) {
  .tg-launcher,
  .tg-chat-box,
  .tg-message,
  .tg-lightbox img,
  .tg-send-btn,
  .tg-launcher-badge {
    animation: none !important;
    transition-duration: 0.05s !important;
    transform: none !important;
  }
  .tg-launcher.is-open .icon-chat,
  .tg-launcher .icon-close {
    transform: none !important;
  }
  .tg-status-dot-pulse {
    display: none;
  }
}
`;
