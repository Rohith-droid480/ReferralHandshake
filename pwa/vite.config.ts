import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  css: {
    postcss: {
      plugins: [
        tailwindcss({
          config: path.resolve(__dirname, 'tailwind.config.js'),
        }),
        autoprefixer(),
      ],
    },
  },
  server: {
    host: '0.0.0.0',
    port: 8080,
    proxy: {
      '/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/mode': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/status': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 8080,
  },
});

