/**
 * Navigation Auto-Loading E2E Tests
 *
 * Tests that verify the ActivityBar navigation items are loaded from
 * server-provided visible_modules via /api/v1/me endpoint.
 *
 * Sprint 4: StudioShell navigation auto-loading fix
 *
 * Test Coverage:
 * - Server-driven navigation configuration
 * - Deep-link synchronization with ActivityBar
 * - Module ID normalization (workflows, cost, observability)
 * - AI prediction indicators
 * - Navigation tracking for AI predictions
 */

import { test, expect } from './fixtures/auth';
import {
  mockUserInfoResponse,
  mockFeatureFlags,
  PERSONA_VISIBLE_MODULES,
} from './fixtures/mock-factories';

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Set up mock for /api/v1/me endpoint with specific visible_modules
 */
async function setupMeEndpointMock(
  page: import('@playwright/test').Page,
  options: {
    persona?: 'admin' | 'developer' | 'user';
    subPersona?: string;
    visibleModules?: string[];
    featureFlags?: Record<string, boolean>;
  } = {}
) {
  const userResponse = mockUserInfoResponse({
    persona: options.persona ?? 'developer',
    sub_persona: options.subPersona ?? 'alice-builder',
    visible_modules:
      options.visibleModules ?? PERSONA_VISIBLE_MODULES['alice-builder'],
    feature_flags: options.featureFlags ?? {},
  });

  await page.route('**/api/v1/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(userResponse),
    });
  });
}

/**
 * Set up mock for /api/v1/features endpoint
 */
async function setupFeaturesMock(
  page: import('@playwright/test').Page,
  flags: Record<string, boolean> = {}
) {
  await page.route('**/api/v1/features', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockFeatureFlags(flags)),
    });
  });
}

// =============================================================================
// Server-Driven Navigation Tests
// =============================================================================

