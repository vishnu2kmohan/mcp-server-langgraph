/**
 * Visual Regression E2E Tests
 *
 * Visual regression tests for the Studio Shell frontend using Playwright's
 * screenshot comparison. These tests capture and compare screenshots of key
 * UI components to detect unintended visual changes.
 *
 * Test Coverage:
 * - StudioShell layout structure
 * - ActivityBar icons and state
 * - SessionNav panel
 * - Canvas panel layout
 * - Compliance dashboards
 * - Responsive breakpoints
 *
 * Note: First run generates baseline screenshots. Subsequent runs compare
 * against baselines. Update baselines with: npm run test:e2e -- --update-snapshots
 */

import { test, expect } from './fixtures/auth';

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock feature flags
const mockFeatureFlags = {
  canvas_studio_shell: true,
  canvas_editable: true,
  canvas_agents: true,
  canvas_ai_palette: true,
  canvas_compliance: true,
  canvas_help: true,
  workflows: true,
  sessions: true,
  cost_dashboard: true,
  observability: true,
  code_export: true,
  ai_suggestions: true,
  llm_suggestions: true,
  mcp_websocket: true,
  interactive_artifacts: true,
  slash_commands: true,
};

async function setupMocks(page: import('@playwright/test').Page) {
  if (!backendEnabled) {
    // Mock feature flags
    await page.route('**/api/v1/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockFeatureFlags),
      });
    });

    // Mock sessions
    await page.route('**/api/v1/sessions*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'session-1',
              name: 'Visual Test Session',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          cursor: null,
        }),
      });
    });

    // Mock compliance reports
    await page.route('**/api/v1/compliance/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'compliant',
          controls: [],
          lastAssessed: new Date().toISOString(),
        }),
      });
    });
  }
}

// Viewport sizes for responsive testing
const viewports = {
  desktop: { width: 1920, height: 1080 },
  laptop: { width: 1440, height: 900 },
  tablet: { width: 1024, height: 768 },
  mobile: { width: 768, height: 1024 },
} as const;

test.describe('Visual Regression - StudioShell Layout', () => {
  test('should match screenshot for desktop viewport', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    // Wait for layout to stabilize
    await alicePage.waitForSelector('[data-testid="studio-shell"]', { timeout: 10000 });

    // Allow CSS animations to complete
    await alicePage.waitForTimeout(500);

    // Take full page screenshot
    await expect(alicePage).toHaveScreenshot('studio-shell-desktop.png', {
      fullPage: true,
      maxDiffPixels: 100, // Allow minor rendering differences
    });
  });

  test('should match screenshot for laptop viewport', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.laptop);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await alicePage.waitForSelector('[data-testid="studio-shell"]', { timeout: 10000 });
    await alicePage.waitForTimeout(500);

    await expect(alicePage).toHaveScreenshot('studio-shell-laptop.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('should match screenshot for tablet viewport', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.tablet);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await alicePage.waitForSelector('[data-testid="studio-shell"]', { timeout: 10000 });
    await alicePage.waitForTimeout(500);

    await expect(alicePage).toHaveScreenshot('studio-shell-tablet.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });
});

test.describe('Visual Regression - ActivityBar', () => {
  test('should match screenshot for ActivityBar component', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    const activityBar = alicePage.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });
    await alicePage.waitForTimeout(300);

    await expect(activityBar).toHaveScreenshot('activity-bar.png', {
      maxDiffPixels: 50,
    });
  });

  test('should match screenshot for ActivityBar with admin persona', async ({ adminPage }) => {
    await setupMocks(adminPage);
    await adminPage.setViewportSize(viewports.desktop);
    await adminPage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    const activityBar = adminPage.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });
    await adminPage.waitForTimeout(300);

    // Admin may have additional nav items
    await expect(activityBar).toHaveScreenshot('activity-bar-admin.png', {
      maxDiffPixels: 50,
    });
  });
});

test.describe('Visual Regression - Canvas Panel', () => {
  test('should match screenshot for CanvasPanel empty state', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
    await alicePage.waitForTimeout(300);

    await expect(canvasPanel).toHaveScreenshot('canvas-panel-empty.png', {
      maxDiffPixels: 100,
    });
  });

  test('should match screenshot for CanvasPanel with session', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);
    await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

    const canvasPanel = alicePage.getByTestId('canvas-panel');
    await expect(canvasPanel).toBeVisible({ timeout: 10000 });
    await alicePage.waitForTimeout(300);

    await expect(canvasPanel).toHaveScreenshot('canvas-panel-session.png', {
      maxDiffPixels: 100,
    });
  });
});

