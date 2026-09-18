# js-chat-telegram-widget

[![npm version](https://img.shields.io/npm/v/js-chat-telegram-widget.svg)](https://www.npmjs.com/package/js-chat-telegram-widget)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

> Zero-dependency, framework-agnostic native Web Component (`<telegram-chat-widget>`) connecting any website directly to a Telegram Bot & Support Team.

---

## ✨ Features

- 🌐 **Zero Dependencies**: Lightweight, self-contained native Custom Element with open Shadow DOM styling isolation.
- 🧩 **Framework Agnostic**: Works out-of-the-box in Vanilla HTML, React, Next.js, Vue, Nuxt, Svelte, Angular, Hugo, Jekyll, or WordPress.
- 📱 **Mobile Native Feel**: Responsive sheet layout (`100dvh`), iOS Safari auto-zoom prevention, safe-area inset support, and fluid entrance micro-animations.
- ✍️ **Auto-Expanding Composer**: Multiline textarea clamping up to 120px with `Shift + Enter` multiline newline support and auto-shrink.
- 🔔 **Embedded Audio Chime**: Self-contained notification chime that rings when support replies arrive, compliant with modern browser autoplay unlock policies.
- 📎 **Rich Media Staging**: Image and file attachment previews with lightbox zoom and clipboard screenshot paste support.
- 🎨 **Fully Customizable**: Flexible CSS custom properties for palette colors, support agent avatars, and typography.

---

## 📦 Installation

```bash
npm install js-chat-telegram-widget
```

---

## 🚀 Usage

### 1. Static HTML / CDN

Include the script directly via CDN (no build step required):

```html
<!-- Load Custom Element bundle -->
<script type="module" src="https://unpkg.com/js-chat-telegram-widget/dist/index.mjs"></script>

<!-- Place widget in your document body -->
<telegram-chat-widget
  backend-url="https://chat.yourdomain.com"
  site-id="my-store"
  primary-color="#151946"
  accent-color="#7C170D"
  bg-color="#EBE1D5"
  title="Customer Support"
  placeholder="Type a message or attach an image..."
  poll-interval="3000">
</telegram-chat-widget>
```

---

### 2. React / Next.js (App Router or Pages Router)

```tsx
'use client';

import { useEffect } from 'react';

export default function SupportChat() {
  useEffect(() => {
    // Dynamically imports and defines <telegram-chat-widget> on the client
    import('js-chat-telegram-widget');
  }, []);

  return (
    // @ts-ignore custom element
    <telegram-chat-widget
      backend-url="https://chat.yourdomain.com"
      site-id="react-store"
      primary-color="#151946"
      accent-color="#7C170D"
      bg-color="#EBE1D5"
      title="Live Chat Support"
    />
  );
}
```

---

### 3. Vue 3 / Nuxt

```vue
<script setup>
import { onMounted } from 'vue';

onMounted(async () => {
  await import('js-chat-telegram-widget');
});
</script>

<template>
  <telegram-chat-widget
    backend-url="https://chat.yourdomain.com"
    site-id="vue-store"
    primary-color="#151946"
    accent-color="#7C170D"
    bg-color="#EBE1D5"
  />
</template>
```

---

### 4. Svelte / SvelteKit

```svelte
<script>
  import { onMount } from 'svelte';

  onMount(async () => {
    await import('js-chat-telegram-widget');
  });
</script>

<telegram-chat-widget
  backend-url="https://chat.yourdomain.com"
  site-id="svelte-store"
/>
```

---

## ⚙️ Configurable Attributes

| Attribute | Type | Default | Description |
|---|---|---|---|
| `backend-url` | `string` | **Required** | Base URL of your backend gateway |
| `site-id` | `string` | `window.location.hostname` | Store / site identifier sent with messages |
| `primary-color` | `string` | `#151946` | Header, launcher, and visitor bubble color |
| `accent-color` | `string` | `#7C170D` | Action buttons, badges, and active focus rings |
| `bg-color` | `string` | `#EBE1D5` | Chat message canvas background color |
| `title` | `string` | `Chat with us` | Header display title |
| `placeholder` | `string` | `Type a message...` | Input field placeholder text |
| `poll-interval` | `number` | `3000` | Polling frequency for incoming messages in ms |
| `profile-pic` | `string` | *Headset Agent* | Custom avatar image URL for header & launcher |
| `avatar-url` | `string` | *Headset Agent* | Alias for `profile-pic` |
| `font-family` | `string` | System font stack | Custom typography font family |
| `font-url` | `string` | `""` | Optional Google Fonts stylesheet link to load |
| `chime-url` | `string` | *Embedded Base64* | Custom audio chime URL (defaults to built-in sound) |

---

## 🔒 Security & Privacy

- **Session Isolation**: Each visitor is assigned an isolated cryptographic UUID token stored in `localStorage` and `SameSite=Lax` cookies. Visitors can never view or access other visitors' messages.
- **Bot Protection**: Telegram bot tokens are strictly isolated in the backend gateway; clients never communicate with Telegram directly.
- **Media Safety**: Uploaded files and attachments are checked for permitted MIME types and served with session-level access control.

---

## 📄 License

MIT © [Timothé Chauvet](https://github.com/timothechauvet)
