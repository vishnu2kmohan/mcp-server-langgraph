/**
 * Playwright E2E Test Configuration
 *
 * Configuration for browser-based E2E tests covering user journeys
 * for admin, alice (power user), and bob (standard user).
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API to catch
 * contract mismatches between frontend and backend.
 *
 * To run E2E tests:
 * 1. Start test infrastructure: `make test-infra-up-build`
 * 2. Run tests: `npm run test:e2e`
 *
 * Environment Variables:
 * - FRONTEND_URL: Override frontend URL (default: http://localhost:5175)
 * - BACKEND_ENABLED: Backend integration mode (default: true)
 * - KEYCLOAK_URL: Keycloak server URL (default: http://localhost:9082)
 * - KEYCLOAK_REALM: Keycloak realm name (default: default)
 * - API_URL: Backend API URL (default: http://localhost:8003)
 */

import { defineConfig, devices } from '@playwright/test';

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Timeout configuration based on mode
const actionTimeout = backendEnabled ? 30000 : 10000;
const navigationTimeout = backendEnabled ? 60000 : 30000;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: backendEnabled ? 60000 : 30000,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    // Base URL matches vite.config.ts (port 5175, base /studio/)
    baseURL: process.env.FRONTEND_URL || 'http://localhost:5175/studio',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout,
    navigationTimeout,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    // URL matches vite.config.ts server port and base path
    url: 'http://localhost:5175/studio/',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  // Global setup/teardown for backend integration
  ...(backendEnabled && {
    globalSetup: './e2e/fixtures/global-setup.ts',
    globalTeardown: './e2e/fixtures/global-teardown.ts',
  }),
});
