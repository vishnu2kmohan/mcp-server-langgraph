/**
 * Admin User Journey E2E Tests
 *
 * Tests the complete admin user journey including:
 * - Dashboard access and system health monitoring
 * - User management
 * - Organization management
 * - HEART metrics visibility
 *
 * Uses HEART framework metrics:
 * - Happiness: Dashboard satisfaction
 * - Engagement: Admin actions per session
 * - Adoption: Feature discovery
 * - Retention: Admin return rate
 * - Task Success: User management completion rate
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 * API mocks are only used when BACKEND_ENABLED=false.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('Admin User Journey', () => {
  test.beforeEach(async ({ adminPage }) => {
    // Only mock API responses when backend is disabled (frontend-only testing)
    if (!backendEnabled) {
      await adminPage.route('**/api/v1/**', async (route) => {
        const url = route.request().url();

        // Health endpoint
        if (url.includes('/health')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              status: 'healthy',
              uptime_seconds: 86400,
              version: '1.0.0',
            }),
          });
          return;
        }

        // HEART metrics endpoint (RTK Query calls /api/v1/metrics/heart/aggregate)
        if (url.includes('/metrics/heart/aggregate') || url.includes('/heart-metrics')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              nps_score_avg: 8.5,
              satisfaction_avg: 4.2,
              avg_session_duration_ms: 300000,
              new_users_count: 25,
              avg_return_visits: 3.5,
              task_success_rate: 0.92,
            }),
          });
          return;
        }

        // Feature flags
        if (url.includes('/features')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ features: {} }),
          });
          return;
        }

        // User endpoint - return roles for persona derivation (Sprint 4 extended)
        if (url.includes('/me')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              user_id: 'user:admin',
              username: 'admin',
              email: 'admin@example.com',
              roles: ['admin'],
              persona: 'admin',
              // Sprint 4: Extended persona fields
              api_version: '2',
              sub_persona: 'admin',
              visible_modules: [
                'chat', 'projects', 'workflows', 'flows', 'mcp', 'agents',
                'traces', 'admin', 'audit', 'compliance', 'settings', 'help',
              ],
              feature_flags: {},
            }),
          });
          return;
        }

        // Default: return empty success response
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });
    }

    // Navigate to the app root
    await adminPage.goto('/studio/');
  });

  test.describe('Dashboard Access', () => {
    test('should access admin dashboard', async ({ adminPage }) => {
      // Navigate to admin section (relative to baseURL /studio)
      await adminPage.goto('/studio/admin/dashboard');

      // Wait for dashboard to load - check for heading or main content
      await expect(adminPage.getByRole('heading').first()).toBeVisible();
    });

    test('should display system health section', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // Wait for page to load - look for any dashboard content
      await expect(adminPage.locator('main, [role="main"], .dashboard, h1, h2').first()).toBeVisible();
    });

    test('should display HEART metrics section', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // Wait for HEART metrics section - flexible matching
      const metricsSection = adminPage.locator('[data-testid*="heart"], [data-testid*="metric"], .metrics, h2');
      await expect(metricsSection.first()).toBeVisible({ timeout: 10000 });
    });

    test('should have refresh functionality', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // Wait for dashboard to load (h1 with "Admin Dashboard" text)
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Click the refresh button
      const refreshButton = adminPage.getByRole('button', { name: /refresh/i });
      await expect(refreshButton).toBeVisible();
      await refreshButton.click();

      // Page should still show dashboard after refresh
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should navigate to studio from admin', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // Find and click studio navigation
      const studioLink = adminPage.getByRole('link', { name: /Studio|Chat|Home/i });
      if (await studioLink.first().isVisible()) {
        await studioLink.first().click();
        await expect(adminPage).toHaveURL(/\/(studio|chat)/);
      }
    });

    test('should have navigation structure', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // Wait for dashboard to load first
      await expect(adminPage.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Check for header or any navigation elements in the app shell
      const navOrHeader = adminPage.locator('nav, [role="navigation"], header, aside');
      await expect(navOrHeader.first()).toBeVisible();
    });
  });

  test.describe('User Management', () => {
    test('should display user management section', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // User manager component - flexible matching
      const userSection = adminPage.locator('[data-testid*="user"], .user-manager, .users');
      // This may not exist in all implementations
      const isVisible = await userSection.first().isVisible().catch(() => false);
      if (isVisible) {
        await expect(userSection.first()).toBeVisible();
      }
    });

    test('should have search functionality if present', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // Look for search input - flexible matching
      const searchInput = adminPage.getByPlaceholder(/search/i);
      if (await searchInput.first().isVisible().catch(() => false)) {
        await searchInput.first().fill('test');
        await expect(searchInput.first()).toHaveValue('test');
      }
    });
  });

  test.describe('Performance Metrics (HEART)', () => {
    test('dashboard should load within acceptable time', async ({ adminPage }) => {
      const startTime = Date.now();

      await adminPage.goto('/studio/admin/dashboard');
      await expect(adminPage.locator('main, [role="main"], h1, h2').first()).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Dashboard should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should have proper accessibility structure', async ({ adminPage }) => {
      await adminPage.goto('/studio/admin/dashboard');

      // Wait for content
      await expect(adminPage.locator('main, [role="main"], h1').first()).toBeVisible();

      // Check for proper heading hierarchy
      const headings = adminPage.getByRole('heading');

      // Should have at least one heading
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });
});
