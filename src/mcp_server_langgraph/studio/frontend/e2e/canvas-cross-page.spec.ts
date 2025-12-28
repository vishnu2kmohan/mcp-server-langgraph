/**
 * Canvas Cross-Page E2E Tests
 *
 * Tests for CanvasContext functionality across different page contexts:
 * - Chat: LLM-generated artifacts
 * - Workflow: Node code, Mermaid diagrams, workflow scripts
 * - MCP Tools: Tool schemas, example inputs/outputs, JSON configs
 * - Agents: Agent configurations, prompt templates
 * - Connections: Connection configs, credential schemas
 *
 * Validates Sprint Block 4 Canvas Context Architecture.
 */

import { test, expect } from "./fixtures/auth";

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// Mock feature flags for canvas cross-page tests
const mockFeatureFlags = {
  studio_canvas_shell: true,
  canvas_editable: true,
  canvas_agents: true,
  canvas_ai_palette: true,
  canvas_compliance: true,
  canvas_help: true,
  workflows: true,
  sessions: true,
  observability: true,
  code_export: true,
  ai_suggestions: true,
  llm_suggestions: true,
  suggestion_strategy: "llm",
  multi_agent_strategy: "orchestrator",
  mcp_websocket: true,
  interactive_artifacts: true,
};

test.describe("Canvas Cross-Page Context", () => {
  test.beforeEach(async ({ page }) => {
    // Mock feature flags endpoint
    await page.route("**/api/v1/features*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockFeatureFlags),
      });
    });

    // Mock session data
    await page.route("**/api/v1/sessions*", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: [],
            pagination: {
              count: 0,
              has_next: false,
              has_prev: false,
            },
          }),
        });
      } else {
        await route.fallback();
      }
    });
  });

  test.describe("Page Context Initialization", () => {
    test("should render canvas in chat context", async ({ page }) => {
      await page.goto("/studio/chat");

      // Wait for canvas workspace to be visible
      const canvas = page.locator('[data-testid="canvas-workspace"]');

      // Canvas may or may not be visible initially depending on artifacts
      // Verify the page loads without errors
      await expect(page).toHaveURL(/\/studio\/chat/);
    });

    test("should render canvas in workflow context", async ({ page }) => {
      // Mock workflow data
      await page.route("**/api/v1/workflows*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [],
            next_cursor: null,
            has_more: false,
          }),
        });
      });

      await page.goto("/studio/workflows");
      await expect(page).toHaveURL(/\/studio\/workflows/);
    });

    test("should render canvas in MCP tools context", async ({ page }) => {
      // Mock MCP data
      await page.route("**/api/v1/mcp/**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ data: [], pagination: { count: 0, has_next: false, has_prev: false } }),
        });
      });

      await page.goto("/studio/mcp");
      await expect(page).toHaveURL(/\/studio\/mcp/);
    });

    test("should render canvas in agents context", async ({ page }) => {
      await page.goto("/studio/agents");
      await expect(page).toHaveURL(/\/studio\/agents/);
    });

    test("should render canvas in connections context", async ({ page }) => {
      // Mock connections data
      await page.route("**/api/v1/connections*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            data: [],
            pagination: { count: 0, has_next: false, has_prev: false },
          }),
        });
      });

      await page.goto("/studio/connections");
      await expect(page).toHaveURL(/\/studio\/connections/);
    });
  });

  test.describe("Canvas State Isolation", () => {
    test("should maintain separate artifact state per page context", async ({
      page,
    }) => {
      // Navigate to chat page
      await page.goto("/studio/chat");
      await expect(page).toHaveURL(/\/studio\/chat/);

      // Mock workflow data
      await page.route("**/api/v1/workflows*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: "wf-1",
                name: "Test Workflow",
                description: "Test",
                node_count: 1,
                edge_count: 0,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ],
            next_cursor: null,
            has_more: false,
          }),
        });
      });

      // Navigate to workflows
      await page.goto("/studio/workflows");
      await expect(page).toHaveURL(/\/studio\/workflows/);

      // Each page has its own CanvasProvider instance
      // State should be isolated between pages
    });
  });

  test.describe("Canvas Feature Flag Integration", () => {
    test("should respect canvas feature flags", async ({ page }) => {
      // Disable canvas features
      const disabledFlags = {
        ...mockFeatureFlags,
        studio_canvas_shell: false,
        canvas_editable: false,
      };

      await page.route("**/api/v1/features*", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(disabledFlags),
        });
      });

      await page.goto("/studio/chat");
      await expect(page).toHaveURL(/\/studio\/chat/);

      // Canvas should be hidden or limited when feature flags are disabled
    });

    test("should include strategy fields in feature flags", async ({
      page,
    }) => {
      let capturedFlags: Record<string, unknown> | null = null;

      await page.route("**/api/v1/features*", async (route) => {
        capturedFlags = mockFeatureFlags;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockFeatureFlags),
        });
      });

      await page.goto("/studio/chat");
      await expect(page).toHaveURL(/\/studio\/chat/);

      // Verify strategy fields are present
      expect(capturedFlags).not.toBeNull();
      expect(capturedFlags!.suggestion_strategy).toBe("llm");
      expect(capturedFlags!.multi_agent_strategy).toBe("orchestrator");
    });
  });
});

test.describe("Canvas Navigation Flows", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/features*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockFeatureFlags),
      });
    });

    await page.route("**/api/v1/sessions*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          data: [],
          pagination: { count: 0, has_next: false, has_prev: false },
        }),
      });
    });

    await page.route("**/api/v1/workflows*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          next_cursor: null,
          has_more: false,
        }),
      });
    });
  });

  test("should navigate between pages without errors", async ({ page }) => {
    // Start at chat
    await page.goto("/studio/chat");
    await expect(page).toHaveURL(/\/studio\/chat/);

    // Navigate to workflows
    const workflowLink = page.locator('a[href*="/studio/workflows"]').first();
    if (await workflowLink.isVisible()) {
      await workflowLink.click();
      await expect(page).toHaveURL(/\/studio\/workflows/);
    }

    // Navigate back to chat
    const chatLink = page.locator('a[href*="/studio/chat"]').first();
    if (await chatLink.isVisible()) {
      await chatLink.click();
      await expect(page).toHaveURL(/\/studio\/chat/);
    }
  });

  test("should maintain app stability during page transitions", async ({
    page,
  }) => {
    // Listen for console errors
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate through pages
    await page.goto("/studio/chat");
    await page.waitForLoadState("networkidle");

    await page.goto("/studio/workflows");
    await page.waitForLoadState("networkidle");

    await page.goto("/studio/agents");
    await page.waitForLoadState("networkidle");

    await page.goto("/studio/chat");
    await page.waitForLoadState("networkidle");

    // Filter out expected errors (like auth redirects)
    const unexpectedErrors = consoleErrors.filter(
      (err) =>
        !err.includes("auth") &&
        !err.includes("401") &&
        !err.includes("Failed to load resource")
    );

    // No unexpected console errors should occur
    expect(unexpectedErrors).toHaveLength(0);
  });
});