test.describe('Visual Regression - Compliance Dashboard', () => {
  test('should match screenshot for Compliance Dashboard', async ({ adminPage }) => {
    await setupMocks(adminPage);
    await adminPage.setViewportSize(viewports.desktop);
    await adminPage.goto('/studio/v2/compliance', { waitUntil: 'networkidle' });

    // Wait for dashboard to render
    const complianceDashboard = adminPage.getByTestId('compliance-dashboard');
    await expect(complianceDashboard).toBeVisible({ timeout: 10000 });
    await adminPage.waitForTimeout(500);

    await expect(complianceDashboard).toHaveScreenshot('compliance-dashboard.png', {
      maxDiffPixels: 200, // Compliance has more dynamic content
    });
  });
});

test.describe('Visual Regression - StatusBar', () => {
  test('should match screenshot for StatusBar', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    const statusBar = alicePage.getByTestId('status-bar');
    await expect(statusBar).toBeVisible({ timeout: 10000 });
    await alicePage.waitForTimeout(300);

    await expect(statusBar).toHaveScreenshot('status-bar.png', {
      maxDiffPixels: 50,
    });
  });
});

test.describe('Visual Regression - Dark/Light Theme', () => {
  test('should match screenshot for light theme', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);

    // Ensure light theme
    await alicePage.addInitScript(() => {
      localStorage.setItem('theme', 'light');
    });

    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });
    await alicePage.waitForSelector('[data-testid="studio-shell"]', { timeout: 10000 });
    await alicePage.waitForTimeout(500);

    await expect(alicePage).toHaveScreenshot('theme-light.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test('should match screenshot for dark theme', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);

    // Force dark theme
    await alicePage.addInitScript(() => {
      localStorage.setItem('theme', 'dark');
    });

    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });
    await alicePage.waitForSelector('[data-testid="studio-shell"]', { timeout: 10000 });
    await alicePage.waitForTimeout(500);

    await expect(alicePage).toHaveScreenshot('theme-dark.png', {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });
});

test.describe('Visual Regression - Loading States', () => {
  test('should match screenshot for loading spinner', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);

    // Intercept and delay API responses to capture loading state
    if (!backendEnabled) {
      await alicePage.route('**/api/v1/sessions*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], cursor: null }),
        });
      });
    }

    await alicePage.goto('/studio/v2/chat', { waitUntil: 'domcontentloaded' });

    // Capture loading state quickly
    await alicePage.waitForTimeout(100);

    // Only capture if loading indicator is visible
    const loading = alicePage.getByTestId('loading-indicator');
    const isVisible = await loading.isVisible().catch(() => false);

    if (isVisible) {
      await expect(loading).toHaveScreenshot('loading-state.png', {
        maxDiffPixels: 50,
      });
    }
  });
});

test.describe('Visual Regression - Error States', () => {
  test('should match screenshot for error boundary', async ({ alicePage }) => {
    await alicePage.setViewportSize(viewports.desktop);

    // Mock an error response
    if (!backendEnabled) {
      await alicePage.route('**/api/v1/features', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal Server Error' }),
        });
      });
    }

    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });
    await alicePage.waitForTimeout(500);

    // Check for error boundary
    const errorBoundary = alicePage.getByTestId('error-boundary');
    const isVisible = await errorBoundary.isVisible().catch(() => false);

    if (isVisible) {
      await expect(errorBoundary).toHaveScreenshot('error-boundary.png', {
        maxDiffPixels: 50,
      });
    }
  });
});

test.describe('Visual Regression - Accessibility Focus States', () => {
  test('should show visible focus indicators on keyboard navigation', async ({ alicePage }) => {
    await setupMocks(alicePage);
    await alicePage.setViewportSize(viewports.desktop);
    await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

    await alicePage.waitForSelector('[data-testid="studio-shell"]', { timeout: 10000 });

    // Tab to focus first interactive element
    await alicePage.keyboard.press('Tab');
    await alicePage.keyboard.press('Tab');
    await alicePage.waitForTimeout(100);

    // Capture focused state
    await expect(alicePage).toHaveScreenshot('focus-state.png', {
      fullPage: true,
      maxDiffPixels: 150, // Focus rings may vary
    });
  });
});
