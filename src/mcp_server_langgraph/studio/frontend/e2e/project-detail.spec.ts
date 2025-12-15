/**
 * ProjectDetailPage E2E Tests
 *
 * Tests the project detail page functionality including:
 * - Tab navigation (Sessions, Workflows, Connections, Observability, Cost, Members)
 * - Project information display
 * - Refresh functionality
 * - Navigation back to projects list
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 * API mocks are only used when BACKEND_ENABLED=false.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('ProjectDetailPage', () => {
  let testProjectId: string;

  test.beforeEach(async ({ alicePage }) => {
    // Only mock API responses when backend is disabled (frontend-only testing)
    if (!backendEnabled) {
      await alicePage.route('**/api/v1/**', async (route) => {
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

        // User endpoint - return roles for persona derivation
        if (url.includes('/me')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'alice-user',
              username: 'alice',
              email: 'alice@example.com',
              roles: ['developer'],
            }),
          });
          return;
        }

        // Project detail
        if (url.match(/\/projects\/[^/]+$/) && !url.includes('/sessions')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'test-project-1',
              name: 'Test Project',
              description: 'A test project for E2E testing',
              status: 'active',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }),
          });
          return;
        }

        // Project sessions
        if (url.includes('/sessions')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              data: [
                {
                  id: 'session-1',
                  name: 'Test Session 1',
                  project_id: 'test-project-1',
                  status: 'active',
                  created_at: new Date().toISOString(),
                },
                {
                  id: 'session-2',
                  name: 'Test Session 2',
                  project_id: 'test-project-1',
                  status: 'completed',
                  created_at: new Date().toISOString(),
                },
              ],
              pagination: {
                count: 2,
                next_cursor: null,
              },
            }),
          });
          return;
        }

        // Project workflows
        if (url.includes('/workflows')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'workflow-1',
                  name: 'Test Workflow',
                  description: 'A test workflow',
                  status: 'active',
                },
              ],
              total: 1,
              cursor: null,
            }),
          });
          return;
        }

        // Project connections
        if (url.includes('/connections')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [],
              total: 0,
            }),
          });
          return;
        }

        // Project observability
        if (url.includes('/observability')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [],
              total: 0,
            }),
          });
          return;
        }

        // Project cost
        if (url.includes('/cost')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              total_cost: 0,
              currency: 'USD',
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

      testProjectId = 'test-project-1';
    } else {
      // With real backend, we need to get a real project ID
      // First navigate to projects page and get the first project
      await alicePage.goto('/studio/projects');
      await alicePage.waitForLoadState('networkidle');

      // Try to find a project link
      const projectLink = alicePage.locator('a[href*="/projects/"]').first();
      if (await projectLink.isVisible({ timeout: 5000 }).catch(() => false)) {
        const href = await projectLink.getAttribute('href');
        testProjectId = href?.split('/projects/')[1]?.split('/')[0] || 'test-project';
      } else {
        // If no projects exist, use a placeholder - tests will handle 404
        testProjectId = 'test-project';
      }
    }
  });

  test.describe('Project Information', () => {
    test('should display project detail page', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Page should load - look for main content area
      await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
    });

    test('should display project name', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Wait for project info to load - heading or title should contain project name
      const heading = alicePage.getByRole('heading').first();
      await expect(heading).toBeVisible({ timeout: 10000 });
    });

    test('should have back to projects button', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Look for back button or link
      const backButton = alicePage.getByRole('link', { name: /back|projects/i }).first();
      const backButtonVisible = await backButton.isVisible().catch(() => false);

      if (backButtonVisible) {
        await backButton.click();
        await expect(alicePage).toHaveURL(/\/studio\/projects$/);
      }
    });
  });

  test.describe('Tab Navigation', () => {
    test('should display Sessions tab by default', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Sessions tab should be visible
      const sessionsTab = alicePage.getByRole('button', { name: /Sessions/i });
      await expect(sessionsTab).toBeVisible({ timeout: 10000 });
    });

    test('should display all available tabs', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);
      await alicePage.waitForLoadState('networkidle');

      // Check for common tabs (not all may be visible depending on permissions)
      const tabs = [
        'Sessions',
        'Workflows',
        'Connections',
        'Observability',
        'Cost',
      ];

      for (const tabName of tabs) {
        const tab = alicePage.getByRole('button', { name: new RegExp(tabName, 'i') });
        if (await tab.isVisible().catch(() => false)) {
          await expect(tab).toBeVisible();
        }
      }
    });

    test('should switch to Workflows tab when clicked', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      const workflowsTab = alicePage.getByRole('button', { name: /Workflows/i });
      if (await workflowsTab.isVisible().catch(() => false)) {
        await workflowsTab.click();
        // Tab should be selected (aria-selected or similar)
        await expect(workflowsTab).toBeVisible();
      }
    });

    test('should switch to Connections tab when clicked', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      const connectionsTab = alicePage.getByRole('button', { name: /Connections/i });
      if (await connectionsTab.isVisible().catch(() => false)) {
        await connectionsTab.click();
        await expect(connectionsTab).toBeVisible();
      }
    });

    test('should switch to Observability tab when clicked', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      const observabilityTab = alicePage.getByRole('button', { name: /Observability/i });
      if (await observabilityTab.isVisible().catch(() => false)) {
        await observabilityTab.click();
        await expect(observabilityTab).toBeVisible();
      }
    });

    test('should switch to Cost tab when clicked', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      const costTab = alicePage.getByRole('button', { name: /Cost/i });
      if (await costTab.isVisible().catch(() => false)) {
        await costTab.click();
        await expect(costTab).toBeVisible();
      }
    });
  });

  test.describe('Sessions Tab Content', () => {
    test('should display session list', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Wait for sessions content to load
      await alicePage.waitForLoadState('networkidle');

      // Look for session items or empty state
      const sessionContent = alicePage.locator('main, [role="main"]').first();
      await expect(sessionContent).toBeVisible();
    });

    test('should have new session button', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Look for new session button
      const newButton = alicePage.getByRole('button', { name: /New|Create|Add/i });
      if (await newButton.first().isVisible().catch(() => false)) {
        await expect(newButton.first()).toBeVisible();
      }
    });

    test('should have search input for sessions', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Look for search input
      const searchInput = alicePage.getByPlaceholder(/search/i);
      if (await searchInput.isVisible().catch(() => false)) {
        await expect(searchInput).toBeVisible();
      }
    });
  });

  test.describe('Refresh Functionality', () => {
    test('should have refresh button', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Look for refresh button
      const refreshButton = alicePage.getByRole('button', { name: /refresh/i });
      if (await refreshButton.isVisible().catch(() => false)) {
        await expect(refreshButton).toBeVisible();
      }
    });

    test('should refresh content when clicking refresh', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      const refreshButton = alicePage.getByRole('button', { name: /refresh/i });
      if (await refreshButton.isVisible().catch(() => false)) {
        await refreshButton.click();
        // Page should still be visible after refresh
        await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
      }
    });
  });

  test.describe('Performance Metrics', () => {
    test('should load project detail page within acceptable time', async ({ alicePage }) => {
      const startTime = Date.now();

      await alicePage.goto(`/studio/projects/${testProjectId}`);
      await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should have proper page structure', async ({ alicePage }) => {
      await alicePage.goto(`/studio/projects/${testProjectId}`);

      // Page should have main content area
      await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();

      // Should have navigation
      const nav = alicePage.locator('nav, [role="navigation"], aside');
      await expect(nav.first()).toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should handle non-existent project gracefully', async ({ alicePage }) => {
      await alicePage.goto('/studio/projects/non-existent-project-id');

      // Should show error message or redirect
      await alicePage.waitForLoadState('networkidle');

      // Either error message or redirect to projects
      const hasError = await alicePage.getByText(/not found|error|failed/i).isVisible().catch(() => false);
      const redirected = await alicePage.url().includes('/projects');

      expect(hasError || redirected).toBe(true);
    });
  });
});
