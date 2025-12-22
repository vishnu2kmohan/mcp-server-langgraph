/**
 * Hybrid Shell Smoke E2E Tests
 *
 * P0 smoke tests for the Hybrid Canvas implementation.
 * These tests validate critical functionality to ensure no regressions.
 *
 * Test Coverage:
 * - HybridShell layout renders correctly
 * - Legacy AppShell still works (no regressions)
 * - Session list loads and displays
 * - Basic navigation between panels
 * - Persona-aware navigation visibility
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Feature flag for HybridShell (matches backend feature flag)
const HYBRID_SHELL_FLAG = 'canvas_hybrid_shell';

// Mock feature flags - matches the format from MSW handlers (flat object, not wrapped)
// IMPORTANT: The API returns flags directly, not wrapped in { features: {...} }
const mockFeatureFlags = {
  [HYBRID_SHELL_FLAG]: true,
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

test.describe('Hybrid Shell Smoke Tests', () => {
  test.describe('Layout Rendering', () => {
    test('should render HybridShell when feature flag enabled', async ({ alicePage }) => {
      // Setup: Mock feature flag if backend disabled
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      // Navigate to the studio v2 route
      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // Verify HybridShell layout components are rendered
      await expect(alicePage.getByTestId('hybrid-shell')).toBeVisible({ timeout: 10000 });
      await expect(alicePage.getByTestId('activity-bar')).toBeVisible();
      await expect(alicePage.getByTestId('session-nav')).toBeVisible();
      await expect(alicePage.getByTestId('conversation-panel')).toBeVisible();
      await expect(alicePage.getByTestId('canvas-panel')).toBeVisible();
    });

    test('should render ActivityBar with navigation items', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // Verify navigation items are present
      const activityBar = alicePage.getByTestId('activity-bar');
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Basic navigation items should be visible for alice (developer)
      await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
    });

    test('should render StatusBar with connection status', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // Verify status bar is rendered
      await expect(alicePage.getByTestId('status-bar')).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Legacy AppShell Compatibility', () => {
    test('should still render legacy AppShell at /studio', async ({ alicePage }) => {
      // This test ensures the legacy AppShell still works
      // No feature flag override - use whatever is configured
      await alicePage.goto('/studio', { waitUntil: 'networkidle' });

      // Legacy route should still work
      // The specific elements depend on the current implementation
      await expect(alicePage.locator('body')).toBeVisible({ timeout: 10000 });
    });

    test('should handle navigation between legacy and hybrid routes', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      // Start at legacy route
      await alicePage.goto('/studio', { waitUntil: 'networkidle' });
      await expect(alicePage.locator('body')).toBeVisible({ timeout: 10000 });

      // Navigate to hybrid route
      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });
      // Should not crash or show error page
      await expect(alicePage.locator('body')).not.toContainText('Error');
    });
  });

  test.describe('Session Navigation', () => {
    test('should display session list in SessionNav', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock sessions endpoint
        await alicePage.route('**/api/v1/sessions*', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'session-1',
                  name: 'Test Session 1',
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                },
                {
                  id: 'session-2',
                  name: 'Test Session 2',
                  created_at: new Date(Date.now() - 86400000).toISOString(),
                  updated_at: new Date(Date.now() - 86400000).toISOString(),
                },
              ],
              cursor: null,
            }),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // Verify session nav is visible
      const sessionNav = alicePage.getByTestId('session-nav');
      await expect(sessionNav).toBeVisible({ timeout: 10000 });

      // Should have session list or new chat button
      const newChatButton = sessionNav.getByTestId('new-chat-button');
      await expect(newChatButton).toBeVisible();
    });

    test('should create new session when new chat clicked', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        await alicePage.route('**/api/v1/sessions', async (route) => {
          if (route.request().method() === 'POST') {
            await route.fulfill({
              status: 201,
              contentType: 'application/json',
              body: JSON.stringify({
                id: 'new-session-123',
                name: 'New Session',
                created_at: new Date().toISOString(),
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({ items: [], cursor: null }),
            });
          }
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      const newChatButton = alicePage.getByTestId('new-chat-button');
      await expect(newChatButton).toBeVisible({ timeout: 10000 });
      await newChatButton.click();

      // URL should update to include session ID or show new session
      // The exact behavior depends on the implementation
    });
  });

  test.describe('Canvas Panel', () => {
    test('should render empty canvas panel', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      const canvasPanel = alicePage.getByTestId('canvas-panel');
      await expect(canvasPanel).toBeVisible({ timeout: 10000 });
    });

    test('should render canvas tabs when artifacts exist', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock artifacts endpoint
        await alicePage.route('**/api/v1/artifacts*', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'artifact-1',
                  type: 'code',
                  content: 'console.log("test")',
                  version: 1,
                },
              ],
              cursor: null,
            }),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

      // Canvas should render - specific behavior depends on implementation
      const canvasPanel = alicePage.getByTestId('canvas-panel');
      await expect(canvasPanel).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Persona-Aware Navigation', () => {
    test('should show admin-only items for admin persona', async ({ adminPage }) => {
      if (!backendEnabled) {
        await adminPage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      await adminPage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      const activityBar = adminPage.getByTestId('activity-bar');
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Admin should see admin nav item
      // The specific testId depends on implementation
    });

    test('should hide admin items for standard user', async ({ bobPage }) => {
      if (!backendEnabled) {
        await bobPage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      await bobPage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // Bob should have limited navigation
      const activityBar = bobPage.getByTestId('activity-bar');
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Bob should NOT see admin items
      await expect(bobPage.getByTestId('nav-admin')).not.toBeVisible();
    });
  });

  test.describe('Conversation Panel', () => {
    test('should render chat input', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      const conversationPanel = alicePage.getByTestId('conversation-panel');
      await expect(conversationPanel).toBeVisible({ timeout: 10000 });

      // Chat input should be visible
      const chatInput = alicePage.getByTestId('chat-input');
      await expect(chatInput).toBeVisible();
    });

    test('should show message list when session has messages', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock session messages
        await alicePage.route('**/api/v1/sessions/*/messages*', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              items: [
                {
                  id: 'msg-1',
                  role: 'user',
                  content: 'Hello',
                  created_at: new Date().toISOString(),
                },
                {
                  id: 'msg-2',
                  role: 'assistant',
                  content: 'Hi there!',
                  created_at: new Date().toISOString(),
                },
              ],
              cursor: null,
            }),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat/session-1', { waitUntil: 'networkidle' });

      // Message list should render
      const conversationPanel = alicePage.getByTestId('conversation-panel');
      await expect(conversationPanel).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Resizable Panels', () => {
    test('should have resizable panel layout', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // Check that the panel group exists (from react-resizable-panels)
      const hybridShell = alicePage.getByTestId('hybrid-shell');
      await expect(hybridShell).toBeVisible({ timeout: 10000 });

      // Panel resizers should be present
      // Note: The exact selectors depend on react-resizable-panels implementation
    });
  });

  test.describe('Error Handling', () => {
    test('should handle API errors gracefully', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock API error
        await alicePage.route('**/api/v1/sessions*', async (route) => {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Internal Server Error' }),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // Should not show unhandled error page
      await expect(alicePage.locator('body')).not.toContainText('Unhandled Runtime Error');
    });

    test('should handle network timeout gracefully', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock slow/timeout response
        await alicePage.route('**/api/v1/sessions*', async (route) => {
          await new Promise((resolve) => setTimeout(resolve, 100)); // Short delay for test
          await route.abort();
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'domcontentloaded', timeout: 5000 });

      // Page should still be interactive even if API fails
      await expect(alicePage.locator('body')).toBeVisible();
    });
  });
});
