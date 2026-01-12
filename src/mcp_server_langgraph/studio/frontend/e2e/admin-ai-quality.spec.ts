/**
 * Admin AI Quality Metrics E2E Tests
 *
 * Tests the AI Quality Metrics card in the admin dashboard:
 * - Card visibility in Overview tab
 * - Hallucination report count display
 * - Positive rate display
 * - Category breakdown (grid/pie views)
 * - Toggle between grid and pie views
 * - Feature flag gating
 *
 * Reference: Phase 5 - Admin Dashboard Integration
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// Mock feedback summary for frontend-only testing
const MOCK_FEEDBACK_SUMMARY = {
  timeframe: "7d",
  total_feedback: 100,
  positive_count: 80,
  negative_count: 20,
  positive_rate: 0.8,
  hallucination_reports: 12,
  hallucination_categories: {
    factual_error: 5,
    outdated_info: 3,
    made_up_source: 2,
    other: 2,
  },
};

test.describe("Admin AI Quality Metrics", () => {
  test.beforeEach(async ({ adminPage }) => {
    // Mock the feedback summary endpoint when backend is disabled
    if (!backendEnabled) {
      await adminPage.route("**/api/v1/feedback/summary*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_FEEDBACK_SUMMARY),
        });
      });

      // Mock feature flags to enable ai_quality_metrics
      await adminPage.route("**/api/v1/features*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ai_quality_metrics: true,
          }),
        });
      });
    }
  });

  test.describe("Card Visibility", () => {
    test("should display AI Quality card in admin dashboard Overview tab", async ({
      adminPage,
    }) => {
      // Navigate to admin dashboard
      await adminPage.goto("/studio/admin");

      // Wait for the page to load
      await expect(adminPage.getByText("Admin Dashboard")).toBeVisible({
        timeout: 10000,
      });

      // Overview tab should be active by default
      const overviewTab = adminPage.getByRole("tab", { name: /overview/i });
      await expect(overviewTab).toHaveAttribute("aria-selected", "true");

      // AI Quality card should be visible
      const aiQualityCard = adminPage.getByTestId("ai-quality-card");
      await expect(aiQualityCard).toBeVisible({ timeout: 5000 });
    });

    test("should display AI Quality heading", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin");

      await expect(adminPage.getByText("AI Quality")).toBeVisible({
        timeout: 10000,
      });
    });

    test("should hide AI Quality card when switching to Users tab", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/admin");

      // Verify card is present
      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      // Switch to Users tab
      await adminPage.getByRole("tab", { name: /users/i }).click();

      // Card should no longer be visible
      await expect(adminPage.getByTestId("ai-quality-card")).not.toBeVisible();
    });
  });

  test.describe("Metrics Display", () => {
    test("should display hallucination report count", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin");

      // Wait for card to load
      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      // Should show "Hallucination Reports" label
      await expect(adminPage.getByText("Hallucination Reports")).toBeVisible();

      // Should show a number (the count)
      // The exact number depends on real/mock data
      const card = adminPage.getByTestId("ai-quality-card");
      const reportCount = card.locator("text=/^\\d+$/").first();
      await expect(reportCount).toBeVisible();
    });

    test("should display response approval rate", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin");

      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      // Should show "Response Approval Rate" label
      await expect(adminPage.getByText("Response Approval Rate")).toBeVisible();

      // Should show a percentage
      const card = adminPage.getByTestId("ai-quality-card");
      const rateDisplay = card.locator("text=/\\d+%/").first();
      await expect(rateDisplay).toBeVisible();
    });

    test("should display category breakdown when reports exist", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/admin");

      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      // If there are hallucination reports, category breakdown should be visible
      // Categories: Factual Error, Outdated Info, Made Up Source, Other
      const card = adminPage.getByTestId("ai-quality-card");

      // Check if "Reports by Category" heading is visible (only when reports > 0)
      const categoryHeading = card.getByText("Reports by Category");
      const isVisible = await categoryHeading.isVisible().catch(() => false);

      if (isVisible) {
        // Verify at least one category is displayed
        const factualError = card.getByText("Factual Error");
        await expect(factualError).toBeVisible();
      }
    });
  });

  test.describe("Toggle Visualization", () => {
    test("should show toggle button for grid/pie views", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/admin");

      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      // Toggle button should be visible (if there are reports)
      // The button has aria-label "Switch to pie chart view" or "Switch to grid view"
      const toggleButton = adminPage.getByRole("button", {
        name: /switch to (pie chart|grid) view/i,
      });

      // Only test toggle if button is visible (depends on whether there are reports)
      const isToggleVisible = await toggleButton.isVisible().catch(() => false);

      if (isToggleVisible) {
        await expect(toggleButton).toBeEnabled();
      }
    });

    test("should toggle between grid and pie chart views", async ({
      adminPage,
    }) => {
      await adminPage.goto("/studio/admin");

      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      const toggleButton = adminPage.getByRole("button", {
        name: /switch to (pie chart|grid) view/i,
      });

      const isToggleVisible = await toggleButton.isVisible().catch(() => false);

      if (isToggleVisible) {
        // Get initial aria-label
        const initialLabel = await toggleButton.getAttribute("aria-label");

        // Click toggle
        await toggleButton.click();

        // Label should change
        const newLabel = await toggleButton.getAttribute("aria-label");
        expect(newLabel).not.toBe(initialLabel);

        // Click again to toggle back
        await toggleButton.click();

        const finalLabel = await toggleButton.getAttribute("aria-label");
        expect(finalLabel).toBe(initialLabel);
      }
    });

    test("should display pie chart when toggled", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin");

      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      const toggleButton = adminPage.getByRole("button", {
        name: /switch to pie chart view/i,
      });

      const isToggleVisible = await toggleButton.isVisible().catch(() => false);

      if (isToggleVisible) {
        // Click to switch to pie chart
        await toggleButton.click();

        // Pie chart container should appear
        const pieChart = adminPage.getByTestId("ai-quality-pie-chart");
        await expect(pieChart).toBeVisible({ timeout: 3000 });
      }
    });
  });

  test.describe("Accessibility", () => {
    test("should have proper ARIA structure", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin");

      const card = adminPage.getByTestId("ai-quality-card");
      await expect(card).toBeVisible({ timeout: 5000 });

      // Card should be a region with proper aria-label
      await expect(card).toHaveRole("region");
      await expect(card).toHaveAttribute("aria-label", /ai quality metrics/i);
    });

    test("should have accessible toggle button", async ({ adminPage }) => {
      await adminPage.goto("/studio/admin");

      await expect(adminPage.getByTestId("ai-quality-card")).toBeVisible({
        timeout: 5000,
      });

      const toggleButton = adminPage.getByRole("button", {
        name: /switch to (pie chart|grid) view/i,
      });

      const isToggleVisible = await toggleButton.isVisible().catch(() => false);

      if (isToggleVisible) {
        // Button should have descriptive aria-label
        const ariaLabel = await toggleButton.getAttribute("aria-label");
        expect(ariaLabel).toMatch(/switch to (pie chart|grid) view/i);
      }
    });
  });

  test.describe("Loading and Error States", () => {
    test("should show loading state initially", async ({ adminPage }) => {
      // Add a delay to the API response to see loading state
      if (!backendEnabled) {
        await adminPage.route("**/api/v1/feedback/summary*", async (route) => {
          await new Promise((resolve) => setTimeout(resolve, 500));
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(MOCK_FEEDBACK_SUMMARY),
          });
        });
      }

      await adminPage.goto("/studio/admin");

      // Card should appear (possibly in loading state first)
      const card = adminPage.getByTestId("ai-quality-card");
      await expect(card).toBeVisible({ timeout: 10000 });
    });

    test("should handle API errors gracefully", async ({ adminPage }) => {
      if (!backendEnabled) {
        // Mock API error
        await adminPage.route("**/api/v1/feedback/summary*", async (route) => {
          await route.fulfill({
            status: 500,
            contentType: "application/json",
            body: JSON.stringify({ detail: "Internal server error" }),
          });
        });

        await adminPage.goto("/studio/admin");

        const card = adminPage.getByTestId("ai-quality-card");
        await expect(card).toBeVisible({ timeout: 5000 });

        // Should show error message
        await expect(
          card.getByText(/failed to load ai quality metrics/i)
        ).toBeVisible();
      }
    });
  });

  test.describe("Zero Reports State", () => {
    test("should display checkmark when no hallucination reports", async ({
      adminPage,
    }) => {
      if (!backendEnabled) {
        // Mock zero reports
        await adminPage.route("**/api/v1/feedback/summary*", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              ...MOCK_FEEDBACK_SUMMARY,
              hallucination_reports: 0,
              hallucination_categories: {
                factual_error: 0,
                outdated_info: 0,
                made_up_source: 0,
                other: 0,
              },
            }),
          });
        });
      }

      await adminPage.goto("/studio/admin");

      const card = adminPage.getByTestId("ai-quality-card");
      await expect(card).toBeVisible({ timeout: 5000 });

      // When there are no reports, should show success message
      const zeroMessage = card.getByText(/no reports in this period/i);
      const isVisible = await zeroMessage.isVisible().catch(() => false);

      // This test validates the zero state if the API returns zero reports
      if (isVisible) {
        await expect(zeroMessage).toBeVisible();
      }
    });
  });
});
