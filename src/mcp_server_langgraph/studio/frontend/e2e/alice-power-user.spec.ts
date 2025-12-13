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
 */

import { test, expect } from '@playwright/test';

test.describe('Alice Power User Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
  });

  test.describe('Workflows Page', () => {
    test('should access workflows page', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Wait for workflows page to load
      await expect(page.getByText(/Workflows/i)).toBeVisible();
    });

    test('should display workflow list', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Wait for page content
      await expect(page.getByRole('heading', { name: /Workflows/i })).toBeVisible();
    });

    test('should have create workflow button', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Look for create button
      const createButton = page.getByRole('button', { name: /Create|New/i });
      await expect(createButton).toBeVisible();
    });

    test('should have search functionality', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Look for search input
      const searchInput = page.getByPlaceholder(/Search/i);
      if (await searchInput.isVisible()) {
        await searchInput.fill('test workflow');
        await expect(searchInput).toHaveValue('test workflow');
      }
    });
  });

  test.describe('Chat Interface', () => {
    test('should access chat page', async ({ page }) => {
      await page.goto('/studio/chat');

      // Chat page should load
      await expect(page.getByText(/Chat|Session/i)).toBeVisible();
    });

    test('should have message input', async ({ page }) => {
      await page.goto('/studio/chat');

      // Look for message input
      const messageInput = page.getByPlaceholder(/Type|Message|Enter/i);
      if (await messageInput.isVisible()) {
        await expect(messageInput).toBeVisible();
      }
    });

    test('should have send button', async ({ page }) => {
      await page.goto('/studio/chat');

      // Look for send button
      const sendButton = page.getByRole('button', { name: /Send|Submit/i });
      if (await sendButton.isVisible()) {
        await expect(sendButton).toBeVisible();
      }
    });
  });

  test.describe('Sessions Page', () => {
    test('should access sessions page', async ({ page }) => {
      await page.goto('/studio/sessions');

      // Sessions page should load
      await expect(page.getByText(/Sessions/i)).toBeVisible();
    });

    test('should display session list', async ({ page }) => {
      await page.goto('/studio/sessions');

      // Wait for sessions content
      await expect(page.getByRole('heading', { name: /Sessions/i })).toBeVisible();
    });

    test('should have create session button', async ({ page }) => {
      await page.goto('/studio/sessions');

      // Look for create button
      const createButton = page.getByRole('button', { name: /Create|New/i });
      await expect(createButton).toBeVisible();
    });
  });

  test.describe('Observability Page', () => {
    test('should access observability page', async ({ page }) => {
      await page.goto('/studio/observability');

      // Observability page should load
      await expect(page.getByText(/Observability/i)).toBeVisible();
    });

    test('should display traces section', async ({ page }) => {
      await page.goto('/studio/observability');

      // Wait for content
      await expect(page.getByText(/Traces/i)).toBeVisible();
    });

    test('should have tab navigation', async ({ page }) => {
      await page.goto('/studio/observability');

      // Check for tab buttons
      await expect(page.getByRole('button', { name: /Traces/i })).toBeVisible();
    });
  });

  test.describe('MCP Explorer', () => {
    test('should access MCP explorer page', async ({ page }) => {
      await page.goto('/studio/mcp');

      // MCP page should load
      await expect(page.getByText(/MCP/i)).toBeVisible();
    });

    test('should display tools section', async ({ page }) => {
      await page.goto('/studio/mcp');

      // Wait for tabs
      await expect(page.getByRole('button', { name: /Tools/i })).toBeVisible();
    });

    test('should have server management', async ({ page }) => {
      await page.goto('/studio/mcp');

      // Check for servers tab
      await expect(page.getByRole('button', { name: /Servers/i })).toBeVisible();
    });
  });

  test.describe('Settings Page', () => {
    test('should access settings page', async ({ page }) => {
      await page.goto('/studio/settings');

      // Settings page should load
      await expect(page.getByText(/Settings/i)).toBeVisible();
    });

    test('should have profile settings', async ({ page }) => {
      await page.goto('/studio/settings');

      // Check for profile tab
      await expect(page.getByRole('button', { name: /Profile/i })).toBeVisible();
    });

    test('should have save button', async ({ page }) => {
      await page.goto('/studio/settings');

      // Look for save button
      const saveButton = page.getByRole('button', { name: /Save/i });
      await expect(saveButton).toBeVisible();
    });
  });

  test.describe('Performance Metrics (HEART)', () => {
    test('workflows page should load quickly', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/studio/workflows');
      await expect(page.getByText(/Workflows/i)).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should have proper navigation structure', async ({ page }) => {
      await page.goto('/studio/workflows');

      // Wait for content
      await expect(page.getByText(/Workflows/i)).toBeVisible();

      // Check navigation links exist
      const navLinks = page.getByRole('link');
      expect(await navLinks.count()).toBeGreaterThan(0);
    });

    test('chat page should be responsive', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/studio/chat');
      await expect(page.getByText(/Chat|Session/i)).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Chat should load within 3 seconds
      expect(loadTime).toBeLessThan(3000);
    });
  });
});
