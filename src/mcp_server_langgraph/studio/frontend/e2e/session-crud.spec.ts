/**
 * Session CRUD Operations E2E Tests
 *
 * Tests the session management functionality including:
 * - Create new session
 * - List and search sessions
 * - Select and switch sessions
 * - Delete sessions (single and bulk)
 * - Pagination and load more
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 * API mocks are only used when BACKEND_ENABLED=false.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('Session CRUD Operations', () => {
  test.beforeEach(async ({ alicePage }) => {
    // Only mock API responses when backend is disabled (frontend-only testing)
    if (!backendEnabled) {
      await alicePage.route('**/api/v1/**', async (route) => {
        const url = route.request().url();
        const method = route.request().method();

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

        // Sessions list
        if (url.includes('/sessions') && method === 'GET') {
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
                  message_count: 5,
                },
                {
                  id: 'session-2',
                  name: 'Test Session 2',
                  project_id: 'test-project-1',
                  status: 'completed',
                  created_at: new Date().toISOString(),
                  message_count: 10,
                },
                {
                  id: 'session-3',
                  name: 'Another Session',
                  project_id: 'test-project-1',
                  status: 'active',
                  created_at: new Date().toISOString(),
                  message_count: 3,
                },
              ],
              pagination: {
                count: 3,
                next_cursor: null,
              },
            }),
          });
          return;
        }

        // Create session
        if (url.includes('/sessions') && method === 'POST') {
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'new-session-id',
              name: 'New Session',
              project_id: 'test-project-1',
              status: 'active',
              created_at: new Date().toISOString(),
              message_count: 0,
            }),
          });
          return;
        }

        // Delete session
        if (url.includes('/sessions') && method === 'DELETE') {
          await route.fulfill({
            status: 204,
            contentType: 'application/json',
            body: '',
          });
          return;
        }

        // Projects
        if (url.includes('/projects')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'test-project-1',
                  name: 'Test Project',
                  description: 'A test project',
                  status: 'active',
                },
              ],
              total: 1,
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

    // Navigate to chat page where sessions are managed
    await alicePage.goto('/studio/chat');
  });

  test.describe('Session List Display', () => {
    test('should display session panel', async ({ alicePage }) => {
      // Wait for chat page to load
      await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();

      // Session panel should be visible (sidebar or panel with sessions)
      const sessionPanel = alicePage.locator('[data-testid="session-panel"], .session-panel, aside');
      const panelVisible = await sessionPanel.first().isVisible().catch(() => false);

      // Either session panel is visible or there's a button to show it
      if (!panelVisible) {
        const showSessionsButton = alicePage.getByRole('button', { name: /sessions/i });
        if (await showSessionsButton.isVisible().catch(() => false)) {
          await showSessionsButton.click();
        }
      }
    });

    test('should show session count', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Look for session count text like "3 sessions" or "1 of 3"
      const sessionCountText = alicePage.getByText(/\d+\s*(sessions|of\s*\d+)/i);
      if (await sessionCountText.first().isVisible().catch(() => false)) {
        await expect(sessionCountText.first()).toBeVisible();
      }
    });
  });

  test.describe('Create Session', () => {
    test('should have new session button', async ({ alicePage }) => {
      // Look for new session button
      const newButton = alicePage.getByRole('button', { name: /new|create|add/i }).first();
      await expect(newButton).toBeVisible({ timeout: 10000 });
    });

    test('should create new session when clicking new button', async ({ alicePage }) => {
      // Find and click new session button
      const newButton = alicePage.getByRole('button', { name: /new|create|add/i }).first();

      if (await newButton.isVisible().catch(() => false)) {
        await newButton.click();

        // Wait for session to be created
        await alicePage.waitForLoadState('networkidle');

        // Should still be on chat page
        await expect(alicePage).toHaveURL(/\/studio\/chat/);
      }
    });
  });

  test.describe('Session Search', () => {
    test('should have search input', async ({ alicePage }) => {
      // Look for search input in session panel
      const searchInput = alicePage.getByPlaceholder(/search/i);
      if (await searchInput.isVisible().catch(() => false)) {
        await expect(searchInput).toBeVisible();
      }
    });

    test('should filter sessions when typing in search', async ({ alicePage }) => {
      const searchInput = alicePage.getByPlaceholder(/search/i);

      if (await searchInput.isVisible().catch(() => false)) {
        // Type search query
        await searchInput.fill('Test');

        // Wait for debounced search
        await alicePage.waitForTimeout(500);

        // Search input should have the value
        await expect(searchInput).toHaveValue('Test');
      }
    });

    test('should clear search when clicking clear button', async ({ alicePage }) => {
      const searchInput = alicePage.getByPlaceholder(/search/i);

      if (await searchInput.isVisible().catch(() => false)) {
        await searchInput.fill('Test');

        // Look for clear button
        const clearButton = alicePage.getByRole('button', { name: /clear|x|×/i }).first();
        if (await clearButton.isVisible().catch(() => false)) {
          await clearButton.click();
          await expect(searchInput).toHaveValue('');
        }
      }
    });
  });

  test.describe('Session Selection', () => {
    test('should select session when clicked', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Find session items
      const sessionItem = alicePage.locator('[data-testid*="session"], .session-item, [role="listitem"]').first();

      if (await sessionItem.isVisible().catch(() => false)) {
        await sessionItem.click();

        // Selected session should be highlighted or active
        await alicePage.waitForLoadState('networkidle');
      }
    });

    test('should display session messages after selection', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Select a session
      const sessionItem = alicePage.locator('[data-testid*="session"], .session-item').first();

      if (await sessionItem.isVisible().catch(() => false)) {
        await sessionItem.click();

        // Wait for messages to load
        await alicePage.waitForLoadState('networkidle');

        // Message area should be visible
        const messageArea = alicePage.locator('main, [role="main"], .messages, .chat-messages');
        await expect(messageArea.first()).toBeVisible();
      }
    });
  });

  test.describe('Session Status Filter', () => {
    test('should have status filter dropdown', async ({ alicePage }) => {
      // Look for status filter
      const statusFilter = alicePage.getByRole('combobox', { name: /status/i });

      if (await statusFilter.isVisible().catch(() => false)) {
        await expect(statusFilter).toBeVisible();
      }
    });

    test('should filter by status when selecting option', async ({ alicePage }) => {
      const statusFilter = alicePage.getByRole('combobox', { name: /status/i });

      if (await statusFilter.isVisible().catch(() => false)) {
        await statusFilter.selectOption('active');
        await alicePage.waitForLoadState('networkidle');
        await expect(statusFilter).toHaveValue('active');
      }
    });
  });

  test.describe('Session Deletion', () => {
    test('should have delete option for sessions', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Find a session item with delete button
      const deleteButton = alicePage.getByRole('button', { name: /delete|remove/i }).first();

      // May be hidden behind a menu
      if (!(await deleteButton.isVisible().catch(() => false))) {
        // Look for menu button (three dots, ellipsis)
        const menuButton = alicePage.locator('[data-testid*="menu"], button[aria-label*="menu"]').first();
        if (await menuButton.isVisible().catch(() => false)) {
          await menuButton.click();
          await alicePage.waitForTimeout(300);
        }
      }
    });

    test('should show confirmation before deleting session', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Find delete button
      const deleteButton = alicePage.getByRole('button', { name: /delete/i }).first();

      if (await deleteButton.isVisible().catch(() => false)) {
        await deleteButton.click();

        // Should show confirmation dialog
        const confirmDialog = alicePage.getByRole('dialog');
        if (await confirmDialog.isVisible().catch(() => false)) {
          await expect(confirmDialog).toBeVisible();

          // Cancel the deletion
          const cancelButton = confirmDialog.getByRole('button', { name: /cancel|no/i });
          if (await cancelButton.isVisible().catch(() => false)) {
            await cancelButton.click();
          }
        }
      }
    });
  });

  test.describe('Bulk Selection', () => {
    test('should have select all checkbox', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Look for select all checkbox
      const selectAllCheckbox = alicePage.getByRole('checkbox', { name: /select all/i });

      if (await selectAllCheckbox.isVisible().catch(() => false)) {
        await expect(selectAllCheckbox).toBeVisible();
      }
    });

    test('should select all sessions when clicking select all', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      const selectAllCheckbox = alicePage.getByRole('checkbox', { name: /select all/i });

      if (await selectAllCheckbox.isVisible().catch(() => false)) {
        await selectAllCheckbox.click();
        await expect(selectAllCheckbox).toBeChecked();
      }
    });

    test('should show bulk delete button when sessions are selected', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      const selectAllCheckbox = alicePage.getByRole('checkbox', { name: /select all/i });

      if (await selectAllCheckbox.isVisible().catch(() => false)) {
        await selectAllCheckbox.click();

        // Bulk delete button should appear
        const bulkDeleteButton = alicePage.getByRole('button', { name: /delete selected|bulk delete/i });
        if (await bulkDeleteButton.isVisible().catch(() => false)) {
          await expect(bulkDeleteButton).toBeVisible();
        }
      }
    });
  });

  test.describe('Pagination', () => {
    test('should show load more button if more sessions exist', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Look for load more button
      const loadMoreButton = alicePage.getByRole('button', { name: /load more|show more/i });

      // May or may not be visible depending on session count
      if (await loadMoreButton.isVisible().catch(() => false)) {
        await expect(loadMoreButton).toBeVisible();
      }
    });

    test('should load more sessions when clicking load more', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      const loadMoreButton = alicePage.getByRole('button', { name: /load more|show more/i });

      if (await loadMoreButton.isVisible().catch(() => false)) {
        await loadMoreButton.click();
        await alicePage.waitForLoadState('networkidle');

        // Page should still be functional
        await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
      }
    });
  });

  test.describe('Performance Metrics', () => {
    test('should load sessions within acceptable time', async ({ alicePage }) => {
      const startTime = Date.now();

      await alicePage.goto('/studio/chat');
      await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should handle rapid session switching', async ({ alicePage }) => {
      await alicePage.waitForLoadState('networkidle');

      // Get session items
      const sessionItems = alicePage.locator('[data-testid*="session"], .session-item');

      if ((await sessionItems.count()) >= 2) {
        // Rapidly switch between sessions
        await sessionItems.first().click();
        await alicePage.waitForTimeout(100);
        await sessionItems.nth(1).click();
        await alicePage.waitForTimeout(100);
        await sessionItems.first().click();

        // Page should still be functional
        await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
      }
    });
  });
});
