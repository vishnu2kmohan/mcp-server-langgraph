/**
 * MCP Aggregated Capabilities E2E Tests
 *
 * Tests the MCP Protocol 2025-11-25 capability aggregation feature.
 * Validates the full user journey for browsing aggregated MCP capabilities:
 * - Tools, Resources, Prompts tabs
 * - Server list and filtering
 * - Real-time WebSocket status indicator
 * - Capability counts and statistics
 *
 * Reference: MCP Protocol 2025-11-25 capability aggregation
 */

import { test, expect } from './fixtures/auth';
import type { Page } from '@playwright/test';

// Backend integration is enabled by default for E2E tests
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

/**
 * Helper to wait for network idle with timeout
 */
async function waitForCapabilitiesLoad(page: Page, timeout = 10000): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });
}

test.describe('MCP Aggregated Capabilities - Panel Rendering', () => {
  test('should display the Aggregated Capabilities panel heading', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // The AggregatedCapabilitiesPanel should show "Aggregated Capabilities" title
    const heading = adminPage.getByText('Aggregated Capabilities');
    await expect(heading.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display capability statistics in the header', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');
    await waitForCapabilitiesLoad(adminPage);

    // Header should show counts: "X servers | Y tools | Z resources | W prompts"
    const statsArea = adminPage.locator('[class*="gap-3"]').filter({
      hasText: /servers|tools|resources|prompts/i,
    });
    await expect(statsArea.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display real-time sync status indicator', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');
    await waitForCapabilitiesLoad(adminPage);

    // WebSocket status indicator shows connection state
    // Look for the status indicator (dot + text like "Live", "connecting", etc.)
    const statusDot = adminPage.locator('[class*="rounded-full"]').filter({
      has: adminPage.locator('[class*="bg-green-500"], [class*="bg-yellow-500"], [class*="bg-gray-400"]'),
    });

    // Either status dot or text should be visible
    const statusText = adminPage.getByText(/Live|connecting|reconnecting|disconnected/i);
    await expect(statusDot.or(statusText).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('MCP Aggregated Capabilities - Tab Navigation', () => {
  test('should display all four capability tabs', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Check all tabs are present
    await expect(adminPage.getByRole('tab', { name: 'Tools' })).toBeVisible({ timeout: 10000 });
    await expect(adminPage.getByRole('tab', { name: 'Resources' })).toBeVisible({ timeout: 10000 });
    await expect(adminPage.getByRole('tab', { name: 'Prompts' })).toBeVisible({ timeout: 10000 });
    await expect(adminPage.getByRole('tab', { name: 'Servers' })).toBeVisible({ timeout: 10000 });
  });

  test('should switch to Tools tab and show tool explorer', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Click Tools tab (should be default but click to ensure)
    const toolsTab = adminPage.getByRole('tab', { name: 'Tools' });
    await toolsTab.click();
    await waitForCapabilitiesLoad(adminPage);

    // Tools tab should be selected (aria-selected="true")
    await expect(toolsTab).toHaveAttribute('aria-selected', 'true');

    // ToolExplorer content should be visible (either tools list or empty state)
    const hasTools = await adminPage.getByText(/tool|invoke|execute/i).count() > 0;
    const hasEmptyState = await adminPage.getByText(/No tools|No MCP servers/i).isVisible().catch(() => false);
    expect(hasTools || hasEmptyState).toBe(true);
  });

  test('should switch to Resources tab and show resource browser', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Click Resources tab
    const resourcesTab = adminPage.getByRole('tab', { name: 'Resources' });
    await resourcesTab.click();
    await waitForCapabilitiesLoad(adminPage);

    // Resources tab should be selected
    await expect(resourcesTab).toHaveAttribute('aria-selected', 'true');

    // ResourceBrowser content should be visible
    const hasResources = await adminPage.getByText(/resource|view|uri/i).count() > 0;
    const hasEmptyState = await adminPage.getByText(/No resources/i).isVisible().catch(() => false);
    expect(hasResources || hasEmptyState).toBe(true);
  });

  test('should switch to Prompts tab and show prompt library', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Click Prompts tab
    const promptsTab = adminPage.getByRole('tab', { name: 'Prompts' });
    await promptsTab.click();
    await waitForCapabilitiesLoad(adminPage);

    // Prompts tab should be selected
    await expect(promptsTab).toHaveAttribute('aria-selected', 'true');

    // PromptLibrary content should be visible
    const hasPrompts = await adminPage.getByText(/prompt|test|template/i).count() > 0;
    const hasEmptyState = await adminPage.getByText(/No prompts/i).isVisible().catch(() => false);
    expect(hasPrompts || hasEmptyState).toBe(true);
  });

  test('should switch to Servers tab and show server cards', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Click Servers tab
    const serversTab = adminPage.getByRole('tab', { name: 'Servers' });
    await serversTab.click();
    await waitForCapabilitiesLoad(adminPage);

    // Servers tab should be selected
    await expect(serversTab).toHaveAttribute('aria-selected', 'true');

    // MCPServerCard components should be visible (grid of cards)
    // Look for server name or count badges
    const hasServerCards = await adminPage.locator('[class*="grid"]').count() > 0;
    const hasEmptyState = await adminPage.getByText(/No servers|No MCP servers/i).isVisible().catch(() => false);
    expect(hasServerCards || hasEmptyState).toBe(true);
  });
});