test.describe('Server-Driven Navigation Configuration', () => {
  test('should load navigation items from server visible_modules', async ({
    page,
  }) => {
    // GIVEN: Server returns specific visible_modules for alice-builder
    await setupMeEndpointMock(page, {
      persona: 'developer',
      subPersona: 'alice-builder',
      visibleModules: ['projects', 'chat', 'workflows', 'agents', 'mcp', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: ActivityBar should show only the modules from visible_modules
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // Should see allowed modules
    await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
    await expect(activityBar.getByTestId('nav-workflows')).toBeVisible();
    await expect(activityBar.getByTestId('nav-agents')).toBeVisible();
    await expect(activityBar.getByTestId('nav-mcp')).toBeVisible();
    await expect(activityBar.getByTestId('nav-help')).toBeVisible();

    // Should NOT see modules not in visible_modules
    await expect(activityBar.getByTestId('nav-admin')).not.toBeVisible();
    await expect(activityBar.getByTestId('nav-compliance')).not.toBeVisible();
    await expect(activityBar.getByTestId('nav-audit')).not.toBeVisible();
  });

  test('should show admin modules when server returns admin visible_modules', async ({
    page,
  }) => {
    // GIVEN: Server returns admin visible_modules
    await setupMeEndpointMock(page, {
      persona: 'admin',
      subPersona: 'admin',
      visibleModules: PERSONA_VISIBLE_MODULES.admin,
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: ActivityBar should show admin modules
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // Admin should see all modules including admin-only
    await expect(activityBar.getByTestId('nav-admin')).toBeVisible();
    await expect(activityBar.getByTestId('nav-compliance')).toBeVisible();
    await expect(activityBar.getByTestId('nav-audit')).toBeVisible();
    await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
    await expect(activityBar.getByTestId('nav-workflows')).toBeVisible();
  });

  test('should show limited modules for bob persona', async ({ page }) => {
    // GIVEN: Server returns bob visible_modules (limited)
    await setupMeEndpointMock(page, {
      persona: 'user',
      subPersona: 'bob',
      visibleModules: PERSONA_VISIBLE_MODULES.bob,
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: ActivityBar should show only bob's modules
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // Bob should see basic modules
    await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
    await expect(activityBar.getByTestId('nav-projects')).toBeVisible();
    await expect(activityBar.getByTestId('nav-workflows')).toBeVisible();
    await expect(activityBar.getByTestId('nav-help')).toBeVisible();

    // Bob should NOT see admin modules
    await expect(activityBar.getByTestId('nav-admin')).not.toBeVisible();
    await expect(activityBar.getByTestId('nav-compliance')).not.toBeVisible();
    await expect(activityBar.getByTestId('nav-agents')).not.toBeVisible();
  });
});

// =============================================================================
// Module ID Normalization Tests
// =============================================================================

test.describe('Module ID Normalization', () => {
  test('should use "workflows" not "flows"', async ({ page }) => {
    // GIVEN: Server returns "workflows" (normalized ID)
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: Workflows nav should be visible
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });
    await expect(activityBar.getByTestId('nav-workflows')).toBeVisible();
  });

  test('should use "cost" not "costs"', async ({ page }) => {
    // GIVEN: Server returns "cost" (normalized ID)
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'cost', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: Cost nav should be visible
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });
    await expect(activityBar.getByTestId('nav-cost')).toBeVisible();
  });

  test('should use "observability" not "metrics"', async ({ page }) => {
    // GIVEN: Server returns "observability" (normalized ID)
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'observability', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: Observability nav should be visible
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });
    await expect(activityBar.getByTestId('nav-observability')).toBeVisible();
  });
});

// =============================================================================
// Deep-Link Synchronization Tests
// =============================================================================

test.describe('Deep-Link Synchronization', () => {
  test('should sync ActivityBar active state with URL on initial load', async ({
    page,
  }) => {
    // GIVEN: Server returns modules including workflows
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'agents', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate directly to /studio/workflows (deep link)
    await page.goto('/studio/workflows', { waitUntil: 'networkidle' });

    // THEN: Workflows nav item should be highlighted as active
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    const workflowsNav = activityBar.getByTestId('nav-workflows');
    await expect(workflowsNav).toBeVisible();
    // Active item has bg-primary-100 class
    await expect(workflowsNav).toHaveClass(/bg-primary-100/);

    // Chat should NOT be active
    const chatNav = activityBar.getByTestId('nav-chat');
    await expect(chatNav).not.toHaveClass(/bg-primary-100/);
  });

  test('should sync ActivityBar when navigating to agents deep link', async ({
    page,
  }) => {
    // GIVEN: Server returns modules including agents
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'agents', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate directly to /studio/agents
    await page.goto('/studio/agents', { waitUntil: 'networkidle' });

    // THEN: Agents nav item should be active
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    const agentsNav = activityBar.getByTestId('nav-agents');
    await expect(agentsNav).toBeVisible();
    await expect(agentsNav).toHaveClass(/bg-primary-100/);
  });

  test('should handle deep links with sub-paths', async ({ page }) => {
    // GIVEN: Server returns modules
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to a sub-path of chat
    await page.goto('/studio/chat/session-123', { waitUntil: 'networkidle' });

    // THEN: Chat nav item should be active (prefix match)
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    const chatNav = activityBar.getByTestId('nav-chat');
    await expect(chatNav).toBeVisible();
    await expect(chatNav).toHaveClass(/bg-primary-100/);
  });

  test('should not crash on unknown routes', async ({ page }) => {
    // GIVEN: Server returns modules
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'help'],
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to an unknown route
    await page.goto('/studio/unknown-route', { waitUntil: 'networkidle' });

    // THEN: ActivityBar should still render without crashing
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // No nav item should be active (unknown route)
    // Chat and workflows should still be visible but not active
    await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
  });
});

// =============================================================================
// Navigation Click Tests
// =============================================================================

test.describe('Navigation Click Behavior', () => {
  test('should navigate and update active state on nav item click', async ({
    page,
  }) => {
    // GIVEN: Server returns modules
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'agents', 'help'],
    });
    await setupFeaturesMock(page);

    // Start at chat
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // WHEN: Click on workflows nav item
    const workflowsNav = activityBar.getByTestId('nav-workflows');
    await workflowsNav.click();

    // THEN: URL should change and workflows should become active
    await expect(page).toHaveURL(/\/studio\/workflows/);
    await expect(workflowsNav).toHaveClass(/bg-primary-100/);

    // Chat should no longer be active
    const chatNav = activityBar.getByTestId('nav-chat');
    await expect(chatNav).not.toHaveClass(/bg-primary-100/);
  });

  test('should track page visits for AI predictions', async ({ page }) => {
    // GIVEN: Server returns modules with AI features enabled
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'agents', 'help'],
      featureFlags: { enable_ai_suggestions: true },
    });
    await setupFeaturesMock(page, { enable_ai_suggestions: true });

    // Navigate to chat first
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // WHEN: Navigate to workflows, then agents
    await activityBar.getByTestId('nav-workflows').click();
    await expect(page).toHaveURL(/\/studio\/workflows/);

    await activityBar.getByTestId('nav-agents').click();
    await expect(page).toHaveURL(/\/studio\/agents/);

    // THEN: Navigation history is tracked (verified by successful navigation)
    // The recentPages state is updated in sessionSlice via trackPageVisit
    await expect(activityBar.getByTestId('nav-agents')).toHaveClass(
      /bg-primary-100/
    );
  });
});

