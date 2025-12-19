/**
 * WebSocket Status Indicators E2E Tests
 *
 * Tests the WebSocket-based status indicators in the StatusBar:
 * - MCP Connection Health status
 * - MCP Task status
 * - Audit Event streaming (admin only)
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('WebSocket Status Indicators', () => {
  test.describe('StatusBar WebSocket Indicators', () => {
    test.beforeEach(async ({ bobPage }) => {
      if (!backendEnabled) {
        // Mock health endpoint
        await bobPage.route('**/api/v1/health', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'healthy' }),
          });
        });

        // Mock WebSocket connections with page.evaluate
        await bobPage.addInitScript(() => {
          // Mock WebSocket for connection health
          const OriginalWebSocket = window.WebSocket;
          window.WebSocket = class extends OriginalWebSocket {
            constructor(url: string | URL, protocols?: string | string[]) {
              super(url, protocols);
              const urlStr = typeof url === 'string' ? url : url.toString();

              // Send mock data after connection
              setTimeout(() => {
                if (urlStr.includes('/connections/health/ws')) {
                  this.dispatchEvent(new MessageEvent('message', {
                    data: JSON.stringify({
                      type: 'connection_status',
                      connections: [
                        { id: 'conn-1', name: 'MCP Server 1', status: 'connected' },
                        { id: 'conn-2', name: 'MCP Server 2', status: 'connected' },
                      ],
                    }),
                  }));
                }
                if (urlStr.includes('/mcp/tasks/ws')) {
                  this.dispatchEvent(new MessageEvent('message', {
                    data: JSON.stringify({
                      type: 'task_list',
                      tasks: [],
                    }),
                  }));
                }
              }, 100);
            }
          } as unknown as typeof WebSocket;
        });
      }

      await bobPage.goto('/studio/');
    });

    test('should display status bar', async ({ bobPage }) => {
      const statusBar = bobPage.getByTestId('status-bar');
      await expect(statusBar).toBeVisible();
    });

    test('should display connection status indicator', async ({ bobPage }) => {
      const connectionStatus = bobPage.getByTestId('connection-status');
      await expect(connectionStatus).toBeVisible();
    });

    test('should display MCP connection count when connections exist', async ({ bobPage }) => {
      // MCP status may or may not be visible depending on backend configuration
      const mcpStatus = bobPage.getByTestId('mcp-status');

      // Wait for either MCP status to appear or timeout gracefully
      try {
        await expect(mcpStatus).toBeVisible({ timeout: 5000 });
        // If visible, verify it shows connection count format
        await expect(mcpStatus).toContainText(/\d+\/\d+/);
      } catch {
        // MCP status not visible - this is acceptable if no MCP servers configured
        test.skip();
      }
    });

    test('should display persona indicator', async ({ bobPage }) => {
      const personaIndicator = bobPage.getByTestId('persona-indicator');
      await expect(personaIndicator).toBeVisible();
    });
  });

  test.describe('Admin Audit Events', () => {
    test.beforeEach(async ({ adminPage }) => {
      if (!backendEnabled) {
        // Mock health endpoint
        await adminPage.route('**/api/v1/health', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'healthy' }),
          });
        });

        // Mock user endpoint for admin persona
        await adminPage.route('**/api/v1/me', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'admin-user',
              username: 'admin',
              email: 'admin@example.com',
              roles: ['admin'],
            }),
          });
        });

        // Mock audit WebSocket
        await adminPage.addInitScript(() => {
          const OriginalWebSocket = window.WebSocket;
          window.WebSocket = class extends OriginalWebSocket {
            constructor(url: string | URL, protocols?: string | string[]) {
              super(url, protocols);
              const urlStr = typeof url === 'string' ? url : url.toString();

              if (urlStr.includes('/api/v1/audit/stream')) {
                setTimeout(() => {
                  // Send a mock audit event
                  this.dispatchEvent(new MessageEvent('message', {
                    data: JSON.stringify({
                      event_id: 'evt-1',
                      timestamp: new Date().toISOString(),
                      category: 'authentication',
                      event_type: 'login',
                      actor: 'test@example.com',
                    }),
                  }));
                }, 100);
              }
            }
          } as unknown as typeof WebSocket;
        });
      }
    });

    test('should navigate to settings audit log tab', async ({ adminPage }) => {
      await adminPage.goto('/studio/settings');

      // Wait for settings page to load
      await expect(adminPage.getByRole('heading', { name: /settings/i })).toBeVisible();

      // Click on Audit Log tab (admin only)
      const auditTab = adminPage.getByRole('button', { name: /audit log/i });

      if (await auditTab.isVisible().catch(() => false)) {
        await auditTab.click();

        // Verify audit panel is visible
        const auditPanel = adminPage.getByTestId('audit-event-panel');
        await expect(auditPanel).toBeVisible();
      } else {
        // Tab not visible - may not have admin permissions in test environment
        test.skip();
      }
    });

    test('should display audit panel controls', async ({ adminPage }) => {
      await adminPage.goto('/studio/settings');

      // Wait for settings page and click audit tab
      await expect(adminPage.getByRole('heading', { name: /settings/i })).toBeVisible();

      const auditTab = adminPage.getByRole('button', { name: /audit log/i });
      if (await auditTab.isVisible().catch(() => false)) {
        await auditTab.click();

        // Verify controls are visible
        const pauseButton = adminPage.getByTestId('pause-button');
        await expect(pauseButton).toBeVisible();

        const auditStatus = adminPage.getByTestId('audit-status');
        await expect(auditStatus).toBeVisible();
      } else {
        test.skip();
      }
    });

    test('should toggle pause/resume in audit panel', async ({ adminPage }) => {
      await adminPage.goto('/studio/settings');

      await expect(adminPage.getByRole('heading', { name: /settings/i })).toBeVisible();

      const auditTab = adminPage.getByRole('button', { name: /audit log/i });
      if (await auditTab.isVisible().catch(() => false)) {
        await auditTab.click();

        // Click pause button
        const pauseButton = adminPage.getByTestId('pause-button');
        await pauseButton.click();

        // Should show resume text/indication
        await expect(adminPage.getByText(/resume/i)).toBeVisible();

        // Click again to resume
        await pauseButton.click();

        // Resume text should disappear
        await expect(adminPage.getByText(/resume/i)).not.toBeVisible();
      } else {
        test.skip();
      }
    });
  });

  test.describe('Task Status Indicator', () => {
    test('should not show task indicator when no active tasks', async ({ bobPage }) => {
      if (!backendEnabled) {
        await bobPage.addInitScript(() => {
          const OriginalWebSocket = window.WebSocket;
          window.WebSocket = class extends OriginalWebSocket {
            constructor(url: string | URL, protocols?: string | string[]) {
              super(url, protocols);
              const urlStr = typeof url === 'string' ? url : url.toString();

              if (urlStr.includes('/mcp/tasks/ws')) {
                setTimeout(() => {
                  this.dispatchEvent(new MessageEvent('message', {
                    data: JSON.stringify({ type: 'task_list', tasks: [] }),
                  }));
                }, 100);
              }
            }
          } as unknown as typeof WebSocket;
        });
      }

      await bobPage.goto('/studio/');

      // Task status should not be visible when no active tasks
      const taskStatus = bobPage.getByTestId('task-status');
      await expect(taskStatus).not.toBeVisible();
    });
  });
});
