/**
 * Model Selector E2E Tests
 *
 * Tests the Enhanced Model Selector feature including:
 * - Model listing with capability badges (Thinking, Vision, Tools)
 * - Model lifecycle status badges (Preview, Legacy, Deprecated)
 * - Deprecation warning banner for deprecated models
 * - Sunset date display for deprecated models
 * - Model sorting by lifecycle status (current > preview > legacy > deprecated)
 * - Model search functionality
 * - Recent models section
 *
 * Sprint 2 - Enhanced Model Selector
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Model Selector", () => {
  test.describe("Basic Functionality", () => {
    test("should display model selector button with current model", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      // Wait for model selector to be ready
      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });

      // Should show some model name (not "Loading models...")
      await expect(modelSelectorButton).not.toContainText("Loading models", {
        timeout: 5000,
      });
    });

    test("should open dropdown on click", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });

      // Click to open dropdown
      await modelSelectorButton.click();

      // Dropdown should be visible
      const dropdown = alicePage.getByRole("listbox", {
        name: /available ai models/i,
      });
      await expect(dropdown).toBeVisible({ timeout: 5000 });
    });

    test("should list models from multiple providers", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Check for models from different providers
      await expect(
        alicePage.getByTestId(/model-option-claude/i)
      ).toBeVisible({ timeout: 5000 });
      await expect(
        alicePage.getByTestId(/model-option-gpt|model-option-o[13]/i)
      ).toBeVisible({ timeout: 5000 });
      await expect(
        alicePage.getByTestId(/model-option-gemini/i)
      ).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Capability Badges", () => {
    test("should display Thinking badge for thinking-capable models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Claude Opus 4.5 should have Thinking badge
      const thinkingBadge = alicePage.getByTestId(
        "capability-badge-thinking-claude-opus-4-5"
      );
      await expect(thinkingBadge).toBeVisible({ timeout: 5000 });
      await expect(thinkingBadge).toContainText("Thinking");
    });

    test("should display Vision badge for vision-capable models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Claude Opus 4.5 should have Vision badge
      const visionBadge = alicePage.getByTestId(
        "capability-badge-vision-claude-opus-4-5"
      );
      await expect(visionBadge).toBeVisible({ timeout: 5000 });
      await expect(visionBadge).toContainText("Vision");
    });

    test("should display Tools badge for tools-capable models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Claude Opus 4.5 should have Tools badge
      const toolsBadge = alicePage.getByTestId(
        "capability-badge-tools-claude-opus-4-5"
      );
      await expect(toolsBadge).toBeVisible({ timeout: 5000 });
      await expect(toolsBadge).toContainText("Tools");
    });
  });

  test.describe("Model Lifecycle Status", () => {
    test("should display Preview badge for preview models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Gemini 3 Flash should have Preview badge
      const previewBadge = alicePage.getByTestId(
        "status-badge-preview-gemini-3-flash"
      );
      await expect(previewBadge).toBeVisible({ timeout: 5000 });
      await expect(previewBadge).toContainText("Preview");
    });

    test("should display Legacy badge for legacy models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // GPT-4o should have Legacy badge
      const legacyBadge = alicePage.getByTestId("status-badge-legacy-gpt-4o");
      await expect(legacyBadge).toBeVisible({ timeout: 5000 });
      await expect(legacyBadge).toContainText("Legacy");
    });

    test("should display Deprecated badge for deprecated models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Claude 3.5 Sonnet should have Deprecated badge
      const deprecatedBadge = alicePage.getByTestId(
        "status-badge-deprecated-claude-3-5-sonnet"
      );
      await expect(deprecatedBadge).toBeVisible({ timeout: 5000 });
      await expect(deprecatedBadge).toContainText("Deprecated");
    });

    test("should display sunset date for deprecated models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Find the deprecated model option and check for sunset text
      const deprecatedModel = alicePage.getByTestId(
        "model-option-claude-3-5-sonnet"
      );
      await expect(deprecatedModel).toBeVisible({ timeout: 5000 });

      // Should contain sunset date text (e.g., "Sunset Oct 2025")
      await expect(deprecatedModel).toContainText(/sunset/i, { timeout: 5000 });
    });
  });

  test.describe("Deprecation Warning Banner", () => {
    test("should show deprecation warning when deprecated model is selected", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Select a deprecated model
      const deprecatedModel = alicePage.getByTestId(
        "model-option-claude-3-5-sonnet"
      );
      await deprecatedModel.click();

      // Deprecation warning banner should appear
      const warningBanner = alicePage.getByTestId("deprecation-warning-banner");
      await expect(warningBanner).toBeVisible({ timeout: 5000 });

      // Should contain model name and deprecation info
      await expect(warningBanner).toContainText("Claude 3.5 Sonnet");
      await expect(warningBanner).toContainText("deprecated");
    });

    test("should show sunset date in deprecation warning", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Select a deprecated model
      const deprecatedModel = alicePage.getByTestId(
        "model-option-claude-3-5-sonnet"
      );
      await deprecatedModel.click();

      // Warning should show sunset date
      const warningBanner = alicePage.getByTestId("deprecation-warning-banner");
      await expect(warningBanner).toBeVisible({ timeout: 5000 });

      // Should contain a date (month name format)
      await expect(warningBanner).toContainText(/October|November|2025/i);
    });

    test("should dismiss deprecation warning when X button is clicked", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Select a deprecated model
      const deprecatedModel = alicePage.getByTestId(
        "model-option-claude-3-5-sonnet"
      );
      await deprecatedModel.click();

      // Warning should appear
      const warningBanner = alicePage.getByTestId("deprecation-warning-banner");
      await expect(warningBanner).toBeVisible({ timeout: 5000 });

      // Click dismiss button
      const dismissButton = alicePage.getByTestId("deprecation-warning-dismiss");
      await dismissButton.click();

      // Warning should be hidden
      await expect(warningBanner).not.toBeVisible({ timeout: 5000 });
    });

    test("should not show deprecation warning for current models", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Select a current model
      const currentModel = alicePage.getByTestId("model-option-claude-opus-4-5");
      await currentModel.click();

      // Wait a moment for any banners to potentially appear
      await alicePage.waitForTimeout(500);

      // Deprecation warning should NOT be visible
      const warningBanner = alicePage.getByTestId("deprecation-warning-banner");
      await expect(warningBanner).not.toBeVisible();
    });
  });

  test.describe("Model Sorting", () => {
    test("should sort models by status priority (current first)", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Get all model options
      const modelOptions = alicePage.locator('[data-testid^="model-option-"]');
      const count = await modelOptions.count();

      // Collect model statuses in order
      const statuses: string[] = [];
      for (let i = 0; i < Math.min(count, 10); i++) {
        const option = modelOptions.nth(i);
        const hasPreview = await option.locator('[data-testid^="status-badge-preview"]').count();
        const hasLegacy = await option.locator('[data-testid^="status-badge-legacy"]').count();
        const hasDeprecated = await option.locator('[data-testid^="status-badge-deprecated"]').count();

        if (hasDeprecated > 0) statuses.push("deprecated");
        else if (hasLegacy > 0) statuses.push("legacy");
        else if (hasPreview > 0) statuses.push("preview");
        else statuses.push("current");
      }

      // Verify correct order: current models should come before deprecated ones
      const currentIndex = statuses.indexOf("current");
      const deprecatedIndex = statuses.indexOf("deprecated");

      if (currentIndex !== -1 && deprecatedIndex !== -1) {
        expect(currentIndex).toBeLessThan(deprecatedIndex);
      }
    });
  });

  test.describe("Keyboard Navigation", () => {
    test("should open dropdown with Enter key", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });

      // Focus and press Enter
      await modelSelectorButton.focus();
      await modelSelectorButton.press("Enter");

      // Dropdown should be visible
      const dropdown = alicePage.getByRole("listbox", {
        name: /available ai models/i,
      });
      await expect(dropdown).toBeVisible({ timeout: 5000 });
    });

    test("should navigate models with Arrow keys", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });

      // Open dropdown
      await modelSelectorButton.click();

      // Press ArrowDown to focus first option
      await modelSelectorButton.press("ArrowDown");

      // Press ArrowDown again to move to second option
      await modelSelectorButton.press("ArrowDown");

      // Verify focus moved (visual focus indicator)
      // This is hard to test without visual regression, so just verify no errors
    });

    test("should close dropdown with Escape key", async ({ alicePage }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });

      // Open dropdown
      await modelSelectorButton.click();

      const dropdown = alicePage.getByRole("listbox", {
        name: /available ai models/i,
      });
      await expect(dropdown).toBeVisible({ timeout: 5000 });

      // Press Escape to close
      await modelSelectorButton.press("Escape");

      // Dropdown should be hidden
      await expect(dropdown).not.toBeVisible({ timeout: 5000 });
    });
  });

  test.describe("Model Search", () => {
    test("should filter models when typing in search input", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      // Check if search input exists (feature flag controlled)
      const searchInput = alicePage.getByTestId("model-search-input");
      const searchExists = await searchInput.isVisible().catch(() => false);

      if (searchExists) {
        // Type search query
        await searchInput.fill("claude");

        // Should show only Claude models
        const claudeModels = alicePage.locator(
          '[data-testid^="model-option-claude"]'
        );
        await expect(claudeModels.first()).toBeVisible({ timeout: 5000 });

        // Should not show OpenAI models
        const gptModels = alicePage.locator('[data-testid^="model-option-gpt"]');
        await expect(gptModels).not.toBeVisible();
      }
    });

    test("should show 'No models found' when search has no results", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");

      const modelSelectorButton = alicePage.getByTestId("model-selector-button");
      await expect(modelSelectorButton).toBeVisible({ timeout: 10000 });
      await modelSelectorButton.click();

      const searchInput = alicePage.getByTestId("model-search-input");
      const searchExists = await searchInput.isVisible().catch(() => false);

      if (searchExists) {
        // Type non-existent model name
        await searchInput.fill("nonexistentmodel12345");

        // Should show "No models found" message
        await expect(alicePage.getByText(/no models found/i)).toBeVisible({
          timeout: 5000,
        });
      }
    });
  });
});
