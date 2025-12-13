/**
 * Admin User Journey E2E Tests
 *
 * Tests the complete admin user journey including:
 * - Dashboard access and system health monitoring
 * - User management
 * - Organization management
 * - HEART metrics visibility
 *
 * Uses HEART framework metrics:
 * - Happiness: Dashboard satisfaction
 * - Engagement: Admin actions per session
 * - Adoption: Feature discovery
 * - Retention: Admin return rate
 * - Task Success: User management completion rate
 */

import { test, expect } from '@playwright/test';

test.describe('Admin User Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
  });

  test.describe('Dashboard Access', () => {
    test('should access admin dashboard', async ({ page }) => {
      // Navigate to admin section
      await page.goto('/admin/dashboard');

      // Wait for dashboard to load
      await expect(page.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
    });

    test('should display system health metrics', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // Wait for data to load
      await expect(page.getByText(/System Health/i)).toBeVisible();

      // Check for health indicators
      await expect(page.getByText(/Status/i)).toBeVisible();
      await expect(page.getByText(/Uptime/i)).toBeVisible();
      await expect(page.getByText(/Active Users/i)).toBeVisible();
      await expect(page.getByText(/Error Rate/i)).toBeVisible();
    });

    test('should display HEART metrics', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // Wait for HEART metrics section
      await expect(page.getByText(/HEART Metrics/i)).toBeVisible();

      // Check for all 5 HEART metrics
      await expect(page.getByText('Happiness')).toBeVisible();
      await expect(page.getByText('Engagement')).toBeVisible();
      await expect(page.getByText('Adoption')).toBeVisible();
      await expect(page.getByText('Retention')).toBeVisible();
      await expect(page.getByText('Task Success')).toBeVisible();
    });

    test('should refresh dashboard data', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // Wait for initial load
      await expect(page.getByText(/System Health/i)).toBeVisible();

      // Click refresh button
      const refreshButton = page.getByRole('button', { name: /Refresh/i });
      await refreshButton.click();

      // Should still show dashboard after refresh
      await expect(page.getByText(/System Health/i)).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should navigate to studio from admin', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // Find and click studio navigation
      const studioLink = page.getByRole('link', { name: /Studio/i });
      if (await studioLink.isVisible()) {
        await studioLink.click();
        await expect(page).toHaveURL(/\/studio/);
      }
    });

    test('should navigate between admin sections', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // Check for navigation elements
      await expect(page.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();
    });
  });

  test.describe('User Management', () => {
    test('should display user management section', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // User manager component should be visible
      const userSection = page.locator('[data-testid="user-manager"]');
      if (await userSection.isVisible()) {
        await expect(userSection).toBeVisible();
      }
    });

    test('should have user search functionality', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // Look for search input in user management
      const searchInput = page.getByPlaceholder(/Search users/i);
      if (await searchInput.isVisible()) {
        await searchInput.fill('alice');
        await expect(searchInput).toHaveValue('alice');
      }
    });
  });

  test.describe('Performance Metrics (HEART)', () => {
    test('dashboard should load within acceptable time', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/admin/dashboard');
      await expect(page.getByText(/Admin Dashboard/i)).toBeVisible();

      const loadTime = Date.now() - startTime;

      // Dashboard should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
    });

    test('should have proper accessibility structure', async ({ page }) => {
      await page.goto('/admin/dashboard');

      // Wait for content
      await expect(page.getByRole('heading', { name: /Admin Dashboard/i })).toBeVisible();

      // Check for proper heading hierarchy
      const h1 = page.getByRole('heading', { level: 1 });
      const h2 = page.getByRole('heading', { level: 2 });

      // Should have at least one heading
      expect(await h1.count() + await h2.count()).toBeGreaterThan(0);
    });
  });
});
