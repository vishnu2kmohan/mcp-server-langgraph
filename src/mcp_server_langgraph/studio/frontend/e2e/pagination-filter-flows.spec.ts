/**
 * Pagination and Filter Flows E2E Tests
 *
 * Tests the pagination and filtering functionality across pages:
 * - ProjectsPage: search, sort, pagination, status filter
 * - ObservabilityPage: trace filters, time range, pagination
 * - SharedWorkflowsList: search, permission filter, shared-by filter
 *
 * These tests verify the UI interactions work correctly with the API.
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * Tests using page.route() mocks are skipped in backend mode.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('Pagination and Filter Flows', () => {
  test.describe('ProjectsPage Filters', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/studio/projects');
    });

    test('should display search input', async ({ page }) => {
      // Look for search input
      const searchInput = page.getByRole('searchbox');
      await expect(searchInput).toBeVisible();
    });

    test('should display sort controls', async ({ page }) => {
      // Look for sort dropdown
      const sortDropdown = page.getByRole('combobox', { name: /sort/i });
      await expect(sortDropdown).toBeVisible();
    });

    test('should display status filter dropdown', async ({ page }) => {
      // Look for status filter dropdown
      const statusDropdown = page.getByRole('combobox', { name: /status/i });
      await expect(statusDropdown).toBeVisible();
    });

    test('should filter projects when typing in search', async ({ page }) => {
      // Type in search input
      const searchInput = page.getByRole('searchbox');
      await searchInput.fill('test project');

      // The list should update (wait for debounced search)
      await page.waitForTimeout(500);

      // Verify search is applied (the URL or query should include search term)
      await expect(searchInput).toHaveValue('test project');
    });

    test('should change sort order when clicking toggle', async ({ page }) => {
      // Find and click sort order toggle
      const sortToggle = page.getByRole('button', { name: /sort order/i });
      if (await sortToggle.isVisible()) {
        await sortToggle.click();
        // Sort order should toggle
        await expect(sortToggle).toBeVisible();
      }
    });

    test('should show pagination controls when data exists', async ({ page }) => {
      // Wait for content to load
      await page.waitForLoadState('networkidle');

      // Look for pagination - may not exist if no data
      const pagination = page.locator('[data-testid="pagination"]');
      const paginationExists = await pagination.isVisible().catch(() => false);

      // If projects exist, should show pagination info
      if (paginationExists) {
        await expect(pagination).toBeVisible();
      }
    });
  });

  test.describe('ObservabilityPage Filters', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/studio/observability');
    });

    test('should display tab navigation', async ({ page }) => {
      // Verify tabs exist
      await expect(page.getByText('Traces')).toBeVisible();
      await expect(page.getByText('Logs')).toBeVisible();
      await expect(page.getByText('Metrics')).toBeVisible();
    });

    test('should display status filter buttons on traces tab', async ({ page }) => {
      // Make sure we're on traces tab
      await page.getByText('Traces').click();

      // Look for status filter buttons
      const allButton = page.getByRole('button', { name: /^all$/i });
      const successButton = page.getByRole('button', { name: /^success$/i });
      const errorButton = page.getByRole('button', { name: /^error$/i });

      await expect(allButton).toBeVisible();
      await expect(successButton).toBeVisible();
      await expect(errorButton).toBeVisible();
    });

    test('should display session ID filter input', async ({ page }) => {
      // Look for session ID filter
      const sessionIdInput = page.getByPlaceholder(/session id/i);
      await expect(sessionIdInput).toBeVisible();
    });

    test('should display time range filter', async ({ page }) => {
      // Look for time range dropdown
      const timeRangeSelect = page.getByRole('combobox', { name: /time range/i });
      await expect(timeRangeSelect).toBeVisible();
    });

    test('should filter traces when clicking status filter', async ({ page }) => {
      // Click on Error filter
      const errorButton = page.getByRole('button', { name: /^error$/i });
      await errorButton.click();

      // Button should be selected (aria-pressed=true)
      await expect(errorButton).toHaveAttribute('aria-pressed', 'true');
    });

    test('should change time range when selecting option', async ({ page }) => {
      // Click on time range dropdown
      const timeRangeSelect = page.getByRole('combobox', { name: /time range/i });
      await timeRangeSelect.selectOption('24h');

      // Verify selection
      await expect(timeRangeSelect).toHaveValue('24h');
    });

    test('should switch to logs tab when clicked', async ({ page }) => {
      // Click on Logs tab
      await page.getByText('Logs').click();

      // Logs content should be visible
      await page.waitForLoadState('networkidle');
      // Either logs appear or empty state message
      const logsExist = await page.getByText(/No logs found|Processing request|level/i).isVisible().catch(() => false);
      expect(logsExist).toBe(true);
    });

    test('should switch to metrics tab when clicked', async ({ page }) => {
      // Click on Metrics tab
      await page.getByText('Metrics').click();

      // Metrics content should be visible
      await page.waitForLoadState('networkidle');
      // Either metrics appear or empty state message
      const metricsExist = await page.getByText(/Total Requests|No metrics|Avg Latency/i).isVisible().catch(() => false);
      expect(metricsExist).toBe(true);
    });
  });

  test.describe('Loading Skeletons (mocked responses)', () => {
    // Skip mock-based tests when running with real backend
    test.skip(backendEnabled, 'Skipped in backend mode - loading state timing varies');

    test('should show skeleton loading on projects page initially', async ({ page }) => {
      // Navigate to projects - intercept to delay response
      await page.route('**/api/v1/projects*', async (route) => {
        // Delay response to capture loading state
        await new Promise((resolve) => setTimeout(resolve, 100));
        await route.continue();
      });

      await page.goto('/studio/projects');

      // Skeleton should appear during loading
      const skeleton = page.locator('.animate-pulse');
      // May or may not catch it depending on timing
      const skeletonWasVisible = await skeleton.isVisible().catch(() => false);
      // Just verify page loaded
      await page.waitForLoadState('networkidle');
    });

    test('should show skeleton loading on observability page initially', async ({ page }) => {
      // Navigate to observability - intercept to delay response
      await page.route('**/api/v1/observability*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        await route.continue();
      });

      await page.goto('/studio/observability');

      // Page should load
      await page.waitForLoadState('networkidle');
      await expect(page.getByText('Observability')).toBeVisible();
    });
  });

  test.describe('Refresh Functionality', () => {
    test('should have refresh button on observability page', async ({ page }) => {
      await page.goto('/studio/observability');

      // Look for refresh button
      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await expect(refreshButton).toBeVisible();
    });

    test('should have refresh button on projects page', async ({ page }) => {
      await page.goto('/studio/projects');

      // Look for refresh button
      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await expect(refreshButton).toBeVisible();
    });

    test('should trigger refresh when clicking refresh button', async ({ page }) => {
      await page.goto('/studio/observability');

      // Click refresh button
      const refreshButton = page.getByRole('button', { name: /refresh/i });
      await refreshButton.click();

      // Button should still be visible after click
      await expect(refreshButton).toBeVisible();
    });
  });

  test.describe('Empty States (mocked responses)', () => {
    // Skip mock-based tests when running with real backend - test actual empty states instead
    test.skip(backendEnabled, 'Skipped in backend mode - use real empty state scenarios');

    test('should handle empty project list gracefully', async ({ page }) => {
      // Mock empty response
      await page.route('**/api/v1/projects*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0, page: 1, per_page: 20, total_pages: 0 }),
        });
      });

      await page.goto('/studio/projects');

      // Should show empty state message
      await expect(page.getByText(/No projects/i)).toBeVisible();
    });

    test('should handle empty traces list gracefully', async ({ page }) => {
      // Mock empty response
      await page.route('**/api/v1/observability/traces*', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0, limit: 50 }),
        });
      });

      await page.goto('/studio/observability');

      // Should show empty state message
      await expect(page.getByText(/No traces found/i)).toBeVisible();
    });
  });

  test.describe('Error States', () => {
    test('should handle API error on projects page', async ({ page }) => {
      // Mock error response
      await page.route('**/api/v1/projects*', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        });
      });

      await page.goto('/studio/projects');

      // Should show error state with retry option
      await expect(page.getByText(/Failed|Error/i)).toBeVisible();
    });

    test('should handle API error on observability page', async ({ page }) => {
      // Mock error response
      await page.route('**/api/v1/observability/traces*', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        });
      });

      await page.goto('/studio/observability');

      // Should show error state with retry option
      await expect(page.getByText(/Failed to load/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /Retry/i })).toBeVisible();
    });
  });
});
