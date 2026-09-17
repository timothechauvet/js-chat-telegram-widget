import { describe, it, expect, beforeEach } from 'vitest';
import '../src/index';
import { TelegramChatWidget } from '../src/widget';

describe('TelegramChatWidget Custom Element', () => {
  let widget: TelegramChatWidget;

  beforeEach(() => {
    document.body.innerHTML = '';
    widget = document.createElement('telegram-chat-widget') as TelegramChatWidget;
    document.body.appendChild(widget);
  });

  it('is registered in customElements registry', () => {
    expect(customElements.get('telegram-chat-widget')).toBeDefined();
  });

  it('renders open Shadow DOM root with launcher and chatbox', () => {
    expect(widget.shadowRoot).not.toBeNull();
    const launcher = widget.shadowRoot!.querySelector('.tg-launcher');
    const chatBox = widget.shadowRoot!.querySelector('.tg-chat-box');
    expect(launcher).toBeTruthy();
    expect(chatBox).toBeTruthy();
  });

  it('applies configured colors via css variables', () => {
    widget.setAttribute('primary-color', '#151946');
    widget.setAttribute('accent-color', '#7C170D');
    widget.setAttribute('bg-color', '#EBE1D5');

    expect(widget.style.getPropertyValue('--tg-primary')).toBe('#151946');
    expect(widget.style.getPropertyValue('--tg-accent')).toBe('#7C170D');
    expect(widget.style.getPropertyValue('--tg-bg')).toBe('#EBE1D5');
  });

  it('toggles chatbox visibility on launcher click and updates aria-expanded', () => {
    const launcher = widget.shadowRoot!.querySelector('.tg-launcher') as HTMLButtonElement;
    const chatBox = widget.shadowRoot!.querySelector('.tg-chat-box') as HTMLElement;

    expect(chatBox.classList.contains('is-open')).toBe(false);
    expect(launcher.getAttribute('aria-expanded')).toBe('false');

    launcher.click();
    expect(chatBox.classList.contains('is-open')).toBe(true);
    expect(launcher.getAttribute('aria-expanded')).toBe('true');

    launcher.click();
    expect(chatBox.classList.contains('is-open')).toBe(false);
    expect(launcher.getAttribute('aria-expanded')).toBe('false');
  });

  it('updates title attribute dynamically', () => {
    widget.setAttribute('title', 'Help Center');
    const headerTitle = widget.shadowRoot!.querySelector('.tg-header-text h3');
    expect(headerTitle?.textContent).toBe('Help Center');
  });

  it('updates placeholder attribute dynamically', () => {
    widget.setAttribute('placeholder', 'Ask anything...');
    const input = widget.shadowRoot!.querySelector('.tg-input-field') as HTMLInputElement;
    expect(input.placeholder).toBe('Ask anything...');
  });

  it('closes chatbox on Escape key press', () => {
    const launcher = widget.shadowRoot!.querySelector('.tg-launcher') as HTMLButtonElement;
    const chatBox = widget.shadowRoot!.querySelector('.tg-chat-box') as HTMLElement;

    launcher.click();
    expect(chatBox.classList.contains('is-open')).toBe(true);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(chatBox.classList.contains('is-open')).toBe(false);
  });

  it('persists session token to cookies and synchronizes with localStorage', async () => {
    const { ChatApi } = await import('../src/api');
    // Pre-populate cookie
    document.cookie = 'tg_chat_token_cookie_test=pre-existing-cookie-token; path=/';
    const api = new ChatApi('http://localhost:8000', 'cookie_test');

    expect(api.getSessionToken()).toBe('pre-existing-cookie-token');
    expect(document.cookie).toContain('tg_chat_token_cookie_test=pre-existing-cookie-token');
    if (typeof window !== 'undefined' && window.localStorage) {
      expect(window.localStorage.getItem('tg_chat_token_cookie_test')).toBe('pre-existing-cookie-token');
    }
  });

  it('renders default profile avatar and online status dot in launcher and header', () => {
    const launcherAvatar = widget.shadowRoot!.querySelector('.tg-launcher-avatar') as HTMLImageElement;
    const onlineDot = widget.shadowRoot!.querySelector('.tg-launcher-online-dot');
    const headerAvatar = widget.shadowRoot!.querySelector('.tg-header-avatar-img') as HTMLImageElement;

    expect(launcherAvatar).toBeTruthy();
    expect(launcherAvatar.src).toContain('data:image/svg+xml');
    expect(onlineDot).toBeTruthy();
    expect(headerAvatar).toBeTruthy();
    expect(headerAvatar.src).toContain('data:image/svg+xml');
  });

  it('customizes profile picture via profile-pic or avatar-url attributes', () => {
    widget.setAttribute('profile-pic', 'https://example.com/custom-support.png');
    let launcherAvatar = widget.shadowRoot!.querySelector('.tg-launcher-avatar') as HTMLImageElement;
    let headerAvatar = widget.shadowRoot!.querySelector('.tg-header-avatar-img') as HTMLImageElement;

    expect(launcherAvatar.src).toBe('https://example.com/custom-support.png');
    expect(headerAvatar.src).toBe('https://example.com/custom-support.png');

    widget.setAttribute('avatar-url', 'https://example.com/agent-2.webp');
    launcherAvatar = widget.shadowRoot!.querySelector('.tg-launcher-avatar') as HTMLImageElement;
    headerAvatar = widget.shadowRoot!.querySelector('.tg-header-avatar-img') as HTMLImageElement;

    expect(launcherAvatar.src).toBe('https://example.com/custom-support.png'); // profile-pic takes precedence or if profile-pic removed:
    widget.removeAttribute('profile-pic');
    launcherAvatar = widget.shadowRoot!.querySelector('.tg-launcher-avatar') as HTMLImageElement;
    expect(launcherAvatar.src).toBe('https://example.com/agent-2.webp');
  });

  it('renders multiline textarea with auto-height adjustment', () => {
    const textarea = widget.shadowRoot!.querySelector('.tg-input-field') as HTMLTextAreaElement;
    expect(textarea).toBeTruthy();
    expect(textarea.tagName.toLowerCase()).toBe('textarea');

    // Simulate multi-line input
    textarea.value = 'Hello\nWorld\nHow are you today?\nLine 4';
    // Mock scrollHeight
    Object.defineProperty(textarea, 'scrollHeight', { value: 78, configurable: true });
    textarea.dispatchEvent(new Event('input'));

    expect(textarea.style.height).toBe('78px');
    expect(textarea.style.overflowY).toBe('hidden');

    // Exceed max height (120px)
    Object.defineProperty(textarea, 'scrollHeight', { value: 200, configurable: true });
    textarea.dispatchEvent(new Event('input'));

    expect(textarea.style.height).toBe('120px');
    expect(textarea.style.overflowY).toBe('auto');
  });

  it('handles Enter to send and ignores Shift+Enter to allow newlines', () => {
    const textarea = widget.shadowRoot!.querySelector('.tg-input-field') as HTMLTextAreaElement;
    textarea.value = 'Test message';

    let sendCalled = false;
    (widget as any).handleSend = () => {
      sendCalled = true;
    };

    // Shift + Enter should NOT call handleSend
    const shiftEnterEvent = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, cancelable: true });
    textarea.dispatchEvent(shiftEnterEvent);
    expect(sendCalled).toBe(false);

    // Normal Enter should call handleSend
    const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false, cancelable: true });
    textarea.dispatchEvent(enterEvent);
    expect(sendCalled).toBe(true);
    expect(enterEvent.defaultPrevented).toBe(true);
  });
});