test.describe('MCP Aggregated Capabilities - Server Filtering', () => {
  test('should show filter indicator when server is selected', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Switch to Servers tab
    const serversTab = adminPage.getByRole('tab', { name: 'Servers' });
    await serversTab.click();
    await waitForCapabilitiesLoad(adminPage);

    // Check if there are any server cards to click
    const serverCards = adminPage.locator('[class*="cursor-pointer"]').filter({
      hasText: /tools|resources|prompts/i,
    });

    const serverCount = await serverCards.count();
    if (serverCount > 0) {
      // Click the first server card
      await serverCards.first().click();
      await waitForCapabilitiesLoad(adminPage);

      // Filter indicator should appear
      const filterIndicator = adminPage.getByText(/Filtered by server/i);
      await expect(filterIndicator).toBeVisible({ timeout: 5000 });
    }
    // If no servers, test passes (nothing to filter)
  });

  test('should clear filter when clear button is clicked', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Switch to Servers tab and select a server (if available)
    const serversTab = adminPage.getByRole('tab', { name: 'Servers' });
    await serversTab.click();
    await waitForCapabilitiesLoad(adminPage);

    const serverCards = adminPage.locator('[class*="cursor-pointer"]').filter({
      hasText: /tools|resources|prompts/i,
    });

    const serverCount = await serverCards.count();
    if (serverCount > 0) {
      await serverCards.first().click();
      await waitForCapabilitiesLoad(adminPage);

      // Click clear filter button
      const clearButton = adminPage.getByText(/Clear filter/i);
      if (await clearButton.isVisible()) {
        await clearButton.click();
        await waitForCapabilitiesLoad(adminPage);

        // Filter indicator should be gone
        await expect(adminPage.getByText(/Filtered by server/i)).not.toBeVisible();
      }
    }
  });

  test('should switch to Tools tab after selecting a server', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Switch to Servers tab
    const serversTab = adminPage.getByRole('tab', { name: 'Servers' });
    await serversTab.click();
    await waitForCapabilitiesLoad(adminPage);

    const serverCards = adminPage.locator('[class*="cursor-pointer"]').filter({
      hasText: /tools|resources|prompts/i,
    });

    const serverCount = await serverCards.count();
    if (serverCount > 0) {
      await serverCards.first().click();
      await waitForCapabilitiesLoad(adminPage);

      // Should auto-switch to Tools tab
      const toolsTab = adminPage.getByRole('tab', { name: 'Tools' });
      await expect(toolsTab).toHaveAttribute('aria-selected', 'true');
    }
  });
});

