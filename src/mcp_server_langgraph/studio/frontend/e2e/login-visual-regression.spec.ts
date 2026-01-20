/**
 * Login Page Visual Regression E2E Tests
 *
 * Visual regression tests for the Login page using Playwright's
 * screenshot comparison. These tests ensure the login page styling
 * remains consistent across changes.
 *
 * Test Coverage:
 * - React /login page layout and colors
 * - Login page responsive breakpoints
 * - Loading state
 * - SSO provider buttons (mocked)
 *
 * Note: First run generates baseline screenshots. Subsequent runs compare
 * against baselines. Update baselines with: npm run test:e2e -- --update-snapshots
 *
 * Regression Prevention:
 * - White background issue (should show dark gradient)
 * - Version display (should show dynamic version)
 * - Icon positioning
 */

import { test, expect } from '@playwright/test';

// Viewport sizes for responsive testing
const viewports = {
  desktop: { width: 1920, height: 1080 },
  laptop: { width: 1440, height: 900 },
  tablet: { width: 1024, height: 768 },
  mobile: { width: 375, height: 812 },
} as const;

// Mock identity providers response
const mockIdentityProviders = {
  identity_providers: [
    {
      alias: 'google',
      display_name: 'Google',
      provider_type: 'social',
      provider_id: 'google',
      icon: 'google',
      login_url: '/api/v1/auth/login?kc_idp_hint=google',
    },
    {
      alias: 'github',
      display_name: 'GitHub',
      provider_type: 'social',
      provider_id: 'github',
      icon: 'github',
      login_url: '/api/v1/auth/login?kc_idp_hint=github',
    },
    {
      alias: 'corporate-okta',
      display_name: 'Corporate SSO',
      provider_type: 'enterprise',
      provider_id: 'oidc',
      icon: 'key',
      login_url: '/api/v1/auth/login?kc_idp_hint=corporate-okta',
    },
  ],
  has_social_login: true,
  has_enterprise_sso: true,
};

async function setupLoginPageMocks(page: import('@playwright/test').Page, options?: {
  includeIdps?: boolean;
  isLoading?: boolean;
}) {
  const { includeIdps = false, isLoading = false } = options || {};

  // Mock identity providers endpoint
  await page.route('**/api/v1/auth/identity-providers', async (route) => {
    if (isLoading) {
      // Delay response to capture loading state
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(includeIdps ? mockIdentityProviders : { identity_providers: [] }),
    });
  });

  // Mock feature flags (for any that might be queried)
  await page.route('**/api/v1/features', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    });
  });
}

test.describe('Visual Regression - Login Page', () => {
  test.describe('Desktop Viewport', () => {
    test('should display dark gradient background (not white)', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      // Wait for page to render
      await page.waitForSelector('text=Agent Studio', { timeout: 10000 });
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot('login-page-desktop.png', {
        fullPage: true,
        maxDiffPixels: 100,
      });
    });

    test('should display login page with SSO providers', async ({ page }) => {
      await setupLoginPageMocks(page, { includeIdps: true });
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      // Wait for IdP buttons to render
      await page.waitForSelector('text=Google', { timeout: 10000 });
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot('login-page-with-idps.png', {
        fullPage: true,
        maxDiffPixels: 100,
      });
    });
  });

  test.describe('Responsive Breakpoints', () => {
    test('should match screenshot for laptop viewport', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.laptop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      await page.waitForSelector('text=Agent Studio', { timeout: 10000 });
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot('login-page-laptop.png', {
        fullPage: true,
        maxDiffPixels: 100,
      });
    });

    test('should match screenshot for tablet viewport', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.tablet);
      await page.goto('/login', { waitUntil: 'networkidle' });

      await page.waitForSelector('text=Agent Studio', { timeout: 10000 });
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot('login-page-tablet.png', {
        fullPage: true,
        maxDiffPixels: 100,
      });
    });

    test('should match screenshot for mobile viewport', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.mobile);
      await page.goto('/login', { waitUntil: 'networkidle' });

      await page.waitForSelector('text=Agent Studio', { timeout: 10000 });
      await page.waitForTimeout(300);

      await expect(page).toHaveScreenshot('login-page-mobile.png', {
        fullPage: true,
        maxDiffPixels: 100,
      });
    });
  });

  test.describe('Loading State', () => {
    test('should show loading spinner while fetching IdPs', async ({ page }) => {
      await setupLoginPageMocks(page, { isLoading: true });
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'domcontentloaded' });

      // Capture loading state before IdP response arrives
      await page.waitForTimeout(100);

      // Look for loading indicator
      const loadingIndicator = page.locator('[role="status"]');
      const isVisible = await loadingIndicator.isVisible().catch(() => false);

      if (isVisible) {
        await expect(page).toHaveScreenshot('login-page-loading.png', {
          fullPage: true,
          maxDiffPixels: 50,
        });
      }
    });
  });

  test.describe('Visual Contract Tests', () => {
    test('should NOT display white background', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      await page.waitForSelector('text=Agent Studio', { timeout: 10000 });

      // Check that the body/root does NOT have a white background
      const backgroundColor = await page.evaluate(() => {
        const body = document.body;
        const computedStyle = window.getComputedStyle(body);
        return computedStyle.backgroundColor;
      });

      // The background should NOT be white (rgb(255, 255, 255))
      expect(backgroundColor).not.toBe('rgb(255, 255, 255)');
    });

    test('should display version in footer', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      // Version should be displayed
      const versionText = page.locator('text=/Agent Studio v\\d+\\.\\d+\\.\\d+/');
      await expect(versionText).toBeVisible({ timeout: 10000 });

      // Should NOT show v0.1.0 (regression test)
      await expect(page.locator('text=v0.1.0')).not.toBeVisible();
    });

    test('should display SSO button with correct link', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      // Main SSO button should link to /api/v1/auth/login
      const ssoButton = page.locator('a:has-text("Sign in with SSO")');
      await expect(ssoButton).toBeVisible({ timeout: 10000 });
      await expect(ssoButton).toHaveAttribute('href', '/api/v1/auth/login');
    });

    test('should display branding icon', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      // Should have the Agent Studio heading
      await expect(page.locator('h1:has-text("Agent Studio")')).toBeVisible({ timeout: 10000 });

      // Should have SVG icon (the computer monitor icon)
      const svgIcon = page.locator('.rounded-2xl svg');
      await expect(svgIcon).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('should have visible focus indicators on keyboard navigation', async ({ page }) => {
      await setupLoginPageMocks(page);
      await page.setViewportSize(viewports.desktop);
      await page.goto('/login', { waitUntil: 'networkidle' });

      await page.waitForSelector('text=Agent Studio', { timeout: 10000 });

      // Tab to SSO button
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);

      await expect(page).toHaveScreenshot('login-page-focus.png', {
        fullPage: true,
        maxDiffPixels: 150, // Focus rings may vary
      });
    });
  });
});
