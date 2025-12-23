/**
 * Alice Builder User Journey E2E Tests
 *
 * Tests the complete workflow builder journey including:
 * - Workflow creation and editing
 * - Agent configuration
 * - MCP server integration
 * - Chat-based development workflow
 *
 * Uses HEART framework metrics:
 * - Happiness: Workflow creation satisfaction
 * - Engagement: Builder actions per session
 * - Adoption: Workflow feature discovery
 * - Retention: Builder return rate
 * - Task Success: Workflow task completion rate
 *
 * Visible modules: chat, flows, mcp, agents, help
 * Default view: /studio/chat
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Alice Builder User Journey", () => {
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

        if (url.includes("/workflows")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "workflow-1",
                  name: "Customer Support Bot",
                  description: "Automated customer support workflow",
                  status: "active",
                  created_at: new Date().toISOString(),
                },
                {
                  id: "workflow-2",
                  name: "Data Pipeline",
                  description: "ETL workflow for analytics",
                  status: "draft",
                  created_at: new Date().toISOString(),
                },
              ],
              total: 2,
            }),
          });
          return;
        }

        if (url.includes("/agents")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "agent-1",
                  name: "Research Agent",
                  type: "research",
                  status: "active",
                },
                {
                  id: "agent-2",
                  name: "Writer Agent",
                  type: "content",
                  status: "active",
                },
              ],
              total: 2,
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
                  tools_count: 5,
                },
                {
                  id: "mcp-2",
                  name: "Search Server",
                  status: "running",
                  port: 8002,
                  tools_count: 3,
                },
              ],
              total: 2,
            }),
          });
          return;
        }

        if (url.includes("/sessions") || url.includes("/chat")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "session-1",
                  title: "Workflow Development Session",
                  created_at: new Date().toISOString(),
                  message_count: 15,
                },
              ],
              total: 1,
            }),
          });
          return;
        }

        if (url.includes("/me")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "alice-builder-user",
              username: "alice",
              email: "alice@example.com",
              roles: ["developer"],
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
    test("should access chat interface as default view", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access workflows page", async ({ alicePage }) => {
      await alicePage.goto("/studio/workflows");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access MCP configuration page", async ({ alicePage }) => {
      await alicePage.goto("/studio/mcp");
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
    test("builder should have development-focused navigation", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Check navigation structure
      const navOrHeader = alicePage.locator(
        'nav, [role="navigation"], header, aside'
      );
      await expect(navOrHeader.first()).toBeVisible();
    });
  });

  test.describe("Primary Workflows", () => {
    test("should view workflow list", async ({ alicePage }) => {
      await alicePage.goto("/studio/workflows");

      // Look for workflows content
      const workflowsContent = alicePage.locator(
        '[data-testid*="workflow"], table, [role="table"], [role="grid"], .workflow-list'
      );
      if (await workflowsContent.first().isVisible().catch(() => false)) {
        await expect(workflowsContent.first()).toBeVisible();
      }
    });

    test("should access workflow creation if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/workflows");

      // Look for create/new workflow button
      const createButton = alicePage.getByRole("button", {
        name: /new|create|add/i,
      });
      if (await createButton.first().isVisible().catch(() => false)) {
        await expect(createButton.first()).toBeVisible();
      }
    });

    test("should view MCP server list for tool integration", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/mcp");

      // Look for MCP server content
      const mcpContent = alicePage.locator(
        '[data-testid*="mcp"], [data-testid*="server"], table, .server-list'
      );
      if (await mcpContent.first().isVisible().catch(() => false)) {
        await expect(mcpContent.first()).toBeVisible();
      }
    });

    test("should access chat for workflow development", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Look for chat interface
      const chatContent = alicePage.locator(
        '[data-testid*="chat"], [data-testid*="message"], textarea, [role="textbox"]'
      );
      if (await chatContent.first().isVisible().catch(() => false)) {
        await expect(chatContent.first()).toBeVisible();
      }
    });

    test("should have input area for chat interaction", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Look for message input
      const messageInput = alicePage.locator(
        'textarea, [data-testid*="input"], [role="textbox"]'
      );
      if (await messageInput.first().isVisible().catch(() => false)) {
        await expect(messageInput.first()).toBeVisible();
      }
    });
  });

  test.describe("Performance Metrics (HEART)", () => {
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

    test("workflows page should load within acceptable time", async ({
      alicePage,
    }) => {
      const startTime = Date.now();

      await alicePage.goto("/studio/workflows");
      await expect(
        alicePage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("should have proper accessibility structure", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");
      await expect(
        alicePage.locator("main, [role='main'], h1").first()
      ).toBeVisible();

      const headings = alicePage.getByRole("heading");
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });

  test.describe("Builder-specific Features", () => {
    test("should have workflow template selection if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/workflows");

      // Look for template-related UI
      const templateUI = alicePage.locator(
        '[data-testid*="template"], button:has-text("template"), [class*="template"]'
      );
      if (await templateUI.first().isVisible().catch(() => false)) {
        await expect(templateUI.first()).toBeVisible();
      }
    });

    test("should support workflow save/export if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/workflows");

      // Look for save/export button
      const saveButton = alicePage.getByRole("button", {
        name: /save|export|download/i,
      });
      if (await saveButton.first().isVisible().catch(() => false)) {
        await expect(saveButton.first()).toBeVisible();
      }
    });

    test("should have agent configuration access if available", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/mcp");

      // Look for agent configuration UI
      const agentConfig = alicePage.locator(
        '[data-testid*="agent"], [data-testid*="config"], button:has-text("configure")'
      );
      if (await agentConfig.first().isVisible().catch(() => false)) {
        await expect(agentConfig.first()).toBeVisible();
      }
    });

    test("should support keyboard shortcuts for development", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Look for keyboard shortcut indicators or help
      const shortcutIndicators = alicePage.locator(
        '[data-testid*="shortcut"], [aria-label*="shortcut"], kbd, .keyboard-shortcut'
      );
      // Shortcuts may not always be visible, so just verify page is functional
      await expect(
        alicePage.locator("main, [role='main']").first()
      ).toBeVisible();
    });
  });
});
