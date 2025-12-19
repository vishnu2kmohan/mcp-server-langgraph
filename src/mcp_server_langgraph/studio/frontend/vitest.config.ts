import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Mock PWA virtual modules for testing
      'virtual:pwa-register/react': path.resolve(__dirname, './src/mocks/pwa-register-react.ts'),
      'virtual:pwa-register': path.resolve(__dirname, './src/mocks/pwa-register.ts'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Use forks pool for better isolation and stability
    pool: 'forks',
    poolOptions: {
      forks: {
        // Isolate each test file in its own process
        isolate: true,
        // Set a timeout for worker cleanup
        singleFork: false,
      },
    },
    // Limit concurrent tests to prevent memory issues
    maxConcurrency: 5,
    // Retry flaky tests once
    retry: 1,
    // Silence verbose errors during cleanup
    silent: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/test/**',
        'src/mocks/**',
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/types/**',
        'src/**/index.ts',
      ],
    },
    testTimeout: 10000,
    hookTimeout: 10000,
  },
});
