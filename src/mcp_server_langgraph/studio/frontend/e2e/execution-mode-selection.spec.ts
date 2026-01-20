/**
 * Execution Mode Selection E2E Tests
 *
 * Tests the execution mode toggle functionality:
 * - SegmentedControl UI for mode selection
 * - Keyboard shortcut (Ctrl/Cmd+Shift+M) to cycle modes
 * - Bypass mode permission checks via OpenFGA
 *
 * Mode cycle order:
 * - Without bypass permission: default → plan → auto_accept → default
 * - With bypass permission: default → plan → auto_accept → bypass → default
 */

import { test, expect } from "./fixtures/auth";

test.describe("Execution Mode Selection", () => {
  test.describe("SegmentedControl UI", () => {
    test("should display execution mode SegmentedControl in chat input", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Wait for chat input area to load
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // SegmentedControl should be visible
      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 5000 });
    });

    test("should display all four mode options", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // All four modes should be present as radio buttons
      await expect(alicePage.getByRole("radio", { name: /default mode/i })).toBeVisible();
      await expect(alicePage.getByRole("radio", { name: /plan mode/i })).toBeVisible();
      await expect(alicePage.getByRole("radio", { name: /auto mode/i })).toBeVisible();
      await expect(alicePage.getByRole("radio", { name: /bypass mode/i })).toBeVisible();
    });

    test("should select default mode by default", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // Default mode should be selected
      const defaultOption = alicePage.getByRole("radio", { name: /default mode/i });
      await expect(defaultOption).toHaveAttribute("aria-checked", "true");
    });

    test("should change mode when clicking Plan segment", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // Click Plan mode
      const planOption = alicePage.getByRole("radio", { name: /plan mode/i });
      await planOption.click();

      // Plan mode should now be selected
      await expect(planOption).toHaveAttribute("aria-checked", "true");

      // Default should no longer be selected
      const defaultOption = alicePage.getByRole("radio", { name: /default mode/i });
      await expect(defaultOption).toHaveAttribute("aria-checked", "false");
    });

    test("should change mode when clicking Auto segment", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // Click Auto mode
      const autoOption = alicePage.getByRole("radio", { name: /auto mode/i });
      await autoOption.click();

      // Auto mode should now be selected
      await expect(autoOption).toHaveAttribute("aria-checked", "true");
    });
  });

  test.describe("Bypass Mode Permissions", () => {
    test("alice should have bypass mode enabled (has bypass_executor permission)", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // Bypass mode should NOT be disabled for alice (who has permission)
      const bypassOption = alicePage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).not.toBeDisabled();
    });

    test("bob should have bypass mode disabled (no bypass_executor permission)", async ({
      bobPage,
    }) => {
      await bobPage.goto("/studio/chat");

      const segmentedControl = bobPage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // Bypass mode should be disabled for bob (no permission)
      const bypassOption = bobPage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).toBeDisabled();
    });

    test("alice can select bypass mode", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const bypassOption = alicePage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).toBeVisible({ timeout: 10000 });

      // Click Bypass mode
      await bypassOption.click();

      // Bypass mode should now be selected
      await expect(bypassOption).toHaveAttribute("aria-checked", "true");
    });
  });

  test.describe("Keyboard Shortcut (Ctrl/Cmd+Shift+M)", () => {
    test("should cycle modes with Ctrl+Shift+M", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Focus on chat input
      await chatInput.focus();

      // Verify starting in default mode
      const defaultOption = alicePage.getByRole("radio", { name: /default mode/i });
      await expect(defaultOption).toHaveAttribute("aria-checked", "true");

      // Press Ctrl+Shift+M to cycle to next mode (plan)
      await alicePage.keyboard.press("Control+Shift+m");

      const planOption = alicePage.getByRole("radio", { name: /plan mode/i });
      await expect(planOption).toHaveAttribute("aria-checked", "true");
    });

    test("should cycle through all modes including bypass for alice", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });
      await chatInput.focus();

      // Default → Plan
      await alicePage.keyboard.press("Control+Shift+m");
      await expect(alicePage.getByRole("radio", { name: /plan mode/i })).toHaveAttribute(
        "aria-checked",
        "true"
      );

      // Plan → Auto
      await alicePage.keyboard.press("Control+Shift+m");
      await expect(alicePage.getByRole("radio", { name: /auto mode/i })).toHaveAttribute(
        "aria-checked",
        "true"
      );

      // Auto → Bypass (alice has permission)
      await alicePage.keyboard.press("Control+Shift+m");
      await expect(alicePage.getByRole("radio", { name: /bypass mode/i })).toHaveAttribute(
        "aria-checked",
        "true"
      );

      // Bypass → Default (cycle complete)
      await alicePage.keyboard.press("Control+Shift+m");
      await expect(alicePage.getByRole("radio", { name: /default mode/i })).toHaveAttribute(
        "aria-checked",
        "true"
      );
    });

    test("should skip bypass mode for bob (no permission)", async ({ bobPage }) => {
      await bobPage.goto("/studio/chat");

      const chatInput = bobPage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });
      await chatInput.focus();

      // Default → Plan
      await bobPage.keyboard.press("Control+Shift+m");
      await expect(bobPage.getByRole("radio", { name: /plan mode/i })).toHaveAttribute(
        "aria-checked",
        "true"
      );

      // Plan → Auto
      await bobPage.keyboard.press("Control+Shift+m");
      await expect(bobPage.getByRole("radio", { name: /auto mode/i })).toHaveAttribute(
        "aria-checked",
        "true"
      );

      // Auto → Default (bypass is skipped because bob has no permission)
      await bobPage.keyboard.press("Control+Shift+m");
      await expect(bobPage.getByRole("radio", { name: /default mode/i })).toHaveAttribute(
        "aria-checked",
        "true"
      );
    });
  });

  test.describe("Mode Persistence", () => {
    test("should maintain selected mode after typing in input", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Select plan mode
      const planOption = alicePage.getByRole("radio", { name: /plan mode/i });
      await planOption.click();
      await expect(planOption).toHaveAttribute("aria-checked", "true");

      // Type in the input
      await chatInput.fill("Hello, this is a test message");

      // Mode should still be plan
      await expect(planOption).toHaveAttribute("aria-checked", "true");
    });
  });

  test.describe("Bypass Mode Auto-Approval Flow", () => {
    test("bypass mode should display appropriate indicator when active", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const bypassOption = alicePage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).toBeVisible({ timeout: 10000 });

      // Select bypass mode
      await bypassOption.click();
      await expect(bypassOption).toHaveAttribute("aria-checked", "true");

      // Verify bypass mode visual indicator (shield icon should be visible)
      const bypassSegment = alicePage.locator('[data-value="bypass"]');
      await expect(bypassSegment).toBeVisible();
    });

    test("bypass mode should show tooltip explaining risk-aware behavior", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const bypassOption = alicePage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).toBeVisible({ timeout: 10000 });

      // Hover over bypass option to see tooltip
      await bypassOption.hover();

      // Tooltip should mention "risk-aware" or "permission"
      const tooltip = alicePage.getByRole("tooltip");
      await expect(tooltip).toContainText(/risk|permission|auto/i);
    });

    test("sending message in bypass mode includes execution_mode parameter", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Enable bypass mode
      const bypassOption = alicePage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).toBeVisible({ timeout: 10000 });
      await bypassOption.click();

      // Intercept API requests to verify execution_mode is sent
      let capturedExecutionMode: string | undefined;
      await alicePage.route("**/api/v1/chat/**", async (route) => {
        const request = route.request();
        if (request.method() === "POST") {
          const postData = request.postDataJSON();
          capturedExecutionMode = postData?.execution_mode;
        }
        await route.continue();
      });

      // Type and send a message
      const chatInput = alicePage.getByRole("textbox", { name: /message|chat/i });
      await chatInput.fill("What time is it?");
      await alicePage.keyboard.press("Enter");

      // Wait for request to be made
      await alicePage.waitForTimeout(1000);

      // Verify execution_mode was sent as "bypass"
      expect(capturedExecutionMode).toBe("bypass");
    });
  });

  test.describe("Accessibility", () => {
    test("should have proper aria-label describing keyboard shortcut", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // The radiogroup should have an aria-label mentioning the keyboard shortcut
      const radiogroup = alicePage.getByRole("radiogroup");
      await expect(radiogroup).toHaveAttribute("aria-label", /Ctrl|Cmd/);
    });

    test("should be navigable with keyboard arrow keys", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const defaultOption = alicePage.getByRole("radio", { name: /default mode/i });
      await expect(defaultOption).toBeVisible({ timeout: 10000 });

      // Focus on the default option
      await defaultOption.focus();

      // Navigate with arrow right
      await alicePage.keyboard.press("ArrowRight");

      // Plan should now be focused/selected
      const planOption = alicePage.getByRole("radio", { name: /plan mode/i });
      await expect(planOption).toBeFocused();
    });

    test("each segment has appropriate accessible name", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      // All options should have accessible names
      await expect(
        alicePage.getByRole("radio", { name: /default mode/i })
      ).toBeVisible({ timeout: 10000 });
      await expect(
        alicePage.getByRole("radio", { name: /plan mode/i })
      ).toBeVisible();
      await expect(
        alicePage.getByRole("radio", { name: /auto mode/i })
      ).toBeVisible();
      await expect(
        alicePage.getByRole("radio", { name: /bypass mode.*permission/i })
      ).toBeVisible();
    });
  });

  test.describe("Navigation Persistence", () => {
    test("should maintain mode when navigating to settings and back", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Select plan mode
      const planOption = alicePage.getByRole("radio", { name: /plan mode/i });
      await expect(planOption).toBeVisible({ timeout: 10000 });
      await planOption.click();
      await expect(planOption).toHaveAttribute("aria-checked", "true");

      // Navigate to settings
      const settingsLink = alicePage.getByRole("link", { name: /settings/i });
      if (await settingsLink.isVisible()) {
        await settingsLink.click();
        await alicePage.waitForURL(/settings/);

        // Navigate back to chat
        await alicePage.goto("/studio/chat");

        // Mode should still be plan (stored in Redux)
        const planOptionAfterNav = alicePage.getByRole("radio", { name: /plan mode/i });
        await expect(planOptionAfterNav).toHaveAttribute("aria-checked", "true");
      }
    });

    test("should maintain bypass mode when switching sessions", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Select bypass mode
      const bypassOption = alicePage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).toBeVisible({ timeout: 10000 });
      await bypassOption.click();
      await expect(bypassOption).toHaveAttribute("aria-checked", "true");

      // Create a new session (if button exists)
      const newChatButton = alicePage.getByRole("button", { name: /new chat|new session/i });
      if (await newChatButton.isVisible()) {
        await newChatButton.click();

        // Mode should persist across session change
        const bypassOptionAfterSwitch = alicePage.getByRole("radio", { name: /bypass mode/i });
        await expect(bypassOptionAfterSwitch).toHaveAttribute("aria-checked", "true");
      }
    });
  });

  test.describe("PreferencesMenu Integration", () => {
    test("should display preferences menu button", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      // Wait for chat area to load
      const chatInput = alicePage.getByRole("textbox", { name: /message|chat/i });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Preferences menu button should be visible (gear icon or "Preferences" text)
      const preferencesButton = alicePage.getByTestId("preferences-menu-trigger").or(
        alicePage.getByRole("button", { name: /preferences|settings/i })
      );
      await expect(preferencesButton).toBeVisible();
    });

    test("should open preferences menu and show model selector", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const preferencesButton = alicePage.getByTestId("preferences-menu-trigger").or(
        alicePage.getByRole("button", { name: /preferences/i })
      );
      await expect(preferencesButton).toBeVisible({ timeout: 10000 });
      await preferencesButton.click();

      // Model selector should be visible in the menu
      const modelSelector = alicePage.getByTestId("model-selector").or(
        alicePage.getByRole("combobox", { name: /model/i })
      );
      await expect(modelSelector).toBeVisible({ timeout: 5000 });
    });

    test("should show thinking level options in preferences menu", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const preferencesButton = alicePage.getByTestId("preferences-menu-trigger").or(
        alicePage.getByRole("button", { name: /preferences/i })
      );
      await expect(preferencesButton).toBeVisible({ timeout: 10000 });
      await preferencesButton.click();

      // Thinking level selector should be visible
      const thinkingSelector = alicePage.getByTestId("thinking-level-selector").or(
        alicePage.getByText(/thinking|reasoning/i)
      );
      await expect(thinkingSelector).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Error Handling", () => {
    test("should handle bypass permission check failure gracefully", async ({
      alicePage,
    }) => {
      // Intercept the permission check API and return an error
      await alicePage.route("**/api/v1/auth/bypass-permission", async (route) => {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Internal server error" }),
        });
      });

      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // Bypass mode should be disabled when permission check fails (fail-closed)
      const bypassOption = alicePage.getByRole("radio", { name: /bypass mode/i });
      await expect(bypassOption).toBeDisabled();
    });

    test("should continue functioning when permission check times out", async ({
      alicePage,
    }) => {
      // Intercept the permission check API and delay response
      await alicePage.route("**/api/v1/auth/bypass-permission", async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ allowed: true }),
        });
      });

      await alicePage.goto("/studio/chat");

      const segmentedControl = alicePage.getByTestId("execution-mode-segmented");
      await expect(segmentedControl).toBeVisible({ timeout: 10000 });

      // Other modes should still be functional while waiting
      const planOption = alicePage.getByRole("radio", { name: /plan mode/i });
      await planOption.click();
      await expect(planOption).toHaveAttribute("aria-checked", "true");
    });
  });
});
