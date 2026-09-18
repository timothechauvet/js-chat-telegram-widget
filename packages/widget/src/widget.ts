import { ChatApi, ChatMessage } from './api';
import { getWidgetStyles } from './styles';
import { playChime, unlockAudio } from './chime';

const DEFAULT_AVATAR_SVG = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='bg' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='%23151946'/><stop offset='100%' stop-color='%23242B6A'/></linearGradient><linearGradient id='face' x1='0%' y1='0%' x2='0%' y2='100%'><stop offset='0%' stop-color='%23FFDFBF'/><stop offset='100%' stop-color='%23F3C69D'/></linearGradient></defs><circle cx='50' cy='50' r='50' fill='url(%23bg)'/><circle cx='50' cy='46' r='22' fill='url(%23face)'/><path d='M34 42 C34 29, 66 29, 66 42 C66 44, 63 39, 50 39 C37 39, 34 44, 34 42 Z' fill='%232D1A10'/><circle cx='43' cy='46' r='2.5' fill='%232D1A10'/><circle cx='57' cy='46' r='2.5' fill='%232D1A10'/><path d='M45 55 Q50 60 55 55' stroke='%23B35936' stroke-width='2.2' stroke-linecap='round' fill='none'/><path d='M22 94 C26 74, 74 74, 78 94 Z' fill='%23FFFFFF'/><path d='M31 46 C31 33, 69 33, 69 46' stroke='%237C170D' stroke-width='3.5' stroke-linecap='round' fill='none'/><rect x='27' y='42' width='6' height='12' rx='3' fill='%237C170D'/><rect x='67' y='42' width='6' height='12' rx='3' fill='%237C170D'/><path d='M33 51 Q38 64 48 62' stroke='%237C170D' stroke-width='2.2' stroke-linecap='round' fill='none'/><circle cx='49' cy='62' r='2.8' fill='%237C170D'/></svg>`;

const ICONS = {
  chat: `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>`,
  close: `<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>`,
  send: `<svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor;"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>`,
  paperclip: `<svg viewBox="0 0 24 24" style="width:20px;height:20px;fill:currentColor;"><path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 0 1 5 0v10.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5V6H9v9.5a3.5 3.5 0 0 0 7 0V5c0-2.21-1.79-4-4-4S5 2.79 5 5v12.5c0 3.31 2.69 6 6 6s6-2.69 6-6V6h-1.5z"/></svg>`,
  document: `<svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>`,
  empty: `<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/></svg>`,
  check: `<svg viewBox="0 0 24 24" class="tg-check-icon"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>`,
  cloudUpload: `<svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>`,
};

export class TelegramChatWidget extends HTMLElement {
  private shadow: ShadowRoot;
  private api: ChatApi | null = null;
  private messages: ChatMessage[] = [];
  private pollIntervalId: number | null = null;
  private isOpen: boolean = false;
  private stagedFile: File | null = null;
  private unreadCount: number = 0;
  private onDocumentKeyDown: ((e: KeyboardEvent) => void) | null = null;
  private onDocumentClick: ((e: MouseEvent) => void) | null = null;

