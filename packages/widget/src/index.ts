import { TelegramChatWidget } from './widget';

export { TelegramChatWidget } from './widget';
export { ChatApi, type ChatMessage } from './api';
export { getWidgetStyles } from './styles';

if (typeof window !== 'undefined' && !customElements.get('telegram-chat-widget')) {
  customElements.define('telegram-chat-widget', TelegramChatWidget);
}
