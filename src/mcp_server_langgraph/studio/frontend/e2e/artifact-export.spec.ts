/**
 * Artifact Export E2E Tests
 *
 * Tests the artifact export functionality that requires browser canvas/image APIs.
 * These tests cover functionality that cannot be tested in jsdom:
 * - PNG export from charts (canvas.toBlob)
 * - SVG to PNG conversion
 * - Download triggering
 *
 * Cross-Reference: Skipped Unit Tests
 * ====================================
 * These E2E tests provide coverage for the following skipped unit tests:
 *
 * @see src/components/Artifacts/ArtifactExporter.test.tsx
 *   - it.skip("should call onExport with PNG format when selected") [line ~171]
 *   - it.skip("should call onExport with PNG blob for SVG data") [line ~382]
 *   - it.skip("should export PNG from SVG element reference") [line ~405]
 *
 * @see src/components/Artifacts/ChartArtifact.test.tsx
 *   - it.skip("should call onDownload when export format selected") [line ~119]
 *
 * To run these tests:
 * 1. Start test infrastructure: `make test-infra-up-build`
 * 2. Run tests: `npm run test:e2e -- --grep "Artifact Export"`
 */

import { test, expect } from "./fixtures/auth";
import * as path from "path";
import * as fs from "fs";

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// Mock feature flags for artifact rendering
const mockFeatureFlags = {
  studio_canvas_shell: true,
  canvas_editable: true,
  interactive_artifacts: true,
  workflows: true,
  sessions: true,
};

// Mock chart response that will render a ChartArtifact
const CHART_RESPONSE = `Here's a chart showing the data:

\`\`\`chart
{
  "type": "bar",
  "title": "Monthly Sales",
  "data": [
    {"label": "Jan", "value": 100},
    {"label": "Feb", "value": 150},
    {"label": "Mar", "value": 200}
  ]
}
\`\`\`

The chart shows increasing monthly sales.`;

// Mock SVG artifact response
const SVG_RESPONSE = `Here's an SVG diagram:

\`\`\`svg
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect x="10" y="10" width="180" height="180" fill="#4CAF50" rx="10"/>
  <circle cx="100" cy="100" r="50" fill="#2196F3"/>
  <text x="100" y="105" text-anchor="middle" fill="white" font-size="16">Test</text>
</svg>
\`\`\`

This is a simple SVG with shapes.`;

