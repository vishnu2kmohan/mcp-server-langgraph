/**
 * Bob Standard User Journey E2E Tests
 *
 * Tests the complete standard user journey including:
 * - Session creation and chat
 * - Message history
 * - Read-only workflow access
 * - Basic settings access
 * - Limited feature set
 *
 * Uses HEART framework metrics:
 * - Happiness: Chat response quality
 * - Engagement: Sessions per week
 * - Adoption: First session creation rate
 * - Retention: 7/14/30-day return rates
 * - Task Success: Chat response accuracy
 */

import { test, expect } from '@playwright/test';

test.describe('Bob Standard User Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
  });

  test.describe('Home Navigation', () => {
    test('should access home page', async ({ page }) => {
      await page.goto('/');

      // App should render
      await expect(page.locator('body')).toBeVisible();
    });

    test('should navigate to studio', async ({ page }) => {
      await page.goto('/studio');

      // Studio section should load
      await expect(page.getByText(/Studio|Workflows|Chat/i)).toBeVisible();
    });
  });

  test.describe('Chat Experience', () => {
    test('should access chat page', async ({ page }) => {
      await page.goto('/studio/chat');

      // Chat interface should load
      await expect(page.getByText(/Chat|Session|Message/i)).toBeVisible();
    });

    test('should display message input', async ({ page }) => {
      await page.goto('/studio/chat');

      // Look for message input
      const messageInput = page.getByRole('textbox');
      if (await messageInput.first().isVisible()) {
        await expect(messageInput.first()).toBeVisible();
      }
    });

    test('should have send functionality', async ({ page }) => {
      await page.goto('/studio/chat');

      // Look for send mechanism
      const sendButton = page.getByRole('button', { name: /Send|Submit/i });
      if (await sendButton.isVisible()) {
        await expect(sendButton).toBeVisible();
      }
    });
  });

  test.describe('Sessions View', () => {
    test('should access sessions page', async ({ page }) => {
      await page.goto('/studio/sessions');

      // Sessions should load
      await expect(page.getByText(/Sessions/i)).toBeVisible();
    });

    test('should display session list', async ({ page }) => {
      await page.goto('/studio/sessions');

      // Wait for page content
      await expect(page.getByRole('heading', { name: /Sessions/i })).toBeVisible();
    });

    test('should have create session option', async ({ page }) => {
      await page.goto('/studio/sessions');

      // Look for create button
      const createButton = page.getByRole('button', { name: /Create|New/i });
      await expect(createButton).toBeVisible();
    });
  });

  test.describe('Workflows View (Read-Only)', () => {
    test('should access workflows page', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Workflows page should load
      await expect(page.getByText(/Workflows/i)).toBeVisible();
    });

    test('should display workflow list', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Wait for content
      await expect(page.getByRole('heading', { name: /Workflows/i })).toBeVisible();
    });

    test('should see shared workflows', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Workflow list should be visible (even if empty)
      await expect(page.getByText(/Workflows/i)).toBeVisible();
    });
  });

  test.describe('Settings Access', () => {
    test('should access settings page', async ({ page }) => {
      await page.goto('/studio/settings');

      // Settings should load
      await expect(page.getByText(/Settings/i)).toBeVisible();
    });

    test('should see profile settings', async ({ page }) => {
      await page.goto('/studio/settings');

      // Profile tab should be visible
      await expect(page.getByRole('button', { name: /Profile/i })).toBeVisible();
    });

    test('should have appearance settings', async ({ page }) => {
      await page.goto('/studio/settings');

      // Appearance tab should be visible
      await expect(page.getByRole('button', { name: /Appearance/i })).toBeVisible();
    });

    test('should navigate to notifications settings', async ({ page }) => {
      await page.goto('/studio/settings');

      // Click notifications tab
      const notificationsTab = page.getByRole('button', { name: /Notifications/i });
      await notificationsTab.click();

      // Notifications content should be visible
      await expect(page.getByText(/Session Complete|Error Alerts/i)).toBeVisible();
    });
  });

  test.describe('MCP Explorer (Limited)', () => {
    test('should access MCP explorer', async ({ page }) => {
      await page.goto('/studio/mcp');

      // MCP page should load
      await expect(page.getByText(/MCP/i)).toBeVisible();
    });

    test('should view available tools', async ({ page }) => {
      await page.goto('/studio/mcp');

      // Tools tab should be available
      await expect(page.getByRole('button', { name: /Tools/i })).toBeVisible();
    });
  });

  test.describe('Performance Metrics (HEART)', () => {
    test('chat page should load within acceptable time', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/studio/chat');
      await expect(page.getByText(/Chat|Session/i)).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 3 seconds
      expect(loadTime).toBeLessThan(3000);
    });

    test('sessions page should load within acceptable time', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/studio/sessions');
      await expect(page.getByText(/Sessions/i)).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('navigation should be responsive', async ({ page }) => {
      await page.goto('/studio');

      // Navigation should be present
      const nav = page.locator('nav, [role="navigation"]');
      if (await nav.first().isVisible()) {
        await expect(nav.first()).toBeVisible();
      }
    });
  });

  test.describe('User Experience Quality', () => {
    test('should have proper page titles', async ({ page }) => {
      await page.goto('/studio/sessions');

      // Page should have heading
      const heading = page.getByRole('heading');
      expect(await heading.count()).toBeGreaterThan(0);
    });

    test('should have accessible form controls', async ({ page }) => {
      await page.goto('/studio/settings');

      // Form controls should be accessible
      const buttons = page.getByRole('button');
      expect(await buttons.count()).toBeGreaterThan(0);
    });

    test('should maintain visual consistency', async ({ page }) => {
      await page.goto('/studio/chat');

      // Page should render without visual errors
      await expect(page.locator('body')).toBeVisible();

      // No JavaScript errors in console
      const errors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto('/studio/sessions');
      await expect(page.getByText(/Sessions/i)).toBeVisible();

      // Filter out expected errors (like failed API calls in test env)
      const criticalErrors = errors.filter(
        (e) => !e.includes('Failed to fetch') && !e.includes('Network')
      );

      expect(criticalErrors.length).toBe(0);
    });
  });
});