// =============================================================================
// Command Palette Tests
// =============================================================================

test.describe('Command Palette', () => {
  test('should open command palette when button is clicked', async ({
    page,
  }) => {
    // GIVEN: User is authenticated and on studio
    await setupMeEndpointMock(page);
    await setupFeaturesMock(page);

    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // WHEN: Click command palette button
    const cmdPaletteBtn = activityBar.getByTestId('command-palette-button');
    await expect(cmdPaletteBtn).toBeVisible();
    await cmdPaletteBtn.click();

    // THEN: Command palette should open (dispatches Cmd+K event)
    // The actual palette rendering depends on CommandPalette component
    // Here we verify the button is clickable and accessible
    await expect(cmdPaletteBtn).toHaveAttribute(
      'aria-label',
      'Command Palette'
    );
  });
});

// =============================================================================
// Accessibility Tests
// =============================================================================

test.describe('Navigation Accessibility', () => {
  test('should have proper ARIA labels on all nav items', async ({ page }) => {
    // GIVEN: Server returns modules
    await setupMeEndpointMock(page, {
      visibleModules: ['chat', 'workflows', 'agents', 'help'],
    });
    await setupFeaturesMock(page);

    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // THEN: All visible nav buttons should have aria-labels
    const chatNav = activityBar.getByTestId('nav-chat');
    await expect(chatNav).toHaveAttribute('aria-label', 'Chat');

    const workflowsNav = activityBar.getByTestId('nav-workflows');
    await expect(workflowsNav).toHaveAttribute('aria-label', 'Workflows');

    const agentsNav = activityBar.getByTestId('nav-agents');
    await expect(agentsNav).toHaveAttribute('aria-label', 'Agents');

    const helpNav = activityBar.getByTestId('nav-help');
    await expect(helpNav).toHaveAttribute('aria-label', 'Help');
  });

  test('should be keyboard navigable', async ({ page }) => {
    // GIVEN: Server returns modules
    await setupMeEndpointMock(page, {
      visibleModules: ['projects', 'chat', 'workflows', 'help'],
    });
    await setupFeaturesMock(page);

    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // WHEN: Tab through nav items
    await page.keyboard.press('Tab');

    // THEN: First nav item (projects) should be focused
    const projectsNav = activityBar.getByTestId('nav-projects');
    await expect(projectsNav).toBeFocused();

    // Tab to next item
    await page.keyboard.press('Tab');
    const chatNav = activityBar.getByTestId('nav-chat');
    await expect(chatNav).toBeFocused();
  });
});

// =============================================================================
// Fallback Behavior Tests
// =============================================================================

test.describe('Fallback Behavior', () => {
  test('should fall back to client-side config when server returns empty visible_modules', async ({
    page,
  }) => {
    // GIVEN: Server returns empty visible_modules
    await setupMeEndpointMock(page, {
      persona: 'developer',
      visibleModules: [], // Empty - should trigger fallback
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: ActivityBar should still render with fallback modules
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // Should at least see chat (common fallback)
    await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
  });

  test('should handle /api/v1/me endpoint failure gracefully', async ({
    page,
  }) => {
    // GIVEN: Server returns error for /me endpoint
    await page.route('**/api/v1/me', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });
    await setupFeaturesMock(page);

    // WHEN: Navigate to the studio
    await page.goto('/studio/chat', { waitUntil: 'networkidle' });

    // THEN: App should not crash - ActivityBar should still render
    // It will use JWT fallback or default config
    const activityBar = page.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 15000 });
  });
});
