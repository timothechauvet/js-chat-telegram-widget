/// <reference types="vitest" />
import { defineConfig } from 'vite';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'TelegramChatWidget',
      fileName: (format) => (format === 'es' ? 'index.mjs' : 'index.js'),
      formats: ['es', 'umd'],
    },
    rollupOptions: {
      output: {
        exports: 'named',
      },
    },
    minify: 'esbuild',
  },
  plugins: [
    {
      name: 'html-transform',
      transformIndexHtml(html) {
        let updated = html;
        if (process.env.VITE_BACKEND_URL || process.env.BACKEND_URL) {
          const url = process.env.VITE_BACKEND_URL || process.env.BACKEND_URL;
          updated = updated.replace(/backend-url="[^"]*"/, `backend-url="${url}"`);
        }
        if (process.env.SITE_ID) {
          updated = updated.replace(/site-id="[^"]*"/, `site-id="${process.env.SITE_ID}"`);
        }
        if (process.env.PRIMARY_COLOR) {
          updated = updated.replace(/primary-color="[^"]*"/, `primary-color="${process.env.PRIMARY_COLOR}"`);
        }
        return updated;
      },
    },
  ],
  test: {
    environment: 'jsdom',
    globals: true,
  },
});

