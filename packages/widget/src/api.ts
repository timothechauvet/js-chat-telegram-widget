export interface ChatMessage {
  id: string;
  sender: 'visitor' | 'admin';
  text?: string | null;
  media_type?: 'photo' | 'video' | 'audio' | 'document' | null;
  media_url?: string | null;
  created_at: number;
}

export class ChatApi {
  private backendUrl: string;
  private siteId: string;
  private sessionTokenKey: string;
  private token: string;

  constructor(backendUrl: string, siteId: string) {
    this.backendUrl = backendUrl.replace(/\/+$/, '');
    this.siteId = siteId || (typeof window !== 'undefined' ? window.location.hostname : 'default');
    this.sessionTokenKey = `tg_chat_token_${this.siteId}`;
    this.token = this.initSessionToken();
  }

  public getSessionToken(): string {
    return this.token;
  }

  public getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null;
    const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
    return match ? decodeURIComponent(match[3]) : null;
  }

  public setCookie(name: string, value: string, days: number = 365): void {
    if (typeof document === 'undefined') return;
    const maxAge = days * 24 * 60 * 60;
    const secure = typeof window !== 'undefined' && window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;
  }

  private initSessionToken(): string {
    let saved: string | null = null;

    // 1. Try reading from cookie first (site-specific or generic)
    saved = this.getCookie(this.sessionTokenKey) || this.getCookie('tg_chat_token');

    // 2. Fallback to localStorage if cookie not found
    if (!saved && typeof window !== 'undefined' && window.localStorage) {
      try {
        saved = localStorage.getItem(this.sessionTokenKey);
      } catch {
        // localStorage might be blocked in restricted browser contexts
      }
    }

    // 3. Generate a new token if not found anywhere
    if (!saved) {
      saved = this.generateUUID();
    }

    // 4. Synchronize token to both cookies and localStorage for robust persistence
    this.persistToken(saved);

    return saved;
  }

  private persistToken(token: string): void {
    // Persist in cookies
    this.setCookie(this.sessionTokenKey, token, 365);
    this.setCookie('tg_chat_token', token, 365);

    // Persist in localStorage
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        localStorage.setItem(this.sessionTokenKey, token);
      } catch {
        // Ignored if localStorage blocked
      }
    }
  }

  private generateUUID(): string {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  public updateConfig(backendUrl: string, siteId: string): void {
    this.backendUrl = backendUrl.replace(/\/+$/, '');
    if (siteId && siteId !== this.siteId) {
      this.siteId = siteId;
      this.sessionTokenKey = `tg_chat_token_${this.siteId}`;
      this.token = this.initSessionToken();
    }
  }

  public getBaseUrl(): string {
    if (this.backendUrl) return this.backendUrl;
    if (typeof window !== 'undefined' && window.location && window.location.origin) {
      return window.location.origin;
    }
    return 'http://localhost:8000';
  }

  public async fetchMessages(since?: number): Promise<ChatMessage[]> {
    const base = this.getBaseUrl();
    const url = new URL(`${base}/api/v1/messages`);
    if (since) {
      url.searchParams.set('since', since.toString());
    }

    const res = await fetch(url.toString(), {
      method: 'GET',
      credentials: 'include',
      headers: {
        Authorization: `Bearer ${this.token}`,
      },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch messages: ${res.status} ${res.statusText}`);
    }

    return (await res.json()) as ChatMessage[];
  }

  public async sendMessage(text?: string, file?: File): Promise<{ status: string; message_id: string }> {
    const formData = new FormData();
    formData.append('site_id', this.siteId);
    if (typeof window !== 'undefined') {
      formData.append('page_url', window.location.href);
      if (document.title) {
        formData.append('page_title', document.title);
      }
    }
    if (text && text.trim().length > 0) {
      formData.append('text', text.trim());
    }
    if (file) {
      formData.append('file', file);
    }

    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.token}`,
    };
    if (typeof window !== 'undefined') {
      headers['X-Page-Url'] = window.location.href;
    }

    const base = this.getBaseUrl();
    const res = await fetch(`${base}/api/v1/send`, {
      method: 'POST',
      credentials: 'include',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Send failed: ${res.statusText}`);
    }

    return (await res.json()) as { status: string; message_id: string };
  }

  public async getStatus(): Promise<{ is_online: boolean; is_night: boolean; offline_message: string }> {
    const base = this.getBaseUrl();
    const res = await fetch(`${base}/api/v1/status`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Authorization: *** ${this.token}`,
      },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch status: ${res.status} ${res.statusText}`);
    }

    return (await res.json()) as { is_online: boolean; is_night: boolean; offline_message: string };
  }

  public getAbsoluteMediaUrl(mediaUrl: string): string {
    if (!mediaUrl) return '';
    let fullUrl = mediaUrl;
    if (!mediaUrl.startsWith('http://') && !mediaUrl.startsWith('https://')) {
      const base = this.getBaseUrl();
      fullUrl = `${base}${mediaUrl.startsWith('/') ? '' : '/'}${mediaUrl}`;
    }
    try {
      const url = new URL(fullUrl);
      if (this.token && !url.searchParams.has('token')) {
        url.searchParams.set('token', this.token);
      }
      return url.toString();
    } catch {
      return fullUrl;
    }
  }
}
