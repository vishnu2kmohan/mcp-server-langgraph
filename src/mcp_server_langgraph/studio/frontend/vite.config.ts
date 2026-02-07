import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';
import { readFileSync, existsSync } from 'fs';
import packageJson from './package.json';

// Check if building for Storybook (Storybook sets this env var)
const isStorybook = process.env.STORYBOOK === 'true';
const OBSERVABILITY_ENV_MAPPINGS: Array<[string, string]> = [
  [
    'OBSERVABILITY_TRACE_LIST_POLLING_ACTIVE_MS',
    'VITE_OBSERVABILITY_TRACE_LIST_POLLING_ACTIVE_MS',
  ],
  [
    'OBSERVABILITY_TRACE_LIST_POLLING_IDLE_MS',
    'VITE_OBSERVABILITY_TRACE_LIST_POLLING_IDLE_MS',
  ],
  [
    'OBSERVABILITY_TRACE_DETAIL_POLLING_MS',
    'VITE_OBSERVABILITY_TRACE_DETAIL_POLLING_MS',
  ],
  ['OBSERVABILITY_METRICS_POLLING_MS', 'VITE_OBSERVABILITY_METRICS_POLLING_MS'],
  ['OBSERVABILITY_LOGS_POLLING_MS', 'VITE_OBSERVABILITY_LOGS_POLLING_MS'],
  ['OBSERVABILITY_ALERTS_POLLING_MS', 'VITE_OBSERVABILITY_ALERTS_POLLING_MS'],
];

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  const resolveEnvValue = (
    userKey: string,
    viteKey: string,
  ): string | undefined => {
    return (
      env[userKey] ??
      env[viteKey] ??
      process.env[userKey] ??
      process.env[viteKey]
    );
  };

  const observabilityEnvDefines = Object.fromEntries(
    OBSERVABILITY_ENV_MAPPINGS.map(([userKey, viteKey]) => [
      `import.meta.env.${viteKey}`,
      JSON.stringify(resolveEnvValue(userKey, viteKey) ?? ''),
    ]),
  );

  return {
    // Inject version and build info at compile time
    define: {
      __APP_VERSION__: JSON.stringify(packageJson.version),
      __BUILD_TIMESTAMP__: JSON.stringify(new Date().toISOString()),
      ...observabilityEnvDefines,
      // sql.js WASM integrity hash (injected at build time for runtime SRI verification)
      'import.meta.env.VITE_SQL_WASM_HASH': JSON.stringify(
        existsSync(path.resolve(__dirname, 'public/wasm/sql-wasm.sha384'))
          ? readFileSync(path.resolve(__dirname, 'public/wasm/sql-wasm.sha384'), 'utf-8').trim()
          : ''
      ),
    },
    plugins: [
      react(),
      // Exclude VitePWA when building for Storybook (Storybook's globals-runtime.js
      // exceeds the maximumFileSizeToCacheInBytes limit and causes build failures)
      !isStorybook && VitePWA({
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
            {
              // WASM files: Cache First (immutable, integrity-verified)
              urlPattern: /\.wasm$/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'wasm-cache',
                expiration: {
                  maxEntries: 5,
                  maxAgeSeconds: 365 * 24 * 60 * 60, // 1 year (versioned)
                },
              },
            },
          ],
        },
        devOptions: {
          enabled: false, // Disable SW in development
        },
      }),
    ].filter(Boolean),
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
      // Increase chunk size warning limit to 700KB
      // Large vendor chunks are expected for:
      // - vendor-sandpack (612KB) - Codesandbox interactive code execution
      // - vendor-syntax (618KB) - React syntax highlighter with all language grammars
      // - vendor-mermaid (483KB) - Mermaid diagram rendering library
      // - vendor-cytoscape (442KB) - Cytoscape graph visualization
      // These are all properly code-split and lazily loaded, so the warning is informational only
      chunkSizeWarningLimit: 700,
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
            // Syntax highlighting (large due to all language grammars)
            'vendor-syntax': ['react-syntax-highlighter'],
            // Code sandbox (very large, split separately)
            'vendor-sandpack': ['@codesandbox/sandpack-react'],
            // Math rendering (katex)
            'vendor-math': ['katex'],
            // Graph visualization (cytoscape)
            'vendor-cytoscape': ['cytoscape'],
            // sql.js SQLite WASM bridge (split for lazy loading)
            'vendor-sql': ['sql.js'],
          },
        },
      },
    },
  };
});
