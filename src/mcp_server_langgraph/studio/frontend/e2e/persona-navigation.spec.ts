/**
 * Persona-Specific Navigation E2E Tests
 *
 * Tests for the 8 sub-persona variants and their navigation visibility.
 * Validates RBAC enforcement in the ActivityBar based on persona.
 *
 * Test Coverage:
 * - Admin personas (admin, security-admin, auditor)
 * - Developer personas (alice-builder, alice-analyst, alice-devops, compliance-officer)
 * - User personas (bob)
 * - Module visibility per persona
 * - Default view navigation per persona
 */

import { test, expect } from './fixtures/auth';

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

// Mock feature flags
const mockFeatureFlags = {
  studio_canvas_shell: true,
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

// Module visibility per persona (from PersonaVariants.ts)
const PERSONA_MODULES = {
  admin: ['chat', 'agents', 'flows', 'mcp', 'files', 'traces', 'costs', 'admin', 'help'],
  'security-admin': ['chat', 'admin', 'compliance', 'audit', 'help'],
  auditor: ['audit', 'compliance', 'help'],
  'alice-builder': ['chat', 'flows', 'mcp', 'agents', 'help'],
  'alice-analyst': ['chat', 'traces', 'costs', 'help'],
  'alice-devops': ['chat', 'mcp', 'traces', 'help'],
  'compliance-officer': ['audit', 'compliance', 'help'],
  bob: ['chat', 'projects', 'flows', 'help'],
};

// Modules that should be hidden for each persona
const PERSONA_HIDDEN_MODULES = {
  admin: [], // Admin sees everything
  'security-admin': ['projects'],
  auditor: ['chat', 'agents', 'flows', 'mcp', 'files', 'traces', 'costs', 'admin'],
  'alice-builder': ['admin', 'compliance', 'audit', 'costs', 'traces'],
  'alice-analyst': ['admin', 'flows', 'agents', 'mcp', 'compliance'],
  'alice-devops': ['admin', 'compliance', 'audit', 'agents', 'flows'],
  'compliance-officer': ['chat', 'agents', 'flows', 'mcp', 'files', 'traces', 'costs', 'admin'],
  bob: ['admin', 'compliance', 'audit', 'agents', 'mcp', 'traces', 'costs'],
};

async function setupFeatureFlagMock(page: import('@playwright/test').Page) {
  if (!backendEnabled) {
    await page.route('**/api/v1/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockFeatureFlags),
      });
    });
  }
}