  static get observedAttributes() {
    return [
      'backend-url',
      'site-id',
      'primary-color',
      'accent-color',
      'bg-color',
      'font-family',
      'font-url',
      'title',
      'placeholder',
      'poll-interval',
      'profile-pic',
      'avatar-url',
      'chime-url',
    ];
  }

  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this.render();
    this.initApi();
    this.startPolling();
    this.attachGlobalListeners();
  }

  disconnectedCallback() {
    this.stopPolling();
    this.detachGlobalListeners();
  }

  attributeChangedCallback(name: string, oldValue: string, newValue: string) {
    if (oldValue === newValue) return;

    if (name === 'backend-url' || name === 'site-id') {
      this.initApi();
      this.messages = [];
      this.startPolling();
    } else if (name === 'poll-interval') {
      this.startPolling();
    } else if (name === 'font-url') {
      this.injectFontUrl(newValue);
    } else if (name === 'title' || name === 'placeholder') {
      this.updateStaticLabels();
    } else if (name === 'profile-pic' || name === 'avatar-url') {
      this.updateAvatar();
    }

    this.updateCssCustomProperties();
  }

  public getAvatarUrl(): string {
    return this.getAttribute('profile-pic') || this.getAttribute('avatar-url') || DEFAULT_AVATAR_SVG;
  }

  private updateAvatar() {
    const avatarUrl = this.getAvatarUrl();
    const launcherAvatar = this.shadow.querySelector('.tg-launcher-avatar') as HTMLImageElement | null;
    if (launcherAvatar) {
      launcherAvatar.src = avatarUrl;
    }
    const headerAvatar = this.shadow.querySelector('.tg-header-avatar-img') as HTMLImageElement | null;
    if (headerAvatar) {
      headerAvatar.src = avatarUrl;
    }
  }

  private adjustTextareaHeight(textarea: HTMLTextAreaElement) {
    textarea.style.height = 'auto';
    const nextHeight = Math.min(Math.max(textarea.scrollHeight, 38), 120);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 120 ? 'auto' : 'hidden';
  }

  private initApi() {
    const backendUrl = this.getAttribute('backend-url') || '';
    const siteId = this.getAttribute('site-id') || (typeof window !== 'undefined' ? window.location.hostname : '');
    if (!this.api) {
      this.api = new ChatApi(backendUrl, siteId);
    } else {
      this.api.updateConfig(backendUrl, siteId);
    }
  }

  private startPolling() {
    this.stopPolling();
    const intervalMs = parseInt(this.getAttribute('poll-interval') || '3000', 10);
    this.pollMessages();
    this.pollIntervalId = window.setInterval(() => {
      this.pollMessages();
    }, intervalMs);
  }

  private stopPolling() {
    if (this.pollIntervalId !== null) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
    }
  }

  private async pollMessages() {
    if (!this.api) return;
    try {
      const fetched = await this.api.fetchMessages();
      const status = await this.api.getStatus();
      this.updateLauncherStatus(status.is_online);
      // Show typing indicator when admin online but no recent admin reply
      if (status.is_online && !fetched.some(m => m.sender === 'admin')) {
        this.renderTypingIndicator();
      } else {
        this.removeTypingIndicator();
      }
      if (JSON.stringify(fetched) !== JSON.stringify(this.messages)) {
        const isInitial = this.messages.length === 0;
        const prevAdminIds = new Set(this.messages.filter((m) => m.sender === 'admin').map((m) => m.id));
        const newAdminMessages = fetched.filter((m) => m.sender === 'admin' && !prevAdminIds.has(m.id));

        if (!isInitial && newAdminMessages.length > 0) {
          playChime(this.getAttribute('chime-url'));
        }

        if (!this.isOpen && newAdminMessages.length > 0) {
          this.unreadCount += newAdminMessages.length;
          this.updateBadge();
        }
        this.messages = fetched;
        this.renderMessages();
      }
    } catch {
      // Polling network fail handled gracefully
    }
  }

  private updateBadge() {
    const launcher = this.shadow.querySelector('.tg-launcher') as HTMLElement | null;
    const badge = this.shadow.querySelector('.tg-launcher-badge') as HTMLElement | null;
    if (!badge || !launcher) return;

    if (this.unreadCount > 0) {
      badge.textContent = this.unreadCount > 9 ? '9+' : this.unreadCount.toString();
      badge.style.display = 'flex';
      launcher.classList.add('has-unread');
    } else {
      badge.style.display = 'none';
      launcher.classList.remove('has-unread');
    }
  }

  private updateCssCustomProperties() {
    const primary = this.getAttribute('primary-color') || '#151946';
    const accent = this.getAttribute('accent-color') || '#7C170D';
    const bg = this.getAttribute('bg-color') || '#EBE1D5';
    const font = this.getAttribute('font-family') || '';

    this.style.setProperty('--tg-primary', primary);
    this.style.setProperty('--tg-accent', accent);
    this.style.setProperty('--tg-bg', bg);
    if (font) {
      this.style.setProperty('--tg-font', font);
    }
  }

  private injectFontUrl(fontUrl: string) {
    if (!fontUrl) return;
    let link = this.shadow.querySelector('link[data-custom-font]') as HTMLLinkElement | null;
    if (!link) {
      link = document.createElement('link');
      link.rel = 'stylesheet';
      link.setAttribute('data-custom-font', 'true');
      this.shadow.appendChild(link);
    }
    link.href = fontUrl;
  }

  private updateStaticLabels() {
    const titleEl = this.shadow.querySelector('.tg-header-text h3');
    if (titleEl) {
      titleEl.textContent = this.getAttribute('title') || 'Chat with us';
    }
    const inputEl = this.shadow.querySelector('.tg-input-field') as HTMLTextAreaElement | null;
    if (inputEl) {
      inputEl.placeholder = this.getAttribute('placeholder') || 'Write a message...';
    }
  }

  private toggleOpen() {
    unlockAudio();
    this.isOpen = !this.isOpen;
    const launcher = this.shadow.querySelector('.tg-launcher') as HTMLElement;
    const chatBox = this.shadow.querySelector('.tg-chat-box') as HTMLElement;

    if (this.isOpen) {
      launcher.classList.add('is-open');
      launcher.setAttribute('aria-expanded', 'true');
      chatBox.classList.add('is-open');
      this.unreadCount = 0;
      this.updateBadge();
      setTimeout(() => {
        const input = this.shadow.querySelector('.tg-input-field') as HTMLTextAreaElement | null;
        input?.focus();
        this.scrollToBottom();
      }, 100);
    } else {
      launcher.classList.remove('is-open');
      launcher.setAttribute('aria-expanded', 'false');
      chatBox.classList.remove('is-open');
      launcher.focus();
    }
  }

  private scrollToBottom() {
    const canvas = this.shadow.querySelector('.tg-messages-canvas');
    if (canvas) {
      canvas.scrollTop = canvas.scrollHeight;
    }
  }

  private stageFile(file: File) {
    const maxBytes = 20 * 1024 * 1024;
    if (file.size > maxBytes) {
      alert(`File "${file.name}" exceeds the 20MB limit.`);
      return;
    }
    this.stagedFile = file;
    this.renderAttachmentPreview();
  }

  private clearStagedFile() {
    this.stagedFile = null;
    this.renderAttachmentPreview();
  }

  private formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  private renderAttachmentPreview() {
    const bar = this.shadow.querySelector('.tg-attachment-preview-bar') as HTMLElement;
    if (!this.stagedFile) {
      bar.style.display = 'none';
      bar.innerHTML = '';
      return;
    }

    bar.style.display = 'flex';
    const isImg = this.stagedFile.type.startsWith('image/');
    const thumbSrc = isImg ? URL.createObjectURL(this.stagedFile) : '';
    const sizeStr = this.formatFileSize(this.stagedFile.size);

    bar.innerHTML = `
      <div class="tg-attachment-info">
        ${isImg ? `<img class="tg-preview-thumbnail" src="${thumbSrc}" alt="preview"/>` : ICONS.document}
        <span>${this.escapeHtml(this.stagedFile.name)}</span>
        <span class="tg-attachment-size">${sizeStr}</span>
      </div>
      <button class="tg-remove-attachment" title="Remove attachment" aria-label="Remove attachment">
        ${ICONS.close}
      </button>
    `;

    bar.querySelector('.tg-remove-attachment')?.addEventListener('click', () => {
      this.clearStagedFile();
    });
  }

  private async handleSend() {
    const input = this.shadow.querySelector('.tg-input-field') as HTMLTextAreaElement | null;
    const text = input?.value.trim().replace(/\n{3,}/g, '\n\n') || '';
    const file = this.stagedFile;

    if (!text && !file) return;

    if (!this.api) {
      this.initApi();
    }
    if (!this.api) return;

    // Optimistic visitor message
    const tempId = 'temp_' + Date.now();
    const optimisticMessage: ChatMessage = {
      id: tempId,
      sender: 'visitor',
      text: text || null,
      media_type: file ? this.detectMediaType(file.type) : null,
      media_url: file && file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
      created_at: Math.floor(Date.now() / 1000),
    };

    this.messages.push(optimisticMessage);
    this.renderMessages();
    this.scrollToBottom();

    // Reset composer input
    if (input) {
      input.value = '';
      this.adjustTextareaHeight(input);
    }
    this.clearStagedFile();

    const sendBtn = this.shadow.querySelector('.tg-send-btn') as HTMLButtonElement | null;
    try {
      if (sendBtn) sendBtn.disabled = true;

      await this.api.sendMessage(text, file || undefined);
      await this.pollMessages();
    } catch (err: any) {
      alert(`Error sending message: ${err.message || err}`);
      this.messages = this.messages.filter((m) => m.id !== tempId);
      this.renderMessages();
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  private detectMediaType(mime: string): 'photo' | 'video' | 'audio' | 'document' {
    if (mime.startsWith('image/')) return 'photo';
    if (mime.startsWith('video/')) return 'video';
    if (mime.startsWith('audio/')) return 'audio';
    return 'document';
  }

  private openLightbox(imgSrc: string) {
    const lightbox = this.shadow.querySelector('.tg-lightbox') as HTMLElement;
    const lightboxImg = lightbox.querySelector('img') as HTMLImageElement;
    lightboxImg.src = imgSrc;
    lightbox.classList.add('is-active');
  }

  private closeLightbox() {
    const lightbox = this.shadow.querySelector('.tg-lightbox') as HTMLElement;
    lightbox.classList.remove('is-active');
  }

  private updateLauncherStatus(isOnline: boolean) {
    const launcher = this.shadow.querySelector('.tg-launcher');
    const headerStatus = this.shadow.querySelector('.tg-header-status span');
    if (launcher) {
      if (isOnline) launcher.classList.remove('is-offline');
      else launcher.classList.add('is-offline');
    }
    if (headerStatus) {
      headerStatus.textContent = isOnline ? 'Active now' : 'Offline';
    }
  }

  private renderTypingIndicator() {
    const canvas = this.shadow.querySelector('.tg-messages-canvas');
    if (!canvas || canvas.querySelector('.tg-typing-indicator')) return;
    const div = document.createElement('div');
    div.className = 'tg-typing-indicator';
    div.innerHTML = '<span class="tg-typing-dot"></span><span class="tg-typing-dot"></span><span class="tg-typing-dot"></span>';
    canvas.appendChild(div);
    this.scrollToBottom();
  }

  private removeTypingIndicator() {
    const indicator = this.shadow.querySelector('.tg-typing-indicator');
    if (indicator) indicator.remove();
  }

  private renderMessages() {
    const canvas = this.shadow.querySelector('.tg-messages-canvas');
    if (!canvas) return;

    if (this.messages.length === 0) {
      canvas.innerHTML = `
        <div class="tg-empty-state">
          ${ICONS.empty}
          <p>No messages yet. Say hello and our team will get right back to you!</p>
        </div>
      `;
      return;
    }

    let html = this.messages
      .map((msg) => {
        const timeFormatted = new Date(msg.created_at * 1000).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        });
        const mediaHtml = this.renderMediaContent(msg);
        const textHtml = msg.text ? `<div class="tg-bubble-text">${this.escapeHtml(msg.text.trim())}</div>` : '';
        const checkIcon = msg.sender === 'visitor' ? ICONS.check : '';

        return `
          <div class="tg-message ${msg.sender}">
            <div class="tg-bubble-content">${mediaHtml}${textHtml}</div>
            <div class="tg-message-meta">
              <span>${timeFormatted}</span>
              ${checkIcon}
            </div>
          </div>
        `;
      })
      .join('');

    // If last message is visitor and no reply yet, show "replying soon"
    if (this.messages.length > 0 && this.messages[this.messages.length - 1].sender === 'visitor') {
      html += `<div class="tg-msg-system-gray">Someone will reply as soon as possible</div>`;
    }

    canvas.innerHTML = html;

    // Attach click listeners for images to open in lightbox
    canvas.querySelectorAll('.tg-bubble-media img').forEach((img) => {
      img.addEventListener('click', (e) => {
        const target = e.target as HTMLImageElement;
        if (target && target.src) {
          this.openLightbox(target.src);
        }
      });
    });

    this.scrollToBottom();
  }

  private renderMediaContent(msg: ChatMessage): string {
    if (!msg.media_type && !msg.media_url) return '';
    const src = msg.media_url && this.api ? this.api.getAbsoluteMediaUrl(msg.media_url) : msg.media_url || '';

    if (msg.media_type === 'photo' || (msg.media_url && msg.media_url.match(/\.(png|jpg|jpeg|webp|gif)$/i))) {
      return `<div class="tg-bubble-media"><img src="${src}" alt="Attached image" loading="lazy"/></div>`;
    }
    if (msg.media_type === 'video' || (msg.media_url && msg.media_url.match(/\.(mp4|webm|mov)$/i))) {
      return `<div class="tg-bubble-media"><video src="${src}" controls></video></div>`;
    }
    if (msg.media_type === 'audio' || (msg.media_url && msg.media_url.match(/\.(mp3|ogg|wav|m4a)$/i))) {
      return `<div class="tg-bubble-media"><audio src="${src}" controls></audio></div>`;
    }
    return `
      <div class="tg-bubble-media">
        <a class="tg-bubble-doc" href="${src}" target="_blank" rel="noopener noreferrer">
          ${ICONS.document}
          <div class="tg-bubble-doc-info">
            <span class="tg-bubble-doc-name">Download attachment</span>
          </div>
        </a>
      </div>
    `;
  }

  private escapeHtml(unsafe: string): string {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  private attachGlobalListeners() {
    this.onDocumentKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        const lightbox = this.shadow.querySelector('.tg-lightbox') as HTMLElement | null;
        if (lightbox && lightbox.classList.contains('is-active')) {
          this.closeLightbox();
        } else if (this.isOpen) {
          this.toggleOpen();
        }
      }
    };
    document.addEventListener('keydown', this.onDocumentKeyDown);

    // Light dismiss when clicking outside
    this.onDocumentClick = (e: MouseEvent) => {
      if (!this.isOpen) return;
      const path = e.composedPath();
      if (!path.includes(this)) {
        this.toggleOpen();
      }
    };
    document.addEventListener('click', this.onDocumentClick);
  }

  private detachGlobalListeners() {
    if (this.onDocumentKeyDown) {
      document.removeEventListener('keydown', this.onDocumentKeyDown);
      this.onDocumentKeyDown = null;
    }
    if (this.onDocumentClick) {
      document.removeEventListener('click', this.onDocumentClick);
      this.onDocumentClick = null;
    }
  }

  private setupDragAndDrop(chatBox: HTMLElement) {
    const dropzone = this.shadow.querySelector('.tg-dropzone-overlay') as HTMLElement;
    if (!dropzone) return;

    let dragDepth = 0;

    chatBox.addEventListener('dragenter', (e) => {
      e.preventDefault();
      dragDepth++;
      dropzone.classList.add('is-active');
    });

    chatBox.addEventListener('dragover', (e) => {
      e.preventDefault();
    });

    chatBox.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dragDepth--;
      if (dragDepth <= 0) {
        dragDepth = 0;
        dropzone.classList.remove('is-active');
      }
    });

    chatBox.addEventListener('drop', (e) => {
      e.preventDefault();
      dragDepth = 0;
      dropzone.classList.remove('is-active');

      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.stageFile(e.dataTransfer.files[0]);
      }
    });
  }

  private render() {
    this.updateCssCustomProperties();
    const title = this.getAttribute('title') || 'Chat with us';
    const placeholder = this.getAttribute('placeholder') || 'Write a message...';

    const fontUrl = this.getAttribute('font-url');
    if (fontUrl) {
      this.injectFontUrl(fontUrl);
    }

    this.shadow.innerHTML = `
      <style>${getWidgetStyles()}</style>
      
      <!-- Launcher Button with Accessible State -->
      <button class="tg-launcher" aria-label="Toggle Live Chat" aria-expanded="false">
        <span class="icon-chat">
          <img class="tg-launcher-avatar" src="${this.escapeHtml(this.getAvatarUrl())}" alt="Chat avatar"/>
        </span>
        <span class="icon-close">${ICONS.close}</span>
        <span class="tg-launcher-online-dot"></span>
        <span class="tg-launcher-badge" style="display:none;"></span>
      </button>

      <!-- Chat Box Card -->
      <div class="tg-chat-box" role="dialog" aria-modal="true" aria-label="Live Chat">
        <!-- Drag & Drop Overlay Zone -->
        <div class="tg-dropzone-overlay">
          ${ICONS.cloudUpload}
          <div class="tg-dropzone-text">Drop file here to send</div>
        </div>

        <div class="tg-header">
          <div class="tg-header-info">
            <div class="tg-header-avatar">
              <img class="tg-header-avatar-img" src="${this.escapeHtml(this.getAvatarUrl())}" alt="Support agent"/>
            </div>
            <div class="tg-header-text">
              <h3>${this.escapeHtml(title)}</h3>
              <div class="tg-header-status">
                <div class="tg-status-dot-container">
                  <span class="tg-status-dot-pulse"></span>
                  <span class="tg-status-dot"></span>
                </div>
                <span>Active now</span>
              </div>
            </div>
          </div>
          <button class="tg-close-btn" title="Close chat" aria-label="Close chat">
            ${ICONS.close}
          </button>
        </div>

        <div class="tg-messages-canvas"></div>

        <div class="tg-attachment-preview-bar" style="display:none;"></div>

        <div class="tg-input-box">
          <input type="file" id="tg-file-input" style="display:none;" accept="image/*,video/*,audio/*,.pdf,.txt,.zip"/>
          <button class="tg-attach-btn" title="Attach file" aria-label="Attach file">
            ${ICONS.paperclip}
          </button>
          <div class="tg-input-wrapper">
            <textarea class="tg-input-field" rows="1" placeholder="${this.escapeHtml(placeholder)}" aria-label="Message input"></textarea>
          </div>
          <button class="tg-send-btn" title="Send message" aria-label="Send message">
            ${ICONS.send}
          </button>
        </div>
      </div>

      <!-- Image Lightbox Modal -->
      <div class="tg-lightbox" role="dialog" aria-modal="true" aria-label="Image Preview">
        <button class="tg-lightbox-close" aria-label="Close image preview">${ICONS.close}</button>
        <img src="" alt="Enlarged view"/>
      </div>
    `;

    // Event listeners
    this.shadow.querySelector('.tg-launcher')?.addEventListener('click', () => this.toggleOpen());
    this.shadow.querySelector('.tg-close-btn')?.addEventListener('click', () => this.toggleOpen());

    const chatBox = this.shadow.querySelector('.tg-chat-box') as HTMLElement;
    if (chatBox) {
      this.setupDragAndDrop(chatBox);
    }

    const fileInput = this.shadow.querySelector('#tg-file-input') as HTMLInputElement;
    this.shadow.querySelector('.tg-attach-btn')?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        this.stageFile(fileInput.files[0]);
        fileInput.value = '';
      }
    });

    const inputField = this.shadow.querySelector('.tg-input-field') as HTMLTextAreaElement | null;
    if (inputField) {
      inputField.addEventListener('input', () => {
        this.adjustTextareaHeight(inputField);
      });

      inputField.addEventListener('keydown', (e: KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSend();
        }
      });

      inputField.addEventListener('focus', () => {
        unlockAudio();
      });

      // Clipboard Paste Listener (paste screenshots)
      inputField.addEventListener('paste', (e: ClipboardEvent) => {
        if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length > 0) {
          const file = e.clipboardData.files[0];
          if (file) {
            e.preventDefault();
            this.stageFile(file);
          }
        }
      });
    }

    this.shadow.querySelector('.tg-send-btn')?.addEventListener('click', () => this.handleSend());

    const lightbox = this.shadow.querySelector('.tg-lightbox') as HTMLElement;
    lightbox?.addEventListener('click', (e) => {
      if (e.target === lightbox || (e.target as HTMLElement).closest('.tg-lightbox-close')) {
        this.closeLightbox();
      }
    });

    this.renderMessages();
  }
}
