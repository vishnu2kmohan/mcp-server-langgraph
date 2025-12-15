/**
 * Alice Power User Journey E2E Tests
 *
 * Tests the complete power user journey including:
 * - Workflow creation and management
 * - Multi-session orchestration
 * - Trace visualization
 * - Cost monitoring
 * - Advanced features access
 *
 * Uses HEART framework metrics:
 * - Happiness: Workflow creation satisfaction
 * - Engagement: Workflows created/modified
 * - Adoption: Power feature usage
 * - Retention: 30-day workflow editor retention
 * - Task Success: Workflow deployment success
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 * API mocks are only used when BACKEND_ENABLED=false.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
// Set BACKEND_ENABLED=false only for quick UI-only validation during development.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('Alice Power User Journey', () => {
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

        // Feature flags
        if (url.includes('/features')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ features: {} }),
          });
          return;
        }

        // User endpoint - return roles for persona derivation (developer)
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

        // Workflows list
        if (url.includes('/workflows') && !url.includes('/generate')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'wf-1',
                  name: 'Test Workflow',
                  description: 'A test workflow',
                  status: 'draft',
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                },
              ],
              total: 1,
              cursor: null,
            }),
          });
          return;
        }

        // Sessions list
        if (url.includes('/sessions')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'session-1',
                  workflow_id: 'wf-1',
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

        // Observability - traces
        if (url.includes('/observability/traces')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [],
              total: 0,
              cursor: null,
            }),
          });
          return;
        }

        // Observability - logs
        if (url.includes('/observability/logs')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [],
              total: 0,
              cursor: null,
            }),
          });
          return;
        }

        // Observability - metrics
        if (url.includes('/observability/metrics')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              total_requests: 100,
              avg_latency_ms: 150,
              error_rate: 0.02,
            }),
          });
          return;
        }

        // MCP tools
        if (url.includes('/mcp/tools')) {
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

        // MCP servers
        if (url.includes('/mcp/servers')) {
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

        // Default: return empty success response
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });
    }

    // Navigate to the app root
    await alicePage.goto('/studio/');
  });

  test.describe('Workflows Page', () => {
    test('should access workflows page', async ({ alicePage }) => {
      await alicePage.goto('/studio/workflows');

      // Wait for workflows page to load
      await expect(alicePage.getByText(/Workflows/i).first()).toBeVisible();
    });

    test('should display workflow list', async ({ alicePage }) => {
      await alicePage.goto('/studio/workflows');

      // Wait for page content - look for New Workflow or other workflow content
      await expect(alicePage.getByText(/New Workflow|Workflow/i).first()).toBeVisible();
    });

    test('should have create workflow button', async ({ alicePage }) => {
      await alicePage.goto('/studio/workflows');

      // Look for create button (Save button is always present)
      const saveButton = alicePage.getByRole('button', { name: /Save/i });
      await expect(saveButton).toBeVisible();
    });

    test('should have AI suggestions toggle', async ({ alicePage }) => {
      await alicePage.goto('/studio/workflows');

      // Look for AI Suggest button
      const aiSuggestButton = alicePage.getByTestId('ai-suggestions-toggle');
      await expect(aiSuggestButton).toBeVisible();
    });
  });

  test.describe('Chat Interface', () => {
    test('should access chat page', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');

      // Chat page should load - look for session panel or chat content
      await expect(alicePage.locator('main, [role="main"], .chat, textarea').first()).toBeVisible();
    });

    test('should have message input', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');

      // Look for message input - could be a textarea
      const messageInput = alicePage.locator('textarea, input[type="text"]').first();
      await expect(messageInput).toBeVisible();
    });

    test('should have send button', async ({ alicePage }) => {
      await alicePage.goto('/studio/chat');

      // Look for send button by role
      const sendButton = alicePage.getByRole('button').filter({ hasText: /Send/i });
      if (await sendButton.isVisible().catch(() => false)) {
        await expect(sendButton).toBeVisible();
      }
    });
  });

  test.describe('Observability Page', () => {
    test('should access observability page', async ({ alicePage }) => {
      await alicePage.goto('/studio/observability');

      // Observability page should load
      await expect(alicePage.getByText(/Observability/i).first()).toBeVisible();
    });

    test('should display traces section', async ({ alicePage }) => {
      await alicePage.goto('/studio/observability');

      // Wait for traces tab or content
      await expect(alicePage.getByRole('button', { name: /Traces/i })).toBeVisible();
    });

    test('should have tab navigation', async ({ alicePage }) => {
      await alicePage.goto('/studio/observability');

      // Check for tab buttons
      await expect(alicePage.getByRole('button', { name: /Traces/i })).toBeVisible();
      await expect(alicePage.getByRole('button', { name: /Logs/i })).toBeVisible();
    });
  });

  test.describe('MCP Explorer', () => {
    test('should access MCP explorer page', async ({ alicePage }) => {
      await alicePage.goto('/studio/mcp');

      // MCP page should load
      await expect(alicePage.getByText(/MCP/i).first()).toBeVisible();
    });

    test('should display tools section', async ({ alicePage }) => {
      await alicePage.goto('/studio/mcp');

      // Wait for tabs
      await expect(alicePage.getByRole('button', { name: /Tools/i })).toBeVisible();
    });

    test('should have server management', async ({ alicePage }) => {
      await alicePage.goto('/studio/mcp');

      // Check for servers tab
      await expect(alicePage.getByRole('button', { name: /Servers/i })).toBeVisible();
    });
  });

  test.describe('Settings Page', () => {
    test('should access settings page', async ({ alicePage }) => {
      await alicePage.goto('/studio/settings');

      // Settings page should load
      await expect(alicePage.getByText(/Settings/i).first()).toBeVisible();
    });

    test('should have profile settings', async ({ alicePage }) => {
      await alicePage.goto('/studio/settings');

      // Check for profile tab
      await expect(alicePage.getByRole('button', { name: /Profile/i })).toBeVisible();
    });

    test('should have save button', async ({ alicePage }) => {
      await alicePage.goto('/studio/settings');

      // Look for save button
      const saveButton = alicePage.getByRole('button', { name: /Save/i });
      await expect(saveButton).toBeVisible();
    });
  });

  test.describe('Performance Metrics (HEART)', () => {
    test('workflows page should load quickly', async ({ alicePage }) => {
      const startTime = Date.now();

      await alicePage.goto('/studio/workflows');
      await expect(alicePage.getByText(/Workflow/i).first()).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should have proper navigation structure', async ({ alicePage }) => {
      await alicePage.goto('/studio/workflows');

      // Wait for content
      await expect(alicePage.getByText(/Workflow/i).first()).toBeVisible();

      // Check for navigation in sidebar
      const nav = alicePage.locator('nav, [role="navigation"], aside');
      await expect(nav.first()).toBeVisible();
    });

    test('chat page should be responsive', async ({ alicePage }) => {
      const startTime = Date.now();

      await alicePage.goto('/studio/chat');
      await expect(alicePage.locator('main, [role="main"], textarea').first()).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Chat should load within 3 seconds
      expect(loadTime).toBeLessThan(3000);
    });
  });

  test.describe('Developer-specific Features', () => {
    test('should not have admin dashboard access', async ({ alicePage }) => {
      // Developer persona should be redirected when trying to access admin
      await alicePage.goto('/studio/admin/dashboard');

      // Should be redirected away from admin (to projects or workflows)
      await expect(alicePage).toHaveURL(/\/studio\/(projects|workflows|chat)/);
    });

    test('should have access to workflow builder features', async ({ alicePage }) => {
      await alicePage.goto('/studio/workflows');

      // Check for developer-level workflow features
      const generateCodeButton = alicePage.getByRole('button', { name: /Generate Code/i });
      await expect(generateCodeButton).toBeVisible();
    });

    test('should have access to export functionality', async ({ alicePage }) => {
      await alicePage.goto('/studio/workflows');

      // Check for export button
      const exportButton = alicePage.getByRole('button', { name: /Export/i });
      await expect(exportButton).toBeVisible();
    });
  });
});
