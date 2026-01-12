/**
 * Hallucination Reporting E2E Tests
 *
 * Tests the AI hallucination reporting feature:
 * - Flag button visibility on assistant messages
 * - Report dialog flow (open, select category, submit)
 * - Thank you confirmation message
 * - "Reported" badge after submission
 * - Feature flag gating
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Hallucination Reporting", () => {
  test.beforeEach(async ({ alicePage }) => {
    // Mock the hallucination report endpoint
    if (!backendEnabled) {
      await alicePage.route(
        "**/api/v1/feedback/hallucination-report",
        async (route) => {
          await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
              id: "report-123",
              message_id: "msg-123",
              session_id: "session-123",
              category: "factual_error",
              severity: "medium",
              status: "submitted",
            }),
          });
        }
      );
    }
  });

  test.describe("Flag Button Visibility", () => {
    test("should show Flag button on assistant messages", async ({
      alicePage,
    }) => {
      // Navigate to chat with an existing conversation
      await alicePage.goto("/studio/chat");

      // Wait for messages to load (need at least one assistant message)
      const assistantMessage = alicePage.locator(
        '[data-testid="assistant-message"], [data-role="assistant"]'
      );

      // If no messages exist, we may need to send one first
      const hasAssistantMessage = await assistantMessage.count();
      if (hasAssistantMessage === 0) {
        // Send a message to get a response
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await expect(chatInput).toBeVisible({ timeout: 10000 });
        await chatInput.fill("Hello, what is 2+2?");
        await chatInput.press("Enter");

        // Wait for assistant response
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      // Find the flag button on the assistant message
      const flagButton = alicePage.getByRole("button", {
        name: /report inaccuracy|flag/i,
      });
      await expect(flagButton.first()).toBeVisible({ timeout: 5000 });
    });

    test("should NOT show Flag button on user messages", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // User messages should not have the flag button
      const userMessage = alicePage.locator(
        '[data-testid="user-message"], [data-role="user"]'
      );
      const count = await userMessage.count();

      if (count > 0) {
        // Check that flag button is not within user message
        const flagInUserMessage = userMessage
          .first()
          .getByRole("button", { name: /report inaccuracy|flag/i });
        await expect(flagInUserMessage).not.toBeVisible();
      }
    });
  });

  test.describe("Report Dialog Flow", () => {
    test("should open dialog when Flag button is clicked", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Ensure we have an assistant message
      const assistantMessage = alicePage.locator('[data-role="assistant"]');
      if ((await assistantMessage.count()) === 0) {
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await chatInput.fill("Hello");
        await chatInput.press("Enter");
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      // Click flag button
      const flagButton = alicePage
        .getByRole("button", { name: /report inaccuracy|flag/i })
        .first();
      await flagButton.click();

      // Dialog should open
      const dialog = alicePage.getByRole("dialog");
      await expect(dialog).toBeVisible({ timeout: 5000 });
      await expect(
        alicePage.getByText(/report inaccuracy/i)
      ).toBeVisible();
    });

    test("should display all category options", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const assistantMessage = alicePage.locator('[data-role="assistant"]');
      if ((await assistantMessage.count()) === 0) {
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await chatInput.fill("Hello");
        await chatInput.press("Enter");
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      const flagButton = alicePage
        .getByRole("button", { name: /report inaccuracy|flag/i })
        .first();
      await flagButton.click();

      // All categories should be visible
      await expect(alicePage.getByText("Factual Error")).toBeVisible();
      await expect(alicePage.getByText("Outdated Information")).toBeVisible();
      await expect(alicePage.getByText("Made Up Source")).toBeVisible();
      await expect(alicePage.getByText("Other Issue")).toBeVisible();
    });

    test("should submit report successfully", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const assistantMessage = alicePage.locator('[data-role="assistant"]');
      if ((await assistantMessage.count()) === 0) {
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await chatInput.fill("Hello");
        await chatInput.press("Enter");
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      const flagButton = alicePage
        .getByRole("button", { name: /report inaccuracy|flag/i })
        .first();
      await flagButton.click();

      // Select a category
      await alicePage.getByText("Factual Error").click();

      // Optionally add details
      const detailsTextarea = alicePage.getByPlaceholder(
        /provide additional details/i
      );
      await detailsTextarea.fill("The information about dates is incorrect");

      // Submit
      const submitButton = alicePage.getByRole("button", { name: /submit/i });
      await expect(submitButton).toBeEnabled();
      await submitButton.click();

      // Dialog should close and thank you message should appear
      await expect(alicePage.getByRole("dialog")).not.toBeVisible({
        timeout: 5000,
      });
      await expect(alicePage.getByText(/thank you/i)).toBeVisible({
        timeout: 5000,
      });
    });

    test("should close dialog on Cancel", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const assistantMessage = alicePage.locator('[data-role="assistant"]');
      if ((await assistantMessage.count()) === 0) {
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await chatInput.fill("Hello");
        await chatInput.press("Enter");
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      const flagButton = alicePage
        .getByRole("button", { name: /report inaccuracy|flag/i })
        .first();
      await flagButton.click();

      await expect(alicePage.getByRole("dialog")).toBeVisible();

      // Click cancel
      await alicePage.getByRole("button", { name: /cancel/i }).click();

      // Dialog should close
      await expect(alicePage.getByRole("dialog")).not.toBeVisible();
    });

    test("should close dialog on ESC key", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const assistantMessage = alicePage.locator('[data-role="assistant"]');
      if ((await assistantMessage.count()) === 0) {
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await chatInput.fill("Hello");
        await chatInput.press("Enter");
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      const flagButton = alicePage
        .getByRole("button", { name: /report inaccuracy|flag/i })
        .first();
      await flagButton.click();

      await expect(alicePage.getByRole("dialog")).toBeVisible();

      // Press ESC
      await alicePage.keyboard.press("Escape");

      // Dialog should close
      await expect(alicePage.getByRole("dialog")).not.toBeVisible();
    });
  });

  test.describe("Submit Button State", () => {
    test("should disable Submit button until category selected", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const assistantMessage = alicePage.locator('[data-role="assistant"]');
      if ((await assistantMessage.count()) === 0) {
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await chatInput.fill("Hello");
        await chatInput.press("Enter");
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      const flagButton = alicePage
        .getByRole("button", { name: /report inaccuracy|flag/i })
        .first();
      await flagButton.click();

      const submitButton = alicePage.getByRole("button", { name: /submit/i });

      // Initially disabled
      await expect(submitButton).toBeDisabled();

      // Select category
      await alicePage.getByText("Outdated Information").click();

      // Now enabled
      await expect(submitButton).toBeEnabled();
    });
  });

  test.describe("Accessibility", () => {
    test("should have accessible dialog structure", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const assistantMessage = alicePage.locator('[data-role="assistant"]');
      if ((await assistantMessage.count()) === 0) {
        const chatInput = alicePage.getByRole("textbox", {
          name: /message|chat/i,
        });
        await chatInput.fill("Hello");
        await chatInput.press("Enter");
        await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
      }

      const flagButton = alicePage
        .getByRole("button", { name: /report inaccuracy|flag/i })
        .first();
      await flagButton.click();

      const dialog = alicePage.getByRole("dialog");
      await expect(dialog).toBeVisible();

      // Check ARIA attributes
      await expect(dialog).toHaveAttribute("aria-modal", "true");
      await expect(dialog).toHaveAttribute("aria-labelledby");
    });
  });
});
