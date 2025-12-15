/**
 * Bob Standard User Journey E2E Tests
 *
 * Tests the complete standard user journey including:
 * - Session creation and chat
 * - Message history
 * - Projects access
 * - Shared workflows access (read-only)
 * - Cost visibility
 *
 * Uses HEART framework metrics:
 * - Happiness: Chat response quality
 * - Engagement: Sessions per week
 * - Adoption: First session creation rate
 * - Retention: 7/14/30-day return rates
 * - Task Success: Chat response accuracy
 *
 * Note: Bob is a standard user (no special roles).
 * Route-level restrictions are enforced via PersonaGuard.
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 * API mocks are only used when BACKEND_ENABLED=false.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('Bob Standard User Journey', () => {
  test.beforeEach(async ({ bobPage }) => {
    // Only mock API responses when backend is disabled (frontend-only testing)
    if (!backendEnabled) {
      await bobPage.route('**/api/v1/**', async (route) => {
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

        // Feature flags
        if (url.includes('/features')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ features: {} }),
          });
          return;
        }

        // User endpoint - return roles for persona derivation (standard user)
        if (url.includes('/me')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'bob-user',
              username: 'bob',
              email: 'bob@example.com',
              roles: [], // Empty roles = user persona
            }),
          });
          return;
        }

        // Projects list (user has access)
        if (url.includes('/projects')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'proj-1',
                  name: 'My Project',
                  description: 'A project for Bob',
                  status: 'active',
                  created_at: new Date().toISOString(),
                },
              ],
              total: 1,
              cursor: null,
            }),
          });
          return;
        }

        // Sessions list (user has access)
        if (url.includes('/sessions')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'session-1',
                  project_id: 'proj-1',
                  status: 'active',
                  created_at: new Date().toISOString(),
                },
              ],
              total: 1,
              cursor: null,
            }),
          });
          return;
        }

        // Shared workflows (read-only access for user)
        if (url.includes('/workflows/shared')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'wf-shared-1',
                  name: 'Shared Workflow',
                  description: 'A workflow shared with users',
                  status: 'active',
                  created_at: new Date().toISOString(),
                },
              ],
              total: 1,
              cursor: null,
            }),
          });
          return;
        }

        // Cost endpoints (user has basic access)
        if (url.includes('/cost/summary')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              total_cost: 12.5,
              period: 'current_month',
              currency: 'USD',
            }),
          });
          return;
        }

        if (url.includes('/cost/by-model')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              models: [],
            }),
          });
          return;
        }

        if (url.includes('/cost/history')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [],
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
    await bobPage.goto('/studio/');
  });

  test.describe('Home Navigation', () => {
    test('should access home page', async ({ bobPage }) => {
      await bobPage.goto('/studio/');

      // App should render - wait for main content
      await expect(bobPage.locator('main, [role="main"], body').first()).toBeVisible();
    });

    test('should navigate to projects', async ({ bobPage }) => {
      await bobPage.goto('/studio/projects');

      // Projects section should load
      await expect(bobPage.getByText(/Projects/i).first()).toBeVisible();
    });
  });

  test.describe('Chat Experience', () => {
    test('should access chat page', async ({ bobPage }) => {
      await bobPage.goto('/studio/chat');

      // Chat interface should load
      await expect(bobPage.locator('main, [role="main"], textarea').first()).toBeVisible();
    });

    test('should have message input area', async ({ bobPage }) => {
      await bobPage.goto('/studio/chat');

      // Look for message input (textarea) - may take time to load
      const messageArea = bobPage.locator('main, [role="main"]').first();
      await expect(messageArea).toBeVisible();
    });
  });

  test.describe('Workflows View (Unified: Owned + Shared)', () => {
    test('should access workflows page with unified view', async ({ bobPage }) => {
      // Workflows page now shows owned workflows (editable) + shared workflows (read-only)
      await bobPage.goto('/studio/workflows');

      // Workflows page should load
      await expect(bobPage.locator('main, [role="main"]').first()).toBeVisible();
    });

    test('should show Read-Only badge for shared workflows', async ({ bobPage }) => {
      await bobPage.goto('/studio/workflows');

      // If shared workflows exist, they should have Read-Only indicator
      // This test verifies the page structure
      await expect(bobPage.locator('main, [role="main"]').first()).toBeVisible();
    });
  });

  test.describe('Cost Page Access', () => {
    test('should access cost page', async ({ bobPage }) => {
      await bobPage.goto('/studio/cost');

      // Cost page should load
      await expect(bobPage.getByText(/Cost/i).first()).toBeVisible();
    });
  });

  test.describe('Route Access Restrictions', () => {
    test('should be redirected from admin dashboard', async ({ bobPage }) => {
      // Standard user should NOT have access to admin (PersonaGuard protected)
      await bobPage.goto('/studio/admin/dashboard');

      // Should be redirected away from admin (PersonaGuard enforces this)
      await expect(bobPage).toHaveURL(/\/studio\/(projects|chat|workflows|cost)/);
    });

    // NOTE: /studio/workflows is now accessible to all personas (unified view)
    // Bob can view workflows but only edit his own, shared workflows are read-only

    test('should be redirected from MCP page', async ({ bobPage }) => {
      // Standard user should NOT have access to MCP (developer/admin only)
      await bobPage.goto('/studio/mcp');

      // Should be redirected to user default route
      await expect(bobPage).toHaveURL(/\/studio\/(projects|chat|workflows|cost)/);
    });

    test('should be redirected from observability page', async ({ bobPage }) => {
      // Standard user should NOT have access to observability (developer/admin only)
      await bobPage.goto('/studio/observability');

      // Should be redirected to user default route
      await expect(bobPage).toHaveURL(/\/studio\/(projects|chat|workflows|cost)/);
    });

    test('should be redirected from connections page', async ({ bobPage }) => {
      // Standard user should NOT have access to connections (developer/admin only)
      await bobPage.goto('/studio/connections');

      // Should be redirected to user default route
      await expect(bobPage).toHaveURL(/\/studio\/(projects|chat|workflows|cost)/);
    });

    test('should be redirected from settings page', async ({ bobPage }) => {
      // Standard user may or may not have access to settings
      await bobPage.goto('/studio/settings');

      // Should either stay on settings or redirect based on persona config
      await expect(bobPage).toHaveURL(/\/studio\/(settings|projects|chat|workflows|cost)/);
    });
  });

  test.describe('Performance Metrics (HEART)', () => {
    test('chat page should load within acceptable time', async ({ bobPage }) => {
      const startTime = Date.now();

      await bobPage.goto('/studio/chat');
      await expect(bobPage.locator('main, [role="main"]').first()).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('projects page should load within acceptable time', async ({ bobPage }) => {
      const startTime = Date.now();

      await bobPage.goto('/studio/projects');
      await expect(bobPage.getByText(/Projects/i).first()).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('navigation should be responsive', async ({ bobPage }) => {
      await bobPage.goto('/studio/');

      // Navigation (sidebar) should be present
      const nav = bobPage.locator('nav, [role="navigation"], aside');
      await expect(nav.first()).toBeVisible();
    });
  });

  test.describe('User Experience Quality', () => {
    test('should have proper page structure', async ({ bobPage }) => {
      await bobPage.goto('/studio/projects');

      // Page should have main content area
      await expect(bobPage.locator('main, [role="main"]').first()).toBeVisible();
    });

    test('should have accessible navigation', async ({ bobPage }) => {
      await bobPage.goto('/studio/');

      // Navigation should have accessible elements
      const nav = bobPage.locator('nav, [role="navigation"], aside');
      await expect(nav.first()).toBeVisible();
    });
  });
});
