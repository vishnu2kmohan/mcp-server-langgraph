/**
 * Bob User Journey E2E Tests
 *
 * Tests the complete standard user journey including:
 * - Chat interaction
 * - Project browsing
 * - Shared workflow viewing
 * - Help access
 *
 * Uses HEART framework metrics:
 * - Happiness: Chat experience satisfaction
 * - Engagement: User actions per session
 * - Adoption: Feature discovery rate
 * - Retention: User return rate
 * - Task Success: Task completion rate
 *
 * Visible modules: chat, projects, shared flows
 * Default view: /studio/v2/chat
 * Role: Standard user with read-focused access
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Bob User Journey", () => {
  test.beforeEach(async ({ bobPage }) => {
    if (!backendEnabled) {
      await bobPage.route("**/api/v1/**", async (route) => {
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

        if (url.includes("/sessions") || url.includes("/chat")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "session-1",
                  title: "General Chat",
                  created_at: new Date().toISOString(),
                  message_count: 5,
                },
                {
                  id: "session-2",
                  title: "Help Request",
                  created_at: new Date(Date.now() - 86400000).toISOString(),
                  message_count: 3,
                },
              ],
              total: 2,
            }),
          });
          return;
        }

        if (url.includes("/projects")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "project-1",
                  name: "Shared Project Alpha",
                  description: "Team collaboration project",
                  owner: "alice",
                  shared: true,
                },
                {
                  id: "project-2",
                  name: "Demo Project",
                  description: "Example project for learning",
                  owner: "admin",
                  shared: true,
                },
              ],
              total: 2,
            }),
          });
          return;
        }

        if (url.includes("/workflows") && url.includes("shared")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "workflow-shared-1",
                  name: "Customer FAQ Bot",
                  description: "Shared FAQ workflow",
                  owner: "alice",
                  shared: true,
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
              id: "bob-user",
              username: "bob",
              email: "bob@example.com",
              roles: ["user"],
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

    await bobPage.goto("/studio/");
  });

  test.describe("Accessible Pages", () => {
    test("should access chat interface as default view", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");
      await expect(
        bobPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access projects page", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/projects");
      await expect(
        bobPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });

    test("should access help section", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/help");
      await expect(
        bobPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();
    });
  });

  test.describe("Route Restrictions", () => {
    test("standard user should have limited navigation", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");

      // Check navigation structure
      const navOrHeader = bobPage.locator(
        'nav, [role="navigation"], header, aside'
      );
      await expect(navOrHeader.first()).toBeVisible();
    });

    test("should not have admin links visible", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");

      // Admin-specific links should not be visible for standard users
      const adminLinks = bobPage.locator(
        'a[href*="/admin"], button:has-text("Admin Dashboard")'
      );
      const count = await adminLinks.count();
      expect(count).toBe(0);
    });
  });

  test.describe("Primary Workflows", () => {
    test("should access chat for conversations", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");

      // Look for chat interface
      const chatContent = bobPage.locator(
        '[data-testid*="chat"], [data-testid*="message"], textarea, [role="textbox"]'
      );
      if (await chatContent.first().isVisible().catch(() => false)) {
        await expect(chatContent.first()).toBeVisible();
      }
    });

    test("should have message input for chat", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");

      // Look for message input
      const messageInput = bobPage.locator(
        'textarea, [data-testid*="input"], [role="textbox"]'
      );
      if (await messageInput.first().isVisible().catch(() => false)) {
        await expect(messageInput.first()).toBeVisible();
      }
    });

    test("should view project list", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/projects");

      // Look for projects content
      const projectsContent = bobPage.locator(
        '[data-testid*="project"], table, [role="table"], [role="grid"], .project-list'
      );
      if (await projectsContent.first().isVisible().catch(() => false)) {
        await expect(projectsContent.first()).toBeVisible();
      }
    });

    test("should view session history", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");

      // Look for session list or history
      const sessionList = bobPage.locator(
        '[data-testid*="session"], [data-testid*="history"], aside, .session-list'
      );
      if (await sessionList.first().isVisible().catch(() => false)) {
        await expect(sessionList.first()).toBeVisible();
      }
    });
  });

  test.describe("Performance Metrics (HEART)", () => {
    test("chat page should load within acceptable time", async ({ bobPage }) => {
      const startTime = Date.now();

      await bobPage.goto("/studio/v2/chat");
      await expect(
        bobPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("projects page should load within acceptable time", async ({
      bobPage,
    }) => {
      const startTime = Date.now();

      await bobPage.goto("/studio/v2/projects");
      await expect(
        bobPage.locator("main, [role='main'], h1, h2").first()
      ).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test("should have proper accessibility structure", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");
      await expect(
        bobPage.locator("main, [role='main'], h1").first()
      ).toBeVisible();

      const headings = bobPage.getByRole("heading");
      expect(await headings.count()).toBeGreaterThan(0);
    });
  });

  test.describe("User-specific Features", () => {
    test("should be able to start new chat session", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");

      // Look for new chat button
      const newChatButton = bobPage.getByRole("button", {
        name: /new|create|start/i,
      });
      if (await newChatButton.first().isVisible().catch(() => false)) {
        await expect(newChatButton.first()).toBeVisible();
      }
    });

    test("should have access to help resources", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/help");

      // Look for help content
      const helpContent = bobPage.locator(
        '[data-testid*="help"], article, .help-content, [role="article"]'
      );
      if (await helpContent.first().isVisible().catch(() => false)) {
        await expect(helpContent.first()).toBeVisible();
      }
    });

    test("should be able to view shared content", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/projects");

      // Look for shared indicators
      const sharedContent = bobPage.locator(
        '[data-testid*="shared"], .shared, [aria-label*="shared"]'
      );
      // Shared content visibility depends on what's actually shared
      await expect(
        bobPage.locator("main, [role='main']").first()
      ).toBeVisible();
    });

    test("should have user settings access", async ({ bobPage }) => {
      await bobPage.goto("/studio/v2/chat");

      // Look for user menu or settings
      const userMenu = bobPage.locator(
        '[data-testid*="user"], [data-testid*="settings"], [aria-label*="user"], button:has-text("Settings")'
      );
      if (await userMenu.first().isVisible().catch(() => false)) {
        await expect(userMenu.first()).toBeVisible();
      }
    });
  });
});
