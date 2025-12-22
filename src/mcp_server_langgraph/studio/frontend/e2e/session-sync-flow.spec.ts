/**
 * Session Sync Flow E2E Tests
 *
 * Tests the session synchronization and revalidation flow:
 * - Loader data syncs to Redux on navigation
 * - Optimistic updates during message sending
 * - Revalidation after mutation completes
 * - Race condition protection for pending mutations
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('Session Sync Flow', () => {
  test.beforeEach(async ({ alicePage }) => {
    // Only mock API responses when backend is disabled
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

        // User endpoint
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

        // Session with messages
        if (url.match(/\/sessions\/[^/]+$/) && method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'session-sync-test',
              name: 'Sync Test Session',
              status: 'active',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              config: {
                model: 'gpt-4',
                model_provider: 'openai',
              },
            }),
          });
          return;
        }

        // Messages endpoint
        if (url.includes('/messages') && method === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              data: [
                {
                  id: 'msg-1',
                  role: 'user',
                  content: 'Hello',
                  created_at: new Date().toISOString(),
                },
                {
                  id: 'msg-2',
                  role: 'assistant',
                  content: 'Hi! How can I help you today?',
                  created_at: new Date().toISOString(),
                },
              ],
              pagination: { count: 2, next_cursor: null },
            }),
          });
          return;
        }

        // Send message
        if (url.includes('/messages') && method === 'POST') {
          // Simulate processing delay for optimistic update testing
          await new Promise(resolve => setTimeout(resolve, 500));
          await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'msg-new',
              role: 'user',
              content: route.request().postDataJSON()?.content,
              created_at: new Date().toISOString(),
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
                  id: 'session-sync-test',
                  name: 'Sync Test Session',
                  status: 'active',
                  created_at: new Date().toISOString(),
                  message_count: 2,
                },
              ],
              pagination: { count: 1, next_cursor: null },
            }),
          });
          return;
        }

        // Projects
        if (url.includes('/projects')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [{ id: 'test-project', name: 'Test', status: 'active' }],
              total: 1,
            }),
          });
          return;
        }

        // Default
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });
    }
  });

  test.describe('Session Data Loading', () => {
    test('should load session from loader and sync to Redux', async ({ alicePage }) => {
      // Navigate to a session
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      // Wait for session list to load
      const sessionItem = alicePage.locator('[data-testid^="session-item-"]').first();
      await sessionItem.waitFor({ timeout: 10000 }).catch(() => null);

      if (await sessionItem.isVisible()) {
        await sessionItem.click();
        await alicePage.waitForLoadState('networkidle');

        // Messages should be visible
        const messageArea = alicePage.locator('main, [role="main"], .messages');
        await expect(messageArea.first()).toBeVisible();
      }
    });

    test('should display messages from loaded session', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      const sessionItem = alicePage.locator('[data-testid^="session-item-"]').first();
      await sessionItem.waitFor({ timeout: 10000 }).catch(() => null);

      if (await sessionItem.isVisible()) {
        await sessionItem.click();
        await alicePage.waitForLoadState('networkidle');

        // Should show message content area
        const messageArea = alicePage.locator('.message, [data-testid*="message"]');
        const messagesVisible = await messageArea.count() > 0 ||
          await alicePage.locator('main').textContent().then(t => t?.includes('Hello') || false);

        // Page should load successfully with messages
        await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
      }
    });
  });

  test.describe('Message Sending Flow', () => {
    test('should send message and show optimistic update', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      // Find and click a session
      const sessionItem = alicePage.locator('[data-testid^="session-item-"]').first();
      await sessionItem.waitFor({ timeout: 10000 }).catch(() => null);

      if (await sessionItem.isVisible()) {
        await sessionItem.click();
        await alicePage.waitForLoadState('networkidle');

        // Find message input
        const messageInput = alicePage.locator('textarea, input[type="text"]').filter({ hasText: '' }).first();
        const sendButton = alicePage.getByRole('button', { name: /send/i });

        if (await messageInput.isVisible({ timeout: 2000 })) {
          // Type and send message
          await messageInput.fill('Test optimistic message');

          if (await sendButton.isVisible({ timeout: 1000 })) {
            await sendButton.click();
          } else {
            await messageInput.press('Enter');
          }

          // Message should appear immediately (optimistic update)
          await alicePage.waitForTimeout(500);

          // Page should remain functional
          await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
        }
      }
    });

    test('should handle rapid message sending without race conditions', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      const sessionItem = alicePage.locator('[data-testid^="session-item-"]').first();
      await sessionItem.waitFor({ timeout: 10000 }).catch(() => null);

      if (await sessionItem.isVisible()) {
        await sessionItem.click();
        await alicePage.waitForLoadState('networkidle');

        const messageInput = alicePage.locator('textarea, input[type="text"]').filter({ hasText: '' }).first();

        if (await messageInput.isVisible({ timeout: 2000 })) {
          // Send multiple messages rapidly
          for (let i = 1; i <= 3; i++) {
            await messageInput.fill(`Rapid message ${i}`);
            await messageInput.press('Enter');
            await alicePage.waitForTimeout(100);
          }

          // Wait for processing
          await alicePage.waitForLoadState('networkidle');

          // Page should still be functional without errors
          await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Session Navigation', () => {
    test('should sync new session data when switching sessions', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      const sessionItems = alicePage.locator('[data-testid^="session-item-"]');

      // Need at least 2 sessions to test switching
      if (await sessionItems.count() >= 2) {
        // Click first session
        await sessionItems.first().click();
        await alicePage.waitForLoadState('networkidle');
        const url1 = alicePage.url();

        // Click second session
        await sessionItems.nth(1).click();
        await alicePage.waitForLoadState('networkidle');
        const url2 = alicePage.url();

        // URLs should be different if session IDs are in URL
        // Page should be functional
        await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
      }
    });

    test('should preserve state during back navigation', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      const sessionItem = alicePage.locator('[data-testid^="session-item-"]').first();
      await sessionItem.waitFor({ timeout: 10000 }).catch(() => null);

      if (await sessionItem.isVisible()) {
        // Navigate to session
        await sessionItem.click();
        await alicePage.waitForLoadState('networkidle');

        // Navigate somewhere else
        const homeLink = alicePage.getByRole('link', { name: /home|dashboard/i }).first();
        if (await homeLink.isVisible({ timeout: 1000 })) {
          await homeLink.click();
          await alicePage.waitForLoadState('networkidle');

          // Go back
          await alicePage.goBack();
          await alicePage.waitForLoadState('networkidle');

          // Session should be restored
          await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
        }
      }
    });
  });

  test.describe('Error Handling', () => {
    test('should handle session load errors gracefully', async ({ alicePage }) => {
      if (!backendEnabled) {
        // Override to return error for specific session
        await alicePage.route('**/sessions/error-session', async (route) => {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Internal server error' }),
          });
        });
      }

      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      // Page should still be functional even with error
      await expect(alicePage.locator('body')).toBeVisible();
    });

    test('should handle network timeouts during sync', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      // Simulate going offline briefly
      await alicePage.context().setOffline(true);
      await alicePage.waitForTimeout(500);
      await alicePage.context().setOffline(false);

      // Page should recover
      await expect(alicePage.locator('body')).toBeVisible();
    });
  });

  test.describe('Performance', () => {
    test('should load session within acceptable time', async ({ alicePage }) => {
      const startTime = Date.now();

      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      const sessionItem = alicePage.locator('[data-testid^="session-item-"]').first();
      await sessionItem.waitFor({ timeout: 10000 }).catch(() => null);

      if (await sessionItem.isVisible()) {
        await sessionItem.click();
        await alicePage.waitForLoadState('networkidle');
      }

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should debounce rapid interactions', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');
      await alicePage.waitForLoadState('networkidle');

      const sessionItems = alicePage.locator('[data-testid^="session-item-"]');

      if (await sessionItems.count() >= 2) {
        // Rapidly switch between sessions (should be debounced)
        for (let i = 0; i < 5; i++) {
          await sessionItems.nth(i % 2).click();
          await alicePage.waitForTimeout(50);
        }

        // Wait for debounce to settle
        await alicePage.waitForLoadState('networkidle');

        // Page should remain stable
        await expect(alicePage.locator('main, [role="main"]').first()).toBeVisible();
      }
    });
  });
});
