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
 *
 * Resource Management:
 * - PW_WORKERS: Override worker count (e.g., PW_WORKERS=4)
 * - PW_BROWSERS: Limit browsers (e.g., PW_BROWSERS=chromium)
 * - CI=true: Uses 2 workers, all browsers, 2 retries
 *
 * Examples:
 *   npm run test:e2e                     # All browsers, auto workers
 *   npm run test:e2e:chromium            # Chromium only (fast local dev)
 *   PW_WORKERS=2 npm run test:e2e        # Limit workers
 */

import { defineConfig, devices } from "@playwright/test";
import os from "os";

// =============================================================================
// Adaptive Resource Configuration
// =============================================================================
// Each browser instance uses ~300-500MB. Calculate workers based on:
// 1. Available CPUs (Playwright default: 50% of cores)
// 2. Available memory (browsers are heavy)
// 3. CI environment (more conservative)
// =============================================================================

function getOptimalWorkerCount(): number | string {
  // Priority 1: Explicit environment variable
  const envWorkers = process.env.PW_WORKERS;
  if (envWorkers) {
    // Support percentage strings like "50%"
    if (envWorkers.endsWith("%")) {
      return envWorkers;
    }
    const parsed = parseInt(envWorkers, 10);
    if (!isNaN(parsed) && parsed > 0) {
      return parsed;
    }
  }

  // Priority 2: CI mode - conservative settings
  const isCI =
    process.env.CI === "true" || process.env.GITHUB_ACTIONS === "true";
  if (isCI) {
    // CI: Use 2 workers for parallel browser testing with resource constraints
    return 2;
  }

  // Priority 3: Calculate based on resources
  const cpuCount = os.availableParallelism?.() ?? os.cpus().length;
  const freeMemoryGB = os.freemem() / 1024 / 1024 / 1024;

  // Each browser worker uses ~400MB (browser + test runner)
  const memoryPerWorkerGB = 0.4;
  // Use at most 40% of free memory (browsers are heavier than vitest workers)
  const memoryBasedLimit = Math.floor((freeMemoryGB * 0.4) / memoryPerWorkerGB);

  // CPU-based: Playwright's default is 50% of cores, we'll use that
  const cpuBasedLimit = Math.floor(cpuCount * 0.5);

  // Take minimum, with floor of 1 and ceiling of 8 for E2E tests
  // (E2E tests are I/O bound, not CPU bound, so more workers != faster)
  const optimal = Math.max(1, Math.min(cpuBasedLimit, memoryBasedLimit, 8));

  return optimal;
}

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";
const isCI = process.env.CI === "true" || process.env.GITHUB_ACTIONS === "true";

// Timeout configuration based on mode
const actionTimeout = backendEnabled ? 30000 : 10000;
const navigationTimeout = backendEnabled ? 60000 : 30000;

// Worker configuration with adaptive resource management
const workers = getOptimalWorkerCount();

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: isCI ? 2 : 0,
  workers,
  timeout: backendEnabled ? 60000 : 30000,
  // Fail fast in CI to save resources
  maxFailures: isCI ? 5 : undefined,
  reporter: [["html", { outputFolder: "playwright-report" }], ["list"]],
  use: {
    // Base URL matches vite.config.ts (port 5175, base /studio/)
    baseURL: process.env.FRONTEND_URL || "http://localhost:5175/studio",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout,
    navigationTimeout,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    // URL matches vite.config.ts server port and base path
    url: "http://localhost:5175/studio/",
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  // Global setup/teardown for backend integration
  ...(backendEnabled && {
    globalSetup: "./e2e/fixtures/global-setup.ts",
    globalTeardown: "./e2e/fixtures/global-teardown.ts",
  }),
});
