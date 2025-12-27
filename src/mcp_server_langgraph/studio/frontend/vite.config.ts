import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';
import packageJson from './package.json';

// https://vitejs.dev/config/
export default defineConfig({
  // Inject version and build info at compile time
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version),
    __BUILD_TIMESTAMP__: JSON.stringify(new Date().toISOString()),
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['icons/*.png', 'icons/*.svg'],
      manifest: false, // Use existing manifest.json in public/
      workbox: {
        // Precache all static assets
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
        // Allow larger chunks to be precached (ChatPage is ~2.5MB)
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024, // 3 MiB
        // Runtime caching strategies
        runtimeCaching: [
          {
            // API calls: Network First with cache fallback
            urlPattern: /^\/api\/v1\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 5 * 60, // 5 minutes
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            // Static assets: Cache First
            urlPattern: /\.(?:js|css)$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'static-assets-cache',
              expiration: {
                maxEntries: 60,
                maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
              },
            },
          },
          {
            // Images: Cache First
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
              },
            },
          },
          {
            // Fonts: Cache First
            urlPattern: /\.(?:woff|woff2|ttf|eot)$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'fonts-cache',
              expiration: {
                maxEntries: 20,
                maxAgeSeconds: 365 * 24 * 60 * 60, // 1 year
              },
            },
          },
        ],
      },
      devOptions: {
        enabled: false, // Disable SW in development
      },
    }),
  ],
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
      // Proxy unified v1 WebSocket connections (must be before /api/v1 for proper matching)
      // All WebSocket endpoints under /api/v1/ws/* use this proxy rule
      '/api/v1/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
      // Proxy unified API v1 requests to backend
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Proxy WebSocket connections for real-time updates (legacy)
      '/ws/v1': {
        target: 'ws://localhost:8000',
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
          // React core (react, react-dom, react-router)
          'vendor-react': ['react', 'react-dom', 'react-router'],
          // Redux state management
          'vendor-redux': ['@reduxjs/toolkit', 'react-redux'],
          // UI libraries (lucide-react, sonner)
          'vendor-ui': ['lucide-react', 'sonner'],
          // Charting libraries (recharts and its dependencies)
          'vendor-charts': ['recharts'],
          // Code editor (monaco-editor, @monaco-editor/react)
          'vendor-editor': ['@monaco-editor/react'],
          // Markdown rendering (react-markdown, remark-gfm)
          'vendor-markdown-base': ['react-markdown', 'remark-gfm', 'rehype-katex', 'remark-math'],
          // Mermaid diagram library (large, split separately)
          'vendor-mermaid': ['mermaid'],
          // Flow diagram library
          'vendor-flow': ['reactflow'],
          // Syntax highlighting
          'vendor-syntax': ['react-syntax-highlighter'],
          // Code sandbox (very large, split separately)
          'vendor-sandpack': ['@codesandbox/sandpack-react'],
          // Math rendering (katex)
          'vendor-math': ['katex'],
        },
      },
    },
  },
});