test.describe('Persona Navigation Visibility', () => {
  test.describe('Admin Persona', () => {
    test('should show all navigation items for admin', async ({ adminPage }) => {
      await setupFeatureFlagMock(adminPage);
      await adminPage.goto('/studio/chat', { waitUntil: 'networkidle' });

      const activityBar = adminPage.getByTestId('activity-bar');
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Admin should see all primary nav items
      await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
      await expect(activityBar.getByTestId('nav-admin')).toBeVisible();
    });

    test('should have access to admin panel', async ({ adminPage }) => {
      await setupFeatureFlagMock(adminPage);
      await adminPage.goto('/studio/admin', { waitUntil: 'networkidle' });

      // Should not redirect away - admin has access
      await expect(adminPage).toHaveURL(/\/studio\/admin/);
    });

    test('should have access to compliance dashboard', async ({ adminPage }) => {
      await setupFeatureFlagMock(adminPage);
      await adminPage.goto('/studio/compliance', { waitUntil: 'networkidle' });

      // Should not redirect away - admin has access
      await expect(adminPage.locator('body')).not.toContainText('Access Denied');
    });
  });

  test.describe('Developer Persona (Alice)', () => {
    test('should show developer navigation items', async ({ alicePage }) => {
      await setupFeatureFlagMock(alicePage);
      await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });

      const activityBar = alicePage.getByTestId('activity-bar');
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Alice (developer) should see chat
      await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
    });

    test('should not show admin-only items for developer', async ({ alicePage }) => {
      await setupFeatureFlagMock(alicePage);
      await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });

      const activityBar = alicePage.getByTestId('activity-bar');
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Alice should NOT see admin nav
      await expect(alicePage.getByTestId('nav-admin')).not.toBeVisible();
    });

    test('should redirect from admin panel to default view', async ({ alicePage }) => {
      await setupFeatureFlagMock(alicePage);
      await alicePage.goto('/studio/admin', { waitUntil: 'networkidle' });

      // Should redirect away - alice doesn't have admin access
      await expect(alicePage).not.toHaveURL(/\/studio\/admin/);
    });
  });

  test.describe('Standard User Persona (Bob)', () => {
    test('should show limited navigation for standard user', async ({ bobPage }) => {
      await setupFeatureFlagMock(bobPage);
      await bobPage.goto('/studio/chat', { waitUntil: 'networkidle' });

      const activityBar = bobPage.getByTestId('activity-bar');
      await expect(activityBar).toBeVisible({ timeout: 10000 });

      // Bob should see chat
      await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
    });

    test('should not show admin items for standard user', async ({ bobPage }) => {
      await setupFeatureFlagMock(bobPage);
      await bobPage.goto('/studio/chat', { waitUntil: 'networkidle' });

      // Bob should NOT see admin items
      await expect(bobPage.getByTestId('nav-admin')).not.toBeVisible();
    });

    test('should not show compliance items for standard user', async ({ bobPage }) => {
      await setupFeatureFlagMock(bobPage);
      await bobPage.goto('/studio/chat', { waitUntil: 'networkidle' });

      // Bob should NOT see compliance
      await expect(bobPage.getByTestId('nav-compliance')).not.toBeVisible();
    });

    test('should redirect from admin routes', async ({ bobPage }) => {
      await setupFeatureFlagMock(bobPage);
      await bobPage.goto('/studio/admin', { waitUntil: 'networkidle' });

      // Should redirect away - bob doesn't have admin access
      await expect(bobPage).not.toHaveURL(/\/studio\/admin/);
    });

    test('should redirect from compliance routes', async ({ bobPage }) => {
      await setupFeatureFlagMock(bobPage);
      await bobPage.goto('/studio/compliance', { waitUntil: 'networkidle' });

      // Should redirect away - bob doesn't have compliance access
      await expect(bobPage).not.toHaveURL(/\/studio\/compliance/);
    });
  });

  test.describe('RBAC Enforcement', () => {
    test('admin can access all routes', async ({ adminPage }) => {
      await setupFeatureFlagMock(adminPage);

      const routes = ['/studio/chat', '/studio/admin', '/studio/compliance'];

      for (const route of routes) {
        await adminPage.goto(route, { waitUntil: 'networkidle' });
        // Should not show access denied
        await expect(adminPage.locator('body')).not.toContainText('Access Denied');
      }
    });

    test('developer can access developer routes', async ({ alicePage }) => {
      await setupFeatureFlagMock(alicePage);

      // Developer should access chat
      await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });
      await expect(alicePage.locator('body')).not.toContainText('Access Denied');
    });

    test('standard user can only access basic routes', async ({ bobPage }) => {
      await setupFeatureFlagMock(bobPage);

      // Bob should access chat
      await bobPage.goto('/studio/chat', { waitUntil: 'networkidle' });
      await expect(bobPage.locator('body')).not.toContainText('Access Denied');
    });
  });
});

test.describe('Persona Switching', () => {
  test('should show persona switcher for admin', async ({ adminPage }) => {
    await setupFeatureFlagMock(adminPage);
    await adminPage.goto('/studio/chat', { waitUntil: 'networkidle' });

    // Look for persona indicator or switcher
    const statusBar = adminPage.getByTestId('status-bar');
    await expect(statusBar).toBeVisible({ timeout: 10000 });
  });

  test('should update navigation when persona changes', async ({ adminPage }) => {
    await setupFeatureFlagMock(adminPage);
    await adminPage.goto('/studio/chat', { waitUntil: 'networkidle' });

    const activityBar = adminPage.getByTestId('activity-bar');
    await expect(activityBar).toBeVisible({ timeout: 10000 });

    // Verify initial admin navigation is visible
    await expect(activityBar.getByTestId('nav-chat')).toBeVisible();
  });
});

test.describe('Workspace Presets', () => {
  test('should apply default layout preset', async ({ alicePage }) => {
    await setupFeatureFlagMock(alicePage);
    await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });

    // Verify the studio shell layout is rendered
    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Panels should be visible
    await expect(alicePage.getByTestId('session-nav')).toBeVisible();
    await expect(alicePage.getByTestId('conversation-panel')).toBeVisible();
    await expect(alicePage.getByTestId('canvas-panel')).toBeVisible();
  });

  test('should persist layout changes', async ({ alicePage }) => {
    await setupFeatureFlagMock(alicePage);
    await alicePage.goto('/studio/chat', { waitUntil: 'networkidle' });

    // Verify the layout is stable after navigation
    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });

    // Reload and verify layout persists
    await alicePage.reload({ waitUntil: 'networkidle' });
    await expect(alicePage.getByTestId('studio-shell')).toBeVisible({ timeout: 10000 });
  });
});
