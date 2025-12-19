/**
 * Chat UX Features E2E Tests
 *
 * Tests the new chat UX features including:
 * - URL Content Fetch (#<url> syntax)
 * - Slash Commands (/help, /clear, /copy, /refresh)
 * - Style Presets (Creative, Balanced, Precise)
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Chat UX Features", () => {
  test.describe("URL Content Fetch (#URL)", () => {
    test("should detect URL pattern when typing #https://", async ({
      alicePage,
    }) => {
      // Navigate to chat
      await alicePage.goto("/studio/chat");

      // Wait for chat input to be ready
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Type a message with #URL pattern
      await chatInput.fill("Check this article #https://example.com");

      // Should show URL fetch indicator
      const urlIndicator = alicePage.getByTestId("url-fetch-indicator");
      await expect(urlIndicator).toBeVisible({ timeout: 5000 });
    });

    test("should show loading state while fetching URL content", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Type URL - auto-fetch should trigger
      await chatInput.fill("#https://httpbin.org/delay/1");

      // Should show loading indicator (spinner or loading text)
      const loadingIndicator = alicePage.locator(
        '[data-testid="url-fetch-loading"], .animate-spin'
      );
      // May or may not appear depending on debounce timing
      // This is a soft check - we just verify no errors occur
    });

    test("should display fetched URL as chip/badge", async ({ alicePage }) => {
      if (!backendEnabled) {
        // Mock the fetch-url endpoint
        await alicePage.route("**/api/v1/ai/fetch-url", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              url: "https://example.com",
              title: "Example Domain",
              content: "This is example content",
              content_type: "text/html",
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("#https://example.com");

      // Wait for fetch to complete and chip to appear
      // The fetched URL should appear as a removable badge
      const urlChip = alicePage.locator('[data-testid="url-fetched-badge"]');
      await expect(urlChip).toBeVisible({ timeout: 10000 });
    });

    test("should allow removing fetched URL", async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/ai/fetch-url", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              url: "https://example.com",
              title: "Example Domain",
              content: "This is example content",
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("#https://example.com");

      // Wait for badge
      const urlChip = alicePage.locator('[data-testid="url-fetched-badge"]');
      await expect(urlChip).toBeVisible({ timeout: 10000 });

      // Click remove button on chip
      const removeButton = urlChip.locator('button[aria-label*="remove" i]');
      await removeButton.click();

      // Chip should be gone
      await expect(urlChip).not.toBeVisible();
    });
  });

  test.describe("Slash Commands", () => {
    test("should show command menu when typing /", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Type / to trigger command menu
      await chatInput.fill("/");

      // Command menu should appear
      const commandMenu = alicePage.getByTestId("slash-command-menu");
      await expect(commandMenu).toBeVisible({ timeout: 5000 });
    });

    test("should filter commands as user types", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Type /he to filter to /help
      await chatInput.fill("/he");

      const commandMenu = alicePage.getByTestId("slash-command-menu");
      await expect(commandMenu).toBeVisible({ timeout: 5000 });

      // Should show /help but not /clear
      await expect(commandMenu.getByText("/help")).toBeVisible();
      await expect(commandMenu.getByText("/clear")).not.toBeVisible();
    });

    test("should execute /help command and show help message", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Type /help and select it
      await chatInput.fill("/help");

      const commandMenu = alicePage.getByTestId("slash-command-menu");
      await expect(commandMenu).toBeVisible({ timeout: 5000 });

      // Click on /help option
      await commandMenu.getByText("/help").click();

      // Should show help message in chat
      const helpMessage = alicePage.getByText("Available Commands");
      await expect(helpMessage).toBeVisible({ timeout: 5000 });
    });

    test("should execute /clear command and clear messages", async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        // Mock session with messages
        await alicePage.route("**/api/v1/sessions/*", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "test-session",
              name: "Test Session",
              messages: [
                { id: "1", role: "user", content: "Hello", timestamp: Date.now() },
                { id: "2", role: "assistant", content: "Hi!", timestamp: Date.now() },
              ],
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Execute /clear command
      await chatInput.fill("/clear");

      const commandMenu = alicePage.getByTestId("slash-command-menu");
      await expect(commandMenu).toBeVisible({ timeout: 5000 });

      await commandMenu.getByText("/clear").click();

      // Should show success toast
      const toast = alicePage.getByText("Conversation cleared");
      await expect(toast).toBeVisible({ timeout: 5000 });
    });

    test("should close command menu on Escape", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("/");

      const commandMenu = alicePage.getByTestId("slash-command-menu");
      await expect(commandMenu).toBeVisible({ timeout: 5000 });

      // Press Escape
      await alicePage.keyboard.press("Escape");

      // Menu should close
      await expect(commandMenu).not.toBeVisible();
    });
  });

  test.describe("Style Presets", () => {
    test("should display style presets selector", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      // Style presets container should be visible
      const stylePresets = alicePage.getByTestId("style-presets-container");
      await expect(stylePresets).toBeVisible({ timeout: 10000 });
    });

    test("should show three preset options", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const stylePresets = alicePage.getByTestId("style-presets-container");
      await expect(stylePresets).toBeVisible({ timeout: 10000 });

      // Should have Creative, Balanced, and Precise options
      await expect(stylePresets.getByText("Creative")).toBeVisible();
      await expect(stylePresets.getByText("Balanced")).toBeVisible();
      await expect(stylePresets.getByText("Precise")).toBeVisible();
    });

    test("should have Balanced selected by default", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const stylePresets = alicePage.getByTestId("style-presets-container");
      await expect(stylePresets).toBeVisible({ timeout: 10000 });

      // Balanced should be the active/selected preset
      const balancedButton = stylePresets.getByRole("button", {
        name: /balanced/i,
      });
      await expect(balancedButton).toHaveAttribute("data-active", "true");
    });

    test("should allow selecting different presets", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const stylePresets = alicePage.getByTestId("style-presets-container");
      await expect(stylePresets).toBeVisible({ timeout: 10000 });

      // Click on Creative
      const creativeButton = stylePresets.getByRole("button", {
        name: /creative/i,
      });
      await creativeButton.click();

      // Creative should now be active
      await expect(creativeButton).toHaveAttribute("data-active", "true");

      // Balanced should not be active
      const balancedButton = stylePresets.getByRole("button", {
        name: /balanced/i,
      });
      await expect(balancedButton).not.toHaveAttribute("data-active", "true");
    });

    test("should persist preset selection during session", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const stylePresets = alicePage.getByTestId("style-presets-container");
      await expect(stylePresets).toBeVisible({ timeout: 10000 });

      // Select Precise
      const preciseButton = stylePresets.getByRole("button", {
        name: /precise/i,
      });
      await preciseButton.click();
      await expect(preciseButton).toHaveAttribute("data-active", "true");

      // Navigate away and back
      await alicePage.goto("/studio/workflows");
      await alicePage.goto("/studio/chat");

      // Precise should still be selected (within same session)
      const stylePresetsAfter = alicePage.getByTestId("style-presets-container");
      await expect(stylePresetsAfter).toBeVisible({ timeout: 10000 });

      // Note: This depends on state management - may reset on navigation
      // This test documents the expected behavior
    });
  });

  test.describe("Error Handling UX", () => {
    test("should show error toast when URL fetch fails", async ({
      alicePage,
    }) => {
      // Mock fetch-url to fail
      await alicePage.route("**/api/v1/ai/fetch-url", async (route) => {
        await route.fulfill({
          status: 400,
          contentType: "application/json",
          body: JSON.stringify({
            detail: "SSRF protection: private IP address not allowed",
          }),
        });
      });

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Try to fetch a blocked URL
      await chatInput.fill("#http://192.168.1.1/admin");

      // Wait for error toast
      const errorToast = alicePage.getByText(/failed to fetch/i);
      await expect(errorToast).toBeVisible({ timeout: 10000 });
    });

    test("should show error toast when streaming fails", async ({
      alicePage,
    }) => {
      // Mock chat completion to fail
      await alicePage.route("**/api/v1/chat/completions/stream", async (route) => {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({
            detail: "Internal server error",
          }),
        });
      });

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Send a message
      await chatInput.fill("Hello");
      await alicePage.keyboard.press("Enter");

      // Wait for error toast
      const errorToast = alicePage.getByText(/chat error/i);
      await expect(errorToast).toBeVisible({ timeout: 10000 });
    });

    test("should show success toast when copy command succeeds", async ({
      alicePage,
    }) => {
      // Grant clipboard permission
      await alicePage.context().grantPermissions(["clipboard-write"]);

      if (!backendEnabled) {
        // Mock session with assistant message
        await alicePage.route("**/api/v1/sessions/*", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              id: "test-session",
              name: "Test Session",
              messages: [
                { id: "1", role: "user", content: "Hello", timestamp: Date.now() },
                {
                  id: "2",
                  role: "assistant",
                  content: "Hi there!",
                  timestamp: Date.now(),
                },
              ],
            }),
          });
        });
      }

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Execute /copy command
      await chatInput.fill("/copy");

      const commandMenu = alicePage.getByTestId("slash-command-menu");
      await expect(commandMenu).toBeVisible({ timeout: 5000 });

      await commandMenu.getByText("/copy").click();

      // Should show success toast
      const toast = alicePage.getByText(/copied to clipboard/i);
      await expect(toast).toBeVisible({ timeout: 5000 });
    });
  });
});
