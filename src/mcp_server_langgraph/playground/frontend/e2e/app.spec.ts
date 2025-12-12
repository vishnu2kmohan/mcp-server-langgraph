/**
 * App E2E Tests
 *
 * End-to-end tests for the Interactive Playground application.
 */

import { test, expect } from '@playwright/test';

test.describe('App Layout', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat/');
  });

  test('should display the header with title', async ({ page }) => {
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByText('Interactive Playground')).toBeVisible();
  });

  test('should display the sidebar', async ({ page }) => {
    await expect(page.getByRole('complementary')).toBeVisible();
  });

  test('should display the main content area', async ({ page }) => {
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('should have dark mode toggle', async ({ page }) => {
    const darkModeToggle = page.getByRole('button', { name: /toggle dark mode/i });
    await expect(darkModeToggle).toBeVisible();
  });

  test('should toggle dark mode on click', async ({ page }) => {
    const html = page.locator('html');
    const darkModeToggle = page.getByRole('button', { name: /toggle dark mode/i });

    // Initially should be light mode
    await expect(html).not.toHaveClass(/dark/);

    // Click to enable dark mode
    await darkModeToggle.click();
    await expect(html).toHaveClass(/dark/);

    // Click to disable dark mode
    await darkModeToggle.click();
    await expect(html).not.toHaveClass(/dark/);
  });

  test('should toggle dark mode with keyboard shortcut', async ({ page }) => {
    const html = page.locator('html');

    // Initially should be light mode
    await expect(html).not.toHaveClass(/dark/);

    // Press Ctrl+Shift+T
    await page.keyboard.press('Control+Shift+T');
    await expect(html).toHaveClass(/dark/);

    // Press again to toggle back
    await page.keyboard.press('Control+Shift+T');
    await expect(html).not.toHaveClass(/dark/);
  });
});

test.describe('Sidebar', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat/');
  });

  test('should display Sessions section', async ({ page }) => {
    await expect(page.getByText('Sessions')).toBeVisible();
  });

  test('should display New Session button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /new session/i })).toBeVisible();
  });

  test('should collapse sidebar when toggle clicked', async ({ page }) => {
    const sidebar = page.getByRole('complementary');
    const toggleButton = page.getByRole('button', { name: /collapse sidebar/i });

    // Initially expanded (w-80 = 320px)
    await expect(sidebar).toHaveCSS('width', '320px');

    // Click to collapse
    await toggleButton.click();

    // Should be collapsed (w-16 = 64px)
    await expect(sidebar).toHaveCSS('width', '64px');
  });

  test('should persist sidebar state after reload', async ({ page }) => {
    const sidebar = page.getByRole('complementary');
    const toggleButton = page.getByRole('button', { name: /collapse sidebar/i });

    // Collapse sidebar
    await toggleButton.click();
    await expect(sidebar).toHaveCSS('width', '64px');

    // Reload page
    await page.reload();

    // Should still be collapsed
    await expect(sidebar).toHaveCSS('width', '64px');
  });
});

test.describe('Session Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat/');
  });

  test('should open create session modal', async ({ page }) => {
    const newSessionButton = page.getByRole('button', { name: /new session/i });
    await newSessionButton.click();

    // Modal should be visible
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Create New Session')).toBeVisible();
  });

  test('should close modal on cancel', async ({ page }) => {
    const newSessionButton = page.getByRole('button', { name: /new session/i });
    await newSessionButton.click();

    const cancelButton = page.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    // Modal should be hidden
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
});

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat/');
  });

  test('should display chat input', async ({ page }) => {
    const chatInput = page.getByPlaceholder(/type a message/i);
    await expect(chatInput).toBeVisible();
  });

  test('should display send button', async ({ page }) => {
    const sendButton = page.getByRole('button', { name: /send/i });
    await expect(sendButton).toBeVisible();
  });

  test('should enable send button when input has text', async ({ page }) => {
    const chatInput = page.getByPlaceholder(/type a message/i);
    const sendButton = page.getByRole('button', { name: /send/i });

    // Initially disabled
    await expect(sendButton).toBeDisabled();

    // Type something
    await chatInput.fill('Hello, world!');

    // Should be enabled
    await expect(sendButton).not.toBeDisabled();
  });
});

test.describe('Connection Status', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat/');
  });

  test('should display connection status indicator', async ({ page }) => {
    const statusIndicator = page.getByLabel('MCP Connection Status');
    await expect(statusIndicator).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat/');
  });

  test('should have proper page structure', async ({ page }) => {
    // Should have exactly one banner (header)
    await expect(page.getByRole('banner')).toHaveCount(1);

    // Should have exactly one main
    await expect(page.getByRole('main')).toHaveCount(1);

    // Should have complementary (sidebar)
    await expect(page.getByRole('complementary')).toHaveCount(1);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    // Should have h1 for main title
    const h1 = page.locator('h1');
    await expect(h1).toHaveCount(1);
    await expect(h1).toContainText('Interactive Playground');
  });

  test('should be keyboard navigable', async ({ page }) => {
    // Tab should move focus
    await page.keyboard.press('Tab');

    // Something should be focused
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });
});

test.describe('Responsive Design', () => {
  test('should adapt to mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/chat/');

    // Page should still render
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('should adapt to tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/chat/');

    // Page should still render
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByRole('main')).toBeVisible();
  });
});
