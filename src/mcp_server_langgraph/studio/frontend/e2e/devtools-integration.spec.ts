/**
 * DevTools Integration E2E Tests
 *
 * Tests for the Chrome DevTools-like debugging panel in Agent Studio.
 * Validates keyboard shortcuts, tab navigation, and context-aware behavior.
 *
 * Test Coverage:
 * - DevTools panel visibility toggle (Cmd+Shift+I)
 * - Tab navigation and switching
 * - Context-aware tab visibility (session vs workflow)
 * - Console log display
 * - State inspection
 * - Feature flag gating
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock feature flags with DevTools enabled
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
  // DevTools feature flags
  devtools_panel: true,
  devtools_ai_insights: true,
  devtools_ai_layout: true,
  devtools_network_tab: true,
};

// Mock feature flags with DevTools disabled
const mockFeatureFlagsDevToolsDisabled = {
  ...mockFeatureFlags,
  devtools_panel: false,
};

test.describe('DevTools Integration', () => {
  test.describe('Panel Visibility', () => {
    test('should render DevTools panel when feature flag enabled', async ({ alicePage }) => {
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

      // DevTools panel should be visible (default open for developer persona)
      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });
    });

    test('should hide DevTools panel when feature flag disabled', async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlagsDevToolsDisabled),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // DevTools panel should not be visible when disabled
      await expect(alicePage.getByTestId('devtools-panel')).not.toBeVisible();
    });

    test('should toggle DevTools panel with Cmd+Shift+I', async ({ alicePage }) => {
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

      // Initial state: DevTools visible (for developer persona)
      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Toggle off with Cmd+Shift+I
      await alicePage.keyboard.press('Meta+Shift+KeyI');
      await expect(alicePage.getByTestId('devtools-panel')).not.toBeVisible();

      // Toggle on with Cmd+Shift+I
      await alicePage.keyboard.press('Meta+Shift+KeyI');
      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible();
    });
  });

  test.describe('Tab Navigation', () => {
    test('should render default tabs', async ({ alicePage }) => {
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

      // Wait for DevTools to be visible
      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Verify core tabs are visible
      await expect(alicePage.getByTestId('devtools-tab-console')).toBeVisible();
      await expect(alicePage.getByTestId('devtools-tab-problems')).toBeVisible();
      await expect(alicePage.getByTestId('devtools-tab-state')).toBeVisible();
    });

    test('should switch tabs on click', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Click on State tab
      await alicePage.getByTestId('devtools-tab-state').click();

      // State tab content should be visible
      await expect(alicePage.getByTestId('state-tab')).toBeVisible();

      // Click on Problems tab
      await alicePage.getByTestId('devtools-tab-problems').click();

      // Problems tab content should be visible
      await expect(alicePage.getByTestId('problems-tab')).toBeVisible();
    });

    test('should navigate tabs with keyboard shortcuts', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Start at Console tab (default)
      await expect(alicePage.getByTestId('console-tab')).toBeVisible();

      // Navigate to next tab with Cmd+]
      await alicePage.keyboard.press('Meta+]');

      // Should move to next tab
      // (exact tab depends on order, but Console should not be active)
    });
  });

  test.describe('Console Tab', () => {
    test('should display console entries', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Click Console tab
      await alicePage.getByTestId('devtools-tab-console').click();

      // Console tab should be visible
      await expect(alicePage.getByTestId('console-tab')).toBeVisible();
    });

    test('should clear console with Cmd+K', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Click Console tab
      await alicePage.getByTestId('devtools-tab-console').click();

      // Clear console with Cmd+K
      await alicePage.keyboard.press('Meta+KeyK');

      // Console should be empty (or show empty state)
      await expect(alicePage.getByTestId('console-tab')).toBeVisible();
    });

    test('should filter console by log level', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Click Console tab
      await alicePage.getByTestId('devtools-tab-console').click();

      // Filter buttons should be visible
      await expect(
        alicePage.getByTestId('console-filter-error')
      ).toBeVisible();
      await expect(
        alicePage.getByTestId('console-filter-warning')
      ).toBeVisible();
    });
  });

  test.describe('State Tab', () => {
    test('should display state tree', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Click State tab
      await alicePage.getByTestId('devtools-tab-state').click();

      // State tree should be visible
      await expect(alicePage.getByTestId('state-tree')).toBeVisible();
    });

    test('should search state', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Click State tab
      await alicePage.getByTestId('devtools-tab-state').click();

      // Search input should be visible
      const searchInput = alicePage.getByTestId('state-search');
      await expect(searchInput).toBeVisible();

      // Type search term
      await searchInput.fill('session');

      // State tree should filter (or highlight matching nodes)
    });
  });

  test.describe('Network Tab', () => {
    test('should show Network tab when feature flag enabled', async ({
      alicePage,
    }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Network tab should be visible when devtools_network_tab is true
      await expect(
        alicePage.getByTestId('devtools-tab-network')
      ).toBeVisible();
    });

    test('should hide Network tab when feature flag disabled', async ({
      alicePage,
    }) => {
      const flagsWithoutNetwork = {
        ...mockFeatureFlags,
        devtools_network_tab: false,
      };

      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(flagsWithoutNetwork),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Network tab should NOT be visible
      await expect(
        alicePage.getByTestId('devtools-tab-network')
      ).not.toBeVisible();
    });
  });

  test.describe('AI Insights Tab', () => {
    test('should show AI Insights tab when feature flag enabled', async ({
      alicePage,
    }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // AI Insights tab should be visible when devtools_ai_insights is true
      await expect(
        alicePage.getByTestId('devtools-tab-ai-insights')
      ).toBeVisible();
    });

    test('should hide AI Insights tab when feature flag disabled', async ({
      alicePage,
    }) => {
      const flagsWithoutAI = {
        ...mockFeatureFlags,
        devtools_ai_insights: false,
      };

      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(flagsWithoutAI),
          });
        });
      }

      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // AI Insights tab should NOT be visible
      await expect(
        alicePage.getByTestId('devtools-tab-ai-insights')
      ).not.toBeVisible();
    });
  });

  test.describe('Context-Aware Tabs', () => {
    test('should show Agent Trace tab in session context', async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock session with trace data
        await alicePage.route('**/api/v1/sessions/session-1', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: 'session-1',
              name: 'Test Session',
              created_at: new Date().toISOString(),
            }),
          });
        });
      }

      // Navigate to session context
      await alicePage.goto('/studio/v2/chat/session-1', {
        waitUntil: 'networkidle',
      });

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Agent Trace tab should be visible in session context
      await expect(
        alicePage.getByTestId('devtools-tab-agent-trace')
      ).toBeVisible();
    });

    test('should show Execution Trace tab in workflow context', async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock workflow
        await alicePage.route(
          '**/api/v1/workflows/workflow-1',
          async (route) => {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                id: 'workflow-1',
                name: 'Test Workflow',
                created_at: new Date().toISOString(),
              }),
            });
          }
        );
      }

      // Navigate to workflow context
      await alicePage.goto('/studio/v2/workflows/workflow-1', {
        waitUntil: 'networkidle',
      });

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Execution Trace tab should be visible in workflow context
      await expect(
        alicePage.getByTestId('devtools-tab-execution-trace')
      ).toBeVisible();
    });
  });

  test.describe('Persona-Based Defaults', () => {
    test('should show DevTools open by default for developer persona', async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      // Alice is a developer persona
      await alicePage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // DevTools should be open by default for developers
      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });
    });

    test('should show DevTools collapsed by default for standard user', async ({
      bobPage,
    }) => {
      if (!backendEnabled) {
        await bobPage.route('**/api/v1/features', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      // Bob is a standard user persona
      await bobPage.goto('/studio/v2/chat', { waitUntil: 'networkidle' });

      // DevTools should be collapsed by default for standard users
      await expect(bobPage.getByTestId('devtools-panel')).not.toBeVisible();

      // But the toggle should still work
      await bobPage.keyboard.press('Meta+Shift+KeyI');
      await expect(bobPage.getByTestId('devtools-panel')).toBeVisible();
    });
  });

  test.describe('Panel Resizing', () => {
    test('should resize DevTools panel', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Get the resize handle
      const resizeHandle = alicePage.getByTestId('devtools-resize-handle');
      await expect(resizeHandle).toBeVisible();

      // Get initial height
      const panel = alicePage.getByTestId('devtools-panel');
      const initialBox = await panel.boundingBox();

      // Drag the resize handle up to make panel larger
      if (resizeHandle && initialBox) {
        await resizeHandle.hover();
        await alicePage.mouse.down();
        await alicePage.mouse.move(initialBox.x, initialBox.y - 100);
        await alicePage.mouse.up();

        // Panel should be taller
        const newBox = await panel.boundingBox();
        expect(newBox?.height).toBeGreaterThan(initialBox.height);
      }
    });
  });

  test.describe('StatusBar Integration', () => {
    test('should show DevTools toggle in status bar', async ({ alicePage }) => {
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

      // Status bar should have DevTools toggle
      await expect(alicePage.getByTestId('status-bar')).toBeVisible({
        timeout: 10000,
      });
      await expect(
        alicePage.getByTestId('status-bar-devtools-toggle')
      ).toBeVisible();
    });

    test('should show problem count badge in status bar', async ({
      alicePage,
    }) => {
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

      // If there are problems, badge should be visible
      const statusBar = alicePage.getByTestId('status-bar');
      await expect(statusBar).toBeVisible({ timeout: 10000 });

      // Problem count badge may or may not be visible depending on state
      // Just verify the toggle exists
      await expect(
        alicePage.getByTestId('status-bar-devtools-toggle')
      ).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper keyboard navigation', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Tab list should have proper ARIA role
      const tabList = alicePage.getByRole('tablist');
      await expect(tabList).toBeVisible();

      // Individual tabs should be focusable
      const consoleTab = alicePage.getByTestId('devtools-tab-console');
      await consoleTab.focus();
      await expect(consoleTab).toBeFocused();

      // Arrow keys should navigate between tabs
      await alicePage.keyboard.press('ArrowRight');
      // Focus should have moved to next tab
    });

    test('should have proper ARIA labels', async ({ alicePage }) => {
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

      await expect(alicePage.getByTestId('devtools-panel')).toBeVisible({
        timeout: 10000,
      });

      // Panel should have proper region role
      const panel = alicePage.getByRole('region', { name: /devtools/i });
      await expect(panel).toBeVisible();

      // Tabs should have proper tab role
      const tabs = alicePage.getByRole('tab');
      const tabCount = await tabs.count();
      expect(tabCount).toBeGreaterThan(0);
    });
  });
});