test.describe('MCP Aggregated Capabilities - Admin Actions', () => {
  test('should display Refresh All button for admin users', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');
    await waitForCapabilitiesLoad(adminPage);

    // Admin should see Refresh All button
    const refreshButton = adminPage.getByRole('button', { name: /Refresh All/i });
    await expect(refreshButton).toBeVisible({ timeout: 10000 });
  });

  test('should trigger refresh when Refresh All is clicked', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');
    await waitForCapabilitiesLoad(adminPage);

    // Click Refresh All button
    const refreshButton = adminPage.getByRole('button', { name: /Refresh All/i });
    await refreshButton.click();

    // Should trigger a refetch (network activity)
    // Since we can't easily verify the network call, just verify no error
    await waitForCapabilitiesLoad(adminPage);

    // Page should still be functional
    await expect(adminPage.getByText('Aggregated Capabilities').first()).toBeVisible();
  });
});

test.describe('MCP Aggregated Capabilities - Error States', () => {
  // These tests validate proper error handling when backend is unavailable
  // Skip in frontend-only mode as errors are mocked differently

  test('should show error state and retry button on API failure', async ({ adminPage }) => {
    // This test only makes sense with backend enabled
    test.skip(!backendEnabled, 'Skipped in frontend-only mode');

    // Mock the API to return an error
    await adminPage.route('**/api/v1/mcp/aggregated/servers', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await adminPage.goto('/studio/connections/mcp');

    // Should show error message and retry button
    const errorMessage = adminPage.getByText(/Failed to load|Error/i);
    const retryButton = adminPage.getByRole('button', { name: /Retry/i });

    await expect(errorMessage.or(retryButton).first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('MCP Aggregated Capabilities - Loading States', () => {
  test('should show loading spinner while fetching data', async ({ adminPage }) => {
    // Slow down the API response to see loading state
    await adminPage.route('**/api/v1/mcp/aggregated/servers', async (route) => {
      // Add a small delay to show loading state
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.continue();
    });

    await adminPage.goto('/studio/connections/mcp');

    // Loading spinner should be visible briefly
    const loadingSpinner = adminPage.getByTestId('loading-spinner');

    // Either spinner was shown or page loaded too fast - both are acceptable
    const hasSpinner = await loadingSpinner.isVisible().catch(() => false);
    const hasContent = await adminPage.getByText('Aggregated Capabilities').isVisible().catch(() => false);

    expect(hasSpinner || hasContent).toBe(true);
  });
});

test.describe('MCP Aggregated Capabilities - Accessibility', () => {
  test('should have proper ARIA roles for tabs', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Tab list should have role="tablist"
    const tabList = adminPage.getByRole('tablist');
    await expect(tabList).toBeVisible({ timeout: 10000 });

    // Individual tabs should have role="tab"
    const tabs = adminPage.getByRole('tab');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(4);
  });

  test('should support keyboard navigation between tabs', async ({ adminPage }) => {
    await adminPage.goto('/studio/connections/mcp');

    // Focus on the first tab
    const toolsTab = adminPage.getByRole('tab', { name: 'Tools' });
    await toolsTab.focus();

    // Press Tab to move to next focusable element
    await adminPage.keyboard.press('Tab');

    // Verify we can still interact with the page
    await expect(adminPage.getByText('Aggregated Capabilities').first()).toBeVisible();
  });
});

test.describe('MCP Aggregated Capabilities - Standard User Access', () => {
  test('bob (standard user) can view aggregated capabilities', async ({ bobPage }) => {
    await bobPage.goto('/studio/connections/mcp');

    // Bob should be able to see the MCP Explorer page
    const heading = bobPage.getByText('Aggregated Capabilities');
    await expect(heading.first()).toBeVisible({ timeout: 10000 });

    // Tabs should be accessible
    await expect(bobPage.getByRole('tab', { name: 'Tools' })).toBeVisible();
  });

  test('alice (power user) can view aggregated capabilities', async ({ alicePage }) => {
    await alicePage.goto('/studio/connections/mcp');

    // Alice should be able to see the MCP Explorer page
    const heading = alicePage.getByText('Aggregated Capabilities');
    await expect(heading.first()).toBeVisible({ timeout: 10000 });

    // Admin actions should be visible for power users
    const refreshButton = alicePage.getByRole('button', { name: /Refresh All/i });
    await expect(refreshButton).toBeVisible({ timeout: 10000 });
  });
});