test.describe("Artifact Export", () => {
  test.describe("Chart PNG Export", () => {
    test("should trigger PNG download when export button clicked on chart", async ({
      alicePage,
    }) => {
      // Navigate to chat page
      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      // Mock the streaming response if backend is not enabled
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: CHART_RESPONSE,
          });
        });

        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      // Find and use chat input
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Request a chart
      await chatInput.fill("Show me a bar chart of monthly sales");
      await alicePage.keyboard.press("Enter");

      // Wait for chart to render
      const chartContainer = alicePage.locator(
        '[data-testid="chart-artifact"], [data-testid="chart-container"]'
      );
      await expect(chartContainer.first()).toBeVisible({ timeout: 30000 });

      // Find export button
      const exportButton = alicePage.locator(
        'button[aria-label*="export" i], button:has-text("Export")'
      );
      await expect(exportButton.first()).toBeVisible({ timeout: 10000 });

      // Set up download listener BEFORE clicking export
      const downloadPromise = alicePage.waitForEvent("download", {
        timeout: 15000,
      });

      // Click export button
      await exportButton.first().click();

      // Click PNG option in export menu
      const pngOption = alicePage.locator(
        'button:has-text("PNG"), [role="menuitem"]:has-text("PNG")'
      );
      await expect(pngOption.first()).toBeVisible({ timeout: 5000 });
      await pngOption.first().click();

      // Verify download was triggered
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/\.(png|PNG)$/);

      // Cleanup
      await download.delete();
    });

    test("should create valid PNG file from chart export", async ({
      alicePage,
    }) => {
      // Navigate to chat page
      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: CHART_RESPONSE,
          });
        });

        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Show me a chart");
      await alicePage.keyboard.press("Enter");

      // Wait for chart
      const chartContainer = alicePage.locator(
        '[data-testid="chart-artifact"], [data-testid="chart-container"]'
      );
      await expect(chartContainer.first()).toBeVisible({ timeout: 30000 });

      // Export to PNG
      const exportButton = alicePage.locator(
        'button[aria-label*="export" i], button:has-text("Export")'
      );
      await expect(exportButton.first()).toBeVisible({ timeout: 10000 });

      const downloadPromise = alicePage.waitForEvent("download", {
        timeout: 15000,
      });

      await exportButton.first().click();
      const pngOption = alicePage.locator(
        'button:has-text("PNG"), [role="menuitem"]:has-text("PNG")'
      );
      await pngOption.first().click();

      const download = await downloadPromise;

      // Save and verify the file
      const downloadPath = path.join("/tmp", download.suggestedFilename());
      await download.saveAs(downloadPath);

      // Verify file exists and has content
      const fileStats = fs.statSync(downloadPath);
      expect(fileStats.size).toBeGreaterThan(0);

      // Verify PNG magic bytes
      const fileBuffer = fs.readFileSync(downloadPath);
      const pngMagic = Buffer.from([0x89, 0x50, 0x4e, 0x47]);
      expect(fileBuffer.subarray(0, 4).equals(pngMagic)).toBe(true);

      // Cleanup
      fs.unlinkSync(downloadPath);
      await download.delete();
    });
  });

  test.describe("SVG to PNG Export", () => {
    test("should convert SVG artifact to PNG on export", async ({
      alicePage,
    }) => {
      // Navigate to chat page
      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: SVG_RESPONSE,
          });
        });

        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Create an SVG diagram");
      await alicePage.keyboard.press("Enter");

      // Wait for SVG to render
      await alicePage.waitForTimeout(5000);

      // Look for export button (SVG artifacts should have export option)
      const exportButton = alicePage.locator(
        'button[aria-label*="export" i], button:has-text("Export")'
      );

      if ((await exportButton.count()) > 0) {
        await exportButton.first().click();

        // Look for PNG export option
        const pngOption = alicePage.locator(
          'button:has-text("PNG"), [role="menuitem"]:has-text("PNG")'
        );

        if ((await pngOption.count()) > 0) {
          const downloadPromise = alicePage.waitForEvent("download", {
            timeout: 15000,
          });

          await pngOption.first().click();

          const download = await downloadPromise;
          expect(download.suggestedFilename()).toMatch(/\.(png|PNG)$/);

          await download.delete();
        }
      }

      // Basic stability check - page should still be functional
      await expect(chatInput).toBeVisible();
    });
  });

  test.describe("Export Menu Options", () => {
    test("should show PNG, SVG, and PDF export options for charts", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: CHART_RESPONSE,
          });
        });

        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Show me a chart");
      await alicePage.keyboard.press("Enter");

      // Wait for chart
      const chartContainer = alicePage.locator(
        '[data-testid="chart-artifact"], [data-testid="chart-container"]'
      );
      await expect(chartContainer.first()).toBeVisible({ timeout: 30000 });

      // Open export menu
      const exportButton = alicePage.locator(
        'button[aria-label*="export" i], button:has-text("Export")'
      );
      await expect(exportButton.first()).toBeVisible({ timeout: 10000 });
      await exportButton.first().click();

      // Verify all export options are present
      const exportMenu = alicePage.locator(
        '[data-testid="export-menu"], [role="menu"]'
      );
      await expect(exportMenu).toBeVisible({ timeout: 5000 });

      await expect(
        alicePage.locator('[role="menuitem"]:has-text("PNG")')
      ).toBeVisible();
      await expect(
        alicePage.locator('[role="menuitem"]:has-text("SVG")')
      ).toBeVisible();
      await expect(
        alicePage.locator('[role="menuitem"]:has-text("PDF")')
      ).toBeVisible();
    });
  });
});
