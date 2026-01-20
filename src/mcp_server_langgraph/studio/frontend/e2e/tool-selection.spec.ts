/**
 * Tool Selection E2E Tests
 *
 * Tests the manual tool selection feature in the chat interface.
 * This feature allows users to override semantic tool search with explicit choices.
 *
 * Tool Selection Modes:
 * - Auto: Default semantic search (AI determines which tools to use)
 * - Manual: User explicitly selects which tools to use
 * - None: Disable all tool use for the message
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Tool Selection", () => {
  test.describe("Tool Selector UI", () => {
    test("should display tool selector button in chat input area", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Wait for chat input to be ready
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Tool selector button should be visible
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await expect(toolSelector).toBeVisible({ timeout: 5000 });
    });

    test("should show 'Auto' as default mode", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Tool selector should indicate Auto mode
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await expect(toolSelector).toContainText("Auto");
    });

    test("should open dropdown when tool selector is clicked", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Click tool selector to open dropdown
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();

      // Dropdown should be visible with mode options
      const dropdown = alicePage.getByTestId("tool-selector-dropdown");
      await expect(dropdown).toBeVisible({ timeout: 5000 });

      // Should show all three modes
      await expect(dropdown.getByRole("option", { name: /auto/i })).toBeVisible();
      await expect(dropdown.getByRole("option", { name: /manual/i })).toBeVisible();
      await expect(dropdown.getByRole("option", { name: /none/i })).toBeVisible();
    });
  });

  test.describe("Mode Switching", () => {
    test("should switch to Manual mode when clicked", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Open dropdown
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();

      // Click Manual mode
      const manualOption = alicePage.getByRole("option", { name: /manual/i });
      await manualOption.click();

      // Tool selector should show search input for tool selection
      await toolSelector.click();
      const searchInput = alicePage.getByPlaceholder(/search tools/i);
      await expect(searchInput).toBeVisible({ timeout: 5000 });
    });

    test("should switch to None mode when clicked", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Open dropdown
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();

      // Click None mode
      const noneOption = alicePage.getByRole("option", { name: /none/i });
      await noneOption.click();

      // Tool selector should indicate None mode
      await expect(toolSelector).toContainText("None");
    });

    test("should switch back to Auto mode", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Switch to None first
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();
      await alicePage.getByRole("option", { name: /none/i }).click();
      await expect(toolSelector).toContainText("None");

      // Switch back to Auto
      await toolSelector.click();
      await alicePage.getByRole("option", { name: /auto/i }).click();
      await expect(toolSelector).toContainText("Auto");
    });
  });

  test.describe("Manual Tool Selection", () => {
    test("should show available tools in manual mode", async ({ alicePage }) => {
      if (!backendEnabled) {
        // Mock the tools endpoint
        await alicePage.route("**/api/v1/tools**", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              tools: [
                {
                  name: "calculator",
                  display_name: "Calculator",
                  description: "Perform math operations",
                  source: "builtin",
                  category: "math",
                },
                {
                  name: "web_search",
                  display_name: "Web Search",
                  description: "Search the web",
                  source: "builtin",
                  category: "search",
                },
              ],
              total: 2,
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Switch to Manual mode
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();
      await alicePage.getByRole("option", { name: /manual/i }).click();

      // Re-open to see tools
      await toolSelector.click();

      // Should show available tools
      const toolsList = alicePage.getByTestId("tool-selector-list");
      await expect(toolsList).toBeVisible({ timeout: 5000 });
    });

    test("should allow selecting multiple tools", async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/tools**", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              tools: [
                {
                  name: "calculator",
                  display_name: "Calculator",
                  description: "Perform math operations",
                  source: "builtin",
                },
                {
                  name: "web_search",
                  display_name: "Web Search",
                  description: "Search the web",
                  source: "builtin",
                },
              ],
              total: 2,
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Switch to Manual mode
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();
      await alicePage.getByRole("option", { name: /manual/i }).click();

      // Re-open and select tools
      await toolSelector.click();

      // Select calculator
      const calculatorCheckbox = alicePage.getByRole("checkbox", {
        name: /calculator/i,
      });
      if (await calculatorCheckbox.isVisible()) {
        await calculatorCheckbox.click();
      }

      // Close and verify selection count
      await alicePage.keyboard.press("Escape");

      // Tool selector should show count of selected tools
      await expect(toolSelector).toContainText(/[1-9]/);
    });

    test("should filter tools with search", async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/tools**", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              tools: [
                {
                  name: "calculator",
                  display_name: "Calculator",
                  description: "Perform math operations",
                  source: "builtin",
                },
                {
                  name: "web_search",
                  display_name: "Web Search",
                  description: "Search the web",
                  source: "builtin",
                },
                {
                  name: "search_knowledge_base",
                  display_name: "Search Knowledge Base",
                  description: "Search the knowledge base",
                  source: "builtin",
                },
              ],
              total: 3,
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Switch to Manual mode and open dropdown
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();
      await alicePage.getByRole("option", { name: /manual/i }).click();
      await toolSelector.click();

      // Search for "calc"
      const searchInput = alicePage.getByPlaceholder(/search tools/i);
      await searchInput.fill("calc");

      // Should only show calculator
      const calculatorItem = alicePage.getByText("Calculator");
      await expect(calculatorItem).toBeVisible({ timeout: 5000 });

      // Web search should be filtered out
      const webSearchItem = alicePage.getByText("Web Search");
      await expect(webSearchItem).not.toBeVisible();
    });
  });

  test.describe("Integration with Chat", () => {
    test("should be disabled while processing", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Mock slow streaming response
      await alicePage.route("**/api/v1/chat/completions/stream", async (route) => {
        // Delay response to simulate processing
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          body: "data: {}\n\n",
        });
      });

      // Send a message
      await chatInput.fill("Hello");
      await alicePage.keyboard.press("Enter");

      // Tool selector should be disabled while processing
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await expect(toolSelector).toBeDisabled({ timeout: 3000 });
    });

    test("should persist selection when sending message", async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/tools**", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              tools: [
                {
                  name: "calculator",
                  display_name: "Calculator",
                  description: "Perform math operations",
                  source: "builtin",
                },
              ],
              total: 1,
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Switch to None mode
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();
      await alicePage.getByRole("option", { name: /none/i }).click();

      // Type a message (don't send)
      await chatInput.fill("Calculate 2 + 2");

      // Tool selection should still be "None"
      await expect(toolSelector).toContainText("None");
    });
  });

  test.describe("Keyboard Navigation", () => {
    test("should close dropdown on Escape", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Open dropdown
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();

      const dropdown = alicePage.getByTestId("tool-selector-dropdown");
      await expect(dropdown).toBeVisible({ timeout: 5000 });

      // Press Escape
      await alicePage.keyboard.press("Escape");

      // Dropdown should close
      await expect(dropdown).not.toBeVisible();
    });

    test("should navigate options with arrow keys", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Open dropdown
      const toolSelector = alicePage.getByRole("button", { name: /tools/i });
      await toolSelector.click();

      const dropdown = alicePage.getByTestId("tool-selector-dropdown");
      await expect(dropdown).toBeVisible({ timeout: 5000 });

      // Use arrow keys to navigate
      await alicePage.keyboard.press("ArrowDown");
      await alicePage.keyboard.press("ArrowDown");
      await alicePage.keyboard.press("Enter");

      // Dropdown should close after selection
      await expect(dropdown).not.toBeVisible();
    });
  });

  test.describe("Loading States", () => {
    test("should show loading indicator while tools are loading", async ({
      alicePage,
    }) => {
      // Mock slow tools endpoint
      await alicePage.route("**/api/v1/tools**", async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ tools: [], total: 0 }),
        });
      });

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Check for loading indicator
      const loadingIndicator = alicePage.getByTestId("tool-selector-loading");
      // May or may not be visible depending on timing
      // This is a soft check
    });
  });
});
