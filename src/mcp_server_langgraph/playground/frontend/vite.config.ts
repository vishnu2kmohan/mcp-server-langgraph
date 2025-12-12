import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5174,
    proxy: {
      // Proxy MCP StreamableHTTP requests to backend
      '/mcp': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // Proxy Playground REST API requests
      '/api/playground': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Proxy WebSocket connections for real-time updates
      '/ws/playground': {
        target: 'ws://localhost:8002',
        ws: true,
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
          vendor: ['react', 'react-dom'],
          markdown: ['react-markdown', 'remark-gfm'],
        },
      },
    },
  },
});
