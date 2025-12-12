import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Base path for production deployment behind Traefik /studio prefix
  base: '/studio/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175,
    proxy: {
      // Proxy unified API v1 requests
      '/api/v1': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      // Proxy WebSocket connections for real-time updates
      '/ws/v1': {
        target: 'ws://localhost:8003',
        ws: true,
        changeOrigin: true,
      },
      // Legacy: Proxy MCP StreamableHTTP requests to backend
      '/mcp': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // Legacy: Proxy Playground REST API requests
      '/api/playground': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Legacy: Proxy Builder REST API requests
      '/api/builder': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          state: ['zustand', 'immer'],
          editor: ['@monaco-editor/react'],
          flow: ['reactflow'],
          markdown: ['react-markdown', 'remark-gfm'],
        },
      },
    },
  },
});
