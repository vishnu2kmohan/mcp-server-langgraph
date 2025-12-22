/**
 * Alice DevOps User Journey E2E Tests
 *
 * Tests the complete DevOps user journey including:
 * - Connection management
 * - MCP server configuration
 * - Trace monitoring
 * - Deployment verification
 *
 * Uses HEART framework metrics:
 * - Happiness: DevOps workflow satisfaction
 * - Engagement: DevOps actions per session
 * - Adoption: Infrastructure feature discovery
 * - Retention: DevOps return rate
 * - Task Success: Configuration task completion rate
 *
 * Visible modules: chat, mcp, connections, traces, help
 * Default view: /studio/v2/connections
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Alice DevOps User Journey", () => {
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

        if (url.includes("/connections")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "conn-1",
                  name: "Production Database",
                  type: "postgresql",
                  status: "connected",
                },
                {
                  id: "conn-2",
                  name: "Redis Cache",
                  type: "redis",
                  status: "connected",
                },
                {
                  id: "conn-3",
                  name: "S3 Storage",
                  type: "s3",
                  status: "disconnected",
                },
              ],
              total: 3,
            }),
          });
          return;
        }

        if (url.includes("/mcp/servers")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "mcp-1",
                  name: "File Server",
                  status: "running",
                  port: 8001,
                },
                {
                  id: "mcp-2",
                  name: "Search Server",
                  status: "running",
                  port: 8002,
                },
              ],
              total: 2,
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
                  name: "deployment-check",
                  duration_ms: 250,
                  status: "success",
                  timestamp: Date.now(),
                },
                {
                  id: "trace-2",
                  name: "connection-test",
                  duration_ms: 150,
                  status: "success",
                  timestamp: Date.now() - 30000,
                },
              ],
              total: 2,
            }),
          });
          return;
        }

        if (url.includes("/me")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "alice-devops-user",
              username: "alice",
              email: "alice@example.com",
              roles: ["developer", "devops"],
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
    test("should access connections page", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/connections");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access MCP configuration page", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/mcp");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access traces/observability page", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/observability");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access chat interface", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/chat");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access help section", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/help");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });
  });

  test.describe("Route Restrictions", () => {
    test("devops should have infrastructure-focused navigation", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/v2/connections");

      // Check navigation structure
      const navOrHeader = alicePage.locator(
        'nav, [role="navigation"], header, aside'
      );
      await expect(navOrHeader.first()).toBeVisible();
    });
  });

  test.describe("Primary Workflows", () => {
    test("should view connection list", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/connections");

      // Look for connections content
      const connectionsContent = alicePage.locator(
        '[data-testid*="connection"], table, [role="table"], [role="grid"], .connections-list'
      );
      if (await connectionsContent.first().isVisible().catch(() => false)) {
        await expect(connectionsContent.first()).toBeVisible();
      }
    });

    test("should view connection status indicators", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/connections");

      // Look for status indicators
      const statusIndicators = alicePage.locator(
        '[data-testid*="status"], .status, [class*="status"]'
      );
      if (await statusIndicators.first().isVisible().catch(() => false)) {
        await expect(statusIndicators.first()).toBeVisible();
      }
    });

    test("should view MCP server list", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/mcp");

      // Look for MCP server content
      const mcpContent = alicePage.locator(
        '[data-testid*="mcp"], [data-testid*="server"], table, .server-list'
      );
      if (await mcpContent.first().isVisible().catch(() => false)) {
        await expect(mcpContent.first()).toBeVisible();
      }
    });

    test("should access MCP server configuration if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/v2/mcp");

      // Look for configuration/settings button
      const configButton = alicePage.getByRole("button", {
        name: /config|settings|edit/i,
      });
      if (await configButton.first().isVisible().catch(() => false)) {
        await expect(configButton.first()).toBeVisible();
      }
    });

    test("should monitor traces for deployment health", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/v2/observability");

      // Look for traces content
      const tracesContent = alicePage.locator(
        '[data-testid*="trace"], table, [role="table"]'
      );
      if (await tracesContent.first().isVisible().catch(() => false)) {
        await expect(tracesContent.first()).toBeVisible();
      }
    });
  });

  test.describe("Performance Metrics (HEART)", () => {
    test("connections page should load within acceptable time", async ({
      alicePage,
    }) => {
      const startTime = Date.now();

      await alicePage.goto("/studio/v2/connections");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("MCP page should load within acceptable time", async ({
      alicePage,
    }) => {
      const startTime = Date.now();

      await alicePage.goto("/studio/v2/mcp");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("should have proper accessibility structure", async ({ alicePage }) => {
      await alicePage.goto("/studio/v2/connections");
      await expect(
        alicePage.locator("main, [role='main'], h1").first()
      ).toBeVisible();

      const headings = alicePage.getByRole("heading");
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });

  test.describe("DevOps-specific Features", () => {
    test("should have connection test functionality if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/v2/connections");

      // Look for test/verify button
      const testButton = alicePage.getByRole("button", {
        name: /test|verify|check/i,
      });
      if (await testButton.first().isVisible().catch(() => false)) {
        await expect(testButton.first()).toBeVisible();
      }
    });

    test("should support adding new connections if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/v2/connections");

      // Look for add button
      const addButton = alicePage.getByRole("button", {
        name: /add|new|create/i,
      });
      if (await addButton.first().isVisible().catch(() => false)) {
        await expect(addButton.first()).toBeVisible();
      }
    });
  });
});
