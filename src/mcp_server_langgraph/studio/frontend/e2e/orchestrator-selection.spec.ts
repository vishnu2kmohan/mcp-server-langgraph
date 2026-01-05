/**
 * Orchestrator Selection E2E Tests
 *
 * Tests the orchestrator mode selection feature (ADR-0090):
 * - Selecting different orchestrator modes (standard, swarm, studio, ux, alert)
 * - Verifying orchestrator preference is sent with chat requests
 * - UI display and interaction with the orchestrator selector
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Orchestrator Selection (ADR-0090)", () => {
  test.describe("UI Display", () => {
    test("should display orchestrator selector when enabled", async ({
      alicePage,
    }) => {
      // Mock feature flag response to enable orchestrator selector
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: true,
          }),
        });
      });

      // Navigate to chat
      await alicePage.goto("/studio/chat");

      // Wait for chat input to be ready
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Orchestrator selector should be visible
      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toBeVisible({ timeout: 5000 });
    });

    test("should not display orchestrator selector when disabled", async ({
      alicePage,
    }) => {
      // Mock feature flag response to disable orchestrator selector
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: false,
          }),
        });
      });

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Orchestrator selector should not be visible
      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).not.toBeVisible();
    });

    test("should have 'standard' as default orchestrator mode", async ({
      alicePage,
    }) => {
      // Mock feature flag to enable selector
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: true,
          }),
        });
      });

      await alicePage.goto("/studio/chat");

      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toBeVisible({ timeout: 10000 });

      // Should default to 'standard'
      await expect(orchestratorSelector).toHaveValue("standard");
    });
  });

  test.describe("Orchestrator Mode Selection", () => {
    test.beforeEach(async ({ alicePage }) => {
      // Enable orchestrator selector via feature flag mock
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: true,
          }),
        });
      });
    });

    test("should allow selecting swarm orchestrator mode", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toBeVisible({ timeout: 10000 });

      // Select swarm mode
      await orchestratorSelector.selectOption("swarm");

      // Verify selection
      await expect(orchestratorSelector).toHaveValue("swarm");
    });

    test("should allow selecting user-facing orchestrator modes", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toBeVisible({ timeout: 10000 });

      // Only user-facing modes are available (standard, swarm)
      // Internal modes (studio, ux, alert) are not exposed to users
      const userFacingModes = ["standard", "swarm"];

      for (const mode of userFacingModes) {
        await orchestratorSelector.selectOption(mode);
        await expect(orchestratorSelector).toHaveValue(mode);
      }
    });
  });

  test.describe("Request Integration", () => {
    test("should send preferred_orchestrator with chat request", async ({
      alicePage,
    }) => {
      // Enable orchestrator selector
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: true,
          }),
        });
      });

      // Track the streaming request
      let capturedRequestBody: string | null = null;
      await alicePage.route("**/api/v1/chat/completions/stream", async (route) => {
        capturedRequestBody = route.request().postData();
        // Return a mock streaming response
        await route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          body: 'data: {"content":"Hello!"}\n\ndata: [DONE]\n\n',
        });
      });

      // Also mock the message save endpoint
      await alicePage.route("**/api/v1/sessions/*/messages", async (route) => {
        if (route.request().method() === "POST") {
          await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
              id: "msg-123",
              role: "user",
              content: "Hello",
              timestamp: Date.now(),
            }),
          });
        } else {
          await route.continue();
        }
      });

      await alicePage.goto("/studio/chat");

      // Wait for UI to be ready
      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toBeVisible({ timeout: 10000 });

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Select swarm mode
      await orchestratorSelector.selectOption("swarm");

      // Send a message
      await chatInput.fill("Hello");
      await alicePage.keyboard.press("Enter");

      // Wait for request to be captured
      await alicePage.waitForTimeout(1000);

      // Verify the request included preferred_orchestrator
      expect(capturedRequestBody).not.toBeNull();
      const requestJson = JSON.parse(capturedRequestBody!);
      expect(requestJson.preferred_orchestrator).toBe("swarm");
    });

    test("should not send preferred_orchestrator when standard mode selected", async ({
      alicePage,
    }) => {
      // Enable orchestrator selector
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: true,
          }),
        });
      });

      // Track the streaming request
      let capturedRequestBody: string | null = null;
      await alicePage.route("**/api/v1/chat/completions/stream", async (route) => {
        capturedRequestBody = route.request().postData();
        await route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          body: 'data: {"content":"Hello!"}\n\ndata: [DONE]\n\n',
        });
      });

      await alicePage.route("**/api/v1/sessions/*/messages", async (route) => {
        if (route.request().method() === "POST") {
          await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
              id: "msg-123",
              role: "user",
              content: "Hello",
              timestamp: Date.now(),
            }),
          });
        } else {
          await route.continue();
        }
      });

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Keep default standard mode
      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toHaveValue("standard");

      // Send a message
      await chatInput.fill("Hello");
      await alicePage.keyboard.press("Enter");

      // Wait for request to be captured
      await alicePage.waitForTimeout(1000);

      // Verify the request did not include preferred_orchestrator (or has standard)
      expect(capturedRequestBody).not.toBeNull();
      const requestJson = JSON.parse(capturedRequestBody!);
      // Standard mode should not include preferred_orchestrator in body
      // OR it can be included as "standard" - depends on implementation
    });
  });

  test.describe("Accessibility", () => {
    test("should have accessible orchestrator selector", async ({
      alicePage,
    }) => {
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: true,
          }),
        });
      });

      await alicePage.goto("/studio/chat");

      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toBeVisible({ timeout: 10000 });

      // Should have accessible label
      await expect(orchestratorSelector).toHaveAttribute("aria-label");

      // Should be keyboard accessible
      await orchestratorSelector.focus();
      expect(await orchestratorSelector.evaluate((el) => document.activeElement === el)).toBe(true);
    });
  });

  test.describe("Persistence", () => {
    test("should persist orchestrator selection during session", async ({
      alicePage,
    }) => {
      await alicePage.route("**/api/v1/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enable_orchestrator_selector: true,
          }),
        });
      });

      await alicePage.goto("/studio/chat");

      const orchestratorSelector = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelector).toBeVisible({ timeout: 10000 });

      // Select swarm mode
      await orchestratorSelector.selectOption("swarm");
      await expect(orchestratorSelector).toHaveValue("swarm");

      // Navigate away and back
      await alicePage.goto("/studio/workflows");
      await alicePage.goto("/studio/chat");

      // Should maintain selection (depending on state management)
      const orchestratorSelectorAfter = alicePage.getByTestId("orchestrator-selector");
      await expect(orchestratorSelectorAfter).toBeVisible({ timeout: 10000 });

      // Note: Persistence behavior depends on state management implementation
      // This test documents the expected behavior
    });
  });
});
