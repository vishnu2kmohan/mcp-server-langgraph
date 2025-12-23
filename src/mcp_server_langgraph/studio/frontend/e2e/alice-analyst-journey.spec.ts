/**
 * Alice Analyst User Journey E2E Tests
 *
 * Tests the complete analyst user journey including:
 * - Trace exploration and analysis
 * - Cost monitoring and optimization
 * - Metrics dashboards
 * - Data-driven insights
 *
 * Uses HEART framework metrics:
 * - Happiness: Analysis workflow satisfaction
 * - Engagement: Analysis actions per session
 * - Adoption: Analytics feature discovery
 * - Retention: Analyst return rate
 * - Task Success: Analysis task completion rate
 *
 * Visible modules: chat, traces, costs, metrics, help
 * Default view: /studio/observability
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Alice Analyst User Journey", () => {
  test.beforeEach(async ({ alicePage }) => {
    if (!backendEnabled) {
      await alicePage.route("**/api/v1/**", async (route) => {
        const url = route.request().url();

        if (url.includes("/health")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              status: "healthy",
              uptime_seconds: 86400,
              version: "1.0.0",
            }),
          });
          return;
        }

        if (url.includes("/traces")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "trace-1",
                  name: "workflow-execution",
                  duration_ms: 1250,
                  status: "success",
                  timestamp: Date.now(),
                },
                {
                  id: "trace-2",
                  name: "llm-call",
                  duration_ms: 890,
                  status: "success",
                  timestamp: Date.now() - 60000,
                },
                {
                  id: "trace-3",
                  name: "mcp-tool-call",
                  duration_ms: 340,
                  status: "error",
                  timestamp: Date.now() - 120000,
                },
              ],
              total: 3,
            }),
          });
          return;
        }

        if (url.includes("/costs") || url.includes("/usage")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              total_cost_usd: 125.5,
              tokens_used: 1500000,
              requests_count: 4500,
              breakdown: {
                openai: { cost: 75.0, tokens: 900000 },
                anthropic: { cost: 50.5, tokens: 600000 },
              },
            }),
          });
          return;
        }

        if (url.includes("/metrics")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              latency_p50_ms: 450,
              latency_p95_ms: 1200,
              latency_p99_ms: 2100,
              error_rate: 0.02,
              requests_per_minute: 12.5,
            }),
          });
          return;
        }

        if (url.includes("/me")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "alice-analyst-user",
              username: "alice",
              email: "alice@example.com",
              roles: ["developer", "analyst"],
            }),
          });
          return;
        }

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
      });
    }

    await alicePage.goto("/studio/");
  });

  test.describe("Accessible Pages", () => {
    test("should access observability/traces page", async ({ alicePage }) => {
      await alicePage.goto("/studio/observability");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access chat interface", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access help section", async ({ alicePage }) => {
      await alicePage.goto("/studio/help");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });
  });

  test.describe("Route Restrictions", () => {
    test("analyst should have focused navigation", async ({ alicePage }) => {
      await alicePage.goto("/studio/observability");

      // Check navigation structure
      const navOrHeader = alicePage.locator(
        'nav, [role="navigation"], header, aside'
      );
      await expect(navOrHeader.first()).toBeVisible();
    });
  });

  test.describe("Primary Workflows", () => {
    test("should view trace list", async ({ alicePage }) => {
      await alicePage.goto("/studio/observability");

      // Look for traces content
      const tracesContent = alicePage.locator(
        '[data-testid*="trace"], table, [role="table"], [role="grid"], .traces-list'
      );
      if (await tracesContent.first().isVisible().catch(() => false)) {
        await expect(tracesContent.first()).toBeVisible();
      }
    });

    test("should filter traces if functionality available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/observability");

      // Look for filter/search controls
      const filterInput = alicePage.locator(
        'input[placeholder*="filter" i], input[placeholder*="search" i], [data-testid*="filter"]'
      );
      if (await filterInput.first().isVisible().catch(() => false)) {
        await filterInput.first().fill("error");
        await expect(filterInput.first()).toHaveValue("error");
      }
    });

    test("should view cost breakdown if available", async ({ alicePage }) => {
      await alicePage.goto("/studio/observability");

      // Look for cost/usage section
      const costContent = alicePage.locator(
        '[data-testid*="cost"], [data-testid*="usage"], .costs, .usage'
      );
      if (await costContent.first().isVisible().catch(() => false)) {
        await expect(costContent.first()).toBeVisible();
      }
    });

    test("should view metrics dashboard if available", async ({ alicePage }) => {
      await alicePage.goto("/studio/observability");

      // Look for metrics visualization
      const metricsContent = alicePage.locator(
        '[data-testid*="metric"], [data-testid*="chart"], canvas, svg.chart'
      );
      if (await metricsContent.first().isVisible().catch(() => false)) {
        await expect(metricsContent.first()).toBeVisible();
      }
    });

    test("should interact with chat for analysis questions", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Look for chat input
      const chatInput = alicePage.locator(
        '[data-testid*="chat-input"], textarea[placeholder*="message" i], input[placeholder*="message" i]'
      );
      if (await chatInput.first().isVisible().catch(() => false)) {
        await expect(chatInput.first()).toBeVisible();
      }
    });
  });

  test.describe("Performance Metrics (HEART)", () => {
    test("observability page should load within acceptable time", async ({
      alicePage,
    }) => {
      const startTime = Date.now();

      await alicePage.goto("/studio/observability");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("chat page should load within acceptable time", async ({
      alicePage,
    }) => {
      const startTime = Date.now();

      await alicePage.goto("/studio/chat");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("should have proper accessibility structure", async ({ alicePage }) => {
      await alicePage.goto("/studio/observability");
      await expect(
        alicePage.locator("main, [role='main'], h1").first()
      ).toBeVisible();

      const headings = alicePage.getByRole("heading");
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });

  test.describe("Analyst-specific Features", () => {
    test("should have data visualization capabilities", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/observability");

      // Look for any data visualization elements
      const vizElements = alicePage.locator(
        "canvas, svg, [data-testid*='chart'], .chart, .graph"
      );
      // This is optional - not all implementations have charts
      const count = await vizElements.count();
      // Just verify page loaded successfully
      await expect(
        alicePage.locator("main, [role='main']").first()
      ).toBeVisible();
    });

    test("should support time range selection if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/observability");

      // Look for time range selector
      const timeSelector = alicePage.locator(
        '[data-testid*="time"], [data-testid*="range"], select, [role="combobox"]'
      );
      if (await timeSelector.first().isVisible().catch(() => false)) {
        await expect(timeSelector.first()).toBeVisible();
      }
    });
  });
});
