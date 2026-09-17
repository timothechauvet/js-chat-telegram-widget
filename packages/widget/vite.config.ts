/// <reference types="vitest" />
import { defineConfig } from 'vite';
import { resolve } from 'path';

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
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
