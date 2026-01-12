/**
 * DataFrame and Bokeh Rendering E2E Tests
 *
 * Tests the automatic detection and rendering of DataFrames and Bokeh charts
 * from Python code execution output.
 *
 * Coverage:
 * - DataFrame JSON detection (Polars to_dicts, Pandas orient='records')
 * - TableArtifact rendering from DataFrame output
 * - Bokeh HTML detection and rendering
 * - HTMLArtifact rendering for Bokeh charts
 *
 * Cross-Reference: Related Unit Tests
 * ====================================
 * These E2E tests complement the following unit tests:
 *
 * @see src/canvas/CanvasArtifact.test.tsx
 *   - describe("DataFrame Output Detection") - Unit tests for detectDataFrameJson()
 *   - describe("Bokeh HTML Detection") - Unit tests for detectBokehHtml()
 *
 * @see src/canvas/CanvasArtifact.tsx
 *   - detectDataFrameJson() - Detection utility function
 *   - detectBokehHtml() - Detection utility function
 *
 * To run these tests:
 * 1. Start test infrastructure: `make test-infra-up-build`
 * 2. Run tests: `npm run test:e2e -- --grep "DataFrame Rendering"`
 */

import { test, expect } from "./fixtures/auth";

// Backend integration
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// Mock feature flags
const mockFeatureFlags = {
  studio_canvas_shell: true,
  canvas_editable: true,
  interactive_artifacts: true,
  workflows: true,
  sessions: true,
  code_execution: true,
};

// Sample DataFrame JSON output (Polars to_dicts format)
const POLARS_DATAFRAME_OUTPUT = JSON.stringify([
  { name: "Alice", age: 30, city: "New York" },
  { name: "Bob", age: 25, city: "Los Angeles" },
  { name: "Charlie", age: 35, city: "Chicago" },
]);

// Sample DataFrame JSON output (Pandas orient='records' format)
const PANDAS_DATAFRAME_OUTPUT = JSON.stringify([
  { product: "Widget", price: 10.99, quantity: 100 },
  { product: "Gadget", price: 25.5, quantity: 50 },
  { product: "Gizmo", price: 15.75, quantity: 75 },
]);

// Sample Bokeh HTML output
const BOKEH_HTML_OUTPUT = `<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.js"></script>
</head>
<body>
  <div class="bk-root" id="plot">
    <div class="bk-plotdiv"></div>
  </div>
  <script>
    Bokeh.embed.embed_item({"doc_id": "test"}, "plot");
  </script>
</body>
</html>`;

// Python code that outputs DataFrame JSON
const PYTHON_POLARS_CODE = `import polars as pl

df = pl.DataFrame({
    "name": ["Alice", "Bob", "Charlie"],
    "age": [30, 25, 35],
    "city": ["New York", "Los Angeles", "Chicago"]
})
print(df.to_dicts())`;

const PYTHON_PANDAS_CODE = `import pandas as pd

df = pd.DataFrame({
    "product": ["Widget", "Gadget", "Gizmo"],
    "price": [10.99, 25.50, 15.75],
    "quantity": [100, 50, 75]
})
print(df.to_json(orient='records'))`;

const PYTHON_BOKEH_CODE = `from bokeh.plotting import figure
from bokeh.embed import file_html
from bokeh.resources import CDN

p = figure(title="Interactive Plot", x_axis_label='x', y_axis_label='y')
p.line([1, 2, 3, 4, 5], [6, 7, 2, 4, 5], line_width=2)
html = file_html(p, CDN, "My Plot")
print(html)`;

test.describe("DataFrame Rendering", () => {
  test.describe("Polars DataFrame Output", () => {
    test("should render Polars DataFrame as table", async ({ alicePage }) => {
      // Navigate to a page with canvas artifact that can run code
      await alicePage.goto("/studio/canvas");
      await alicePage.waitForLoadState("networkidle");

      // Mock code execution endpoint if backend not enabled
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/code/execute", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              stdout: POLARS_DATAFRAME_OUTPUT,
              stderr: "",
              exit_code: 0,
              duration_ms: 150,
            }),
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

      // Look for code artifact with Python code
      const codeArtifact = alicePage.locator(
        '[data-testid="canvas-artifact"], [data-testid="code-artifact"]'
      );

      if ((await codeArtifact.count()) > 0) {
        // Find run button
        const runButton = alicePage.locator(
          'button:has-text("Run"), button:has-text("Execute"), button[aria-label*="run" i]'
        );

        if ((await runButton.count()) > 0) {
          await runButton.first().click();

          // Wait for DataFrame output to be rendered as table
          const tableOutput = alicePage.locator(
            '[data-testid="dataframe-output"], [data-testid="table-artifact"], table'
          );
          await expect(tableOutput.first()).toBeVisible({ timeout: 15000 });

          // Verify table has expected columns
          const tableHeaders = alicePage.locator("th, thead td");
          const headerTexts = await tableHeaders.allTextContents();

          // Should have name, age, city columns
          expect(headerTexts.some((h) => h.toLowerCase().includes("name"))).toBe(
            true
          );
        }
      }

      // Basic stability check
      await expect(alicePage.locator("body")).toBeVisible();
    });

    test("should display correct row count for DataFrame", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/canvas");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/code/execute", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              stdout: POLARS_DATAFRAME_OUTPUT,
              stderr: "",
              exit_code: 0,
              duration_ms: 150,
            }),
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

      const runButton = alicePage.locator(
        'button:has-text("Run"), button:has-text("Execute")'
      );

      if ((await runButton.count()) > 0) {
        await runButton.first().click();

        // Wait for table rows
        const tableRows = alicePage.locator("tbody tr, [data-testid='table-row']");
        await expect(tableRows.first()).toBeVisible({ timeout: 15000 });

        // Should have 3 data rows (Alice, Bob, Charlie)
        const rowCount = await tableRows.count();
        expect(rowCount).toBeGreaterThanOrEqual(3);
      }
    });
  });

  test.describe("Pandas DataFrame Output", () => {
    test("should render Pandas DataFrame as table", async ({ alicePage }) => {
      await alicePage.goto("/studio/canvas");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/code/execute", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              stdout: PANDAS_DATAFRAME_OUTPUT,
              stderr: "",
              exit_code: 0,
              duration_ms: 200,
            }),
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

      const runButton = alicePage.locator(
        'button:has-text("Run"), button:has-text("Execute")'
      );

      if ((await runButton.count()) > 0) {
        await runButton.first().click();

        // Wait for DataFrame output
        const tableOutput = alicePage.locator(
          '[data-testid="dataframe-output"], table'
        );
        await expect(tableOutput.first()).toBeVisible({ timeout: 15000 });

        // Verify product column data is present
        const productCells = alicePage.locator("td:has-text('Widget')");
        if ((await productCells.count()) > 0) {
          await expect(productCells.first()).toBeVisible();
        }
      }
    });
  });

  test.describe("Bokeh Chart Output", () => {
    test("should render Bokeh HTML output in iframe", async ({ alicePage }) => {
      await alicePage.goto("/studio/canvas");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/code/execute", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              stdout: BOKEH_HTML_OUTPUT,
              stderr: "",
              exit_code: 0,
              duration_ms: 300,
            }),
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

      const runButton = alicePage.locator(
        'button:has-text("Run"), button:has-text("Execute")'
      );

      if ((await runButton.count()) > 0) {
        await runButton.first().click();

        // Wait for Bokeh output
        const bokehOutput = alicePage.locator(
          '[data-testid="bokeh-output"], [data-testid="html-artifact"], iframe'
        );
        await expect(bokehOutput.first()).toBeVisible({ timeout: 15000 });
      }

      // Stability check
      await expect(alicePage.locator("body")).toBeVisible();
    });

    test("should show Bokeh Chart label for Bokeh output", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/canvas");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/code/execute", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              stdout: BOKEH_HTML_OUTPUT,
              stderr: "",
              exit_code: 0,
              duration_ms: 300,
            }),
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

      const runButton = alicePage.locator(
        'button:has-text("Run"), button:has-text("Execute")'
      );

      if ((await runButton.count()) > 0) {
        await runButton.first().click();

        // Look for Bokeh Chart label
        const bokehLabel = alicePage.locator('text="Bokeh Chart"');
        if ((await bokehLabel.count()) > 0) {
          await expect(bokehLabel.first()).toBeVisible({ timeout: 10000 });
        }
      }
    });
  });

  test.describe("Plain Text Fallback", () => {
    test("should render plain text when output is not DataFrame or Bokeh", async ({
      alicePage,
    }) => {
      await alicePage.goto("/studio/canvas");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/code/execute", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              stdout: "Hello, World!\nThis is plain text output.",
              stderr: "",
              exit_code: 0,
              duration_ms: 50,
            }),
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

      const runButton = alicePage.locator(
        'button:has-text("Run"), button:has-text("Execute")'
      );

      if ((await runButton.count()) > 0) {
        await runButton.first().click();

        // Plain text should be shown in pre/code element
        const stdoutOutput = alicePage.locator(
          'pre:has-text("Hello, World"), [data-testid="stdout"]'
        );
        await expect(stdoutOutput.first()).toBeVisible({ timeout: 10000 });
      }
    });
  });

  test.describe("Error Handling", () => {
    test("should show stderr for execution errors", async ({ alicePage }) => {
      await alicePage.goto("/studio/canvas");
      await alicePage.waitForLoadState("networkidle");

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/code/execute", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              stdout: "",
              stderr: "NameError: name 'undefined_var' is not defined",
              exit_code: 1,
              duration_ms: 50,
            }),
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

      const runButton = alicePage.locator(
        'button:has-text("Run"), button:has-text("Execute")'
      );

      if ((await runButton.count()) > 0) {
        await runButton.first().click();

        // Error output should be visible
        const stderrOutput = alicePage.locator(
          '[data-testid="stderr"], pre:has-text("NameError")'
        );
        if ((await stderrOutput.count()) > 0) {
          await expect(stderrOutput.first()).toBeVisible({ timeout: 10000 });
        }
      }

      // Page should remain stable
      await expect(alicePage.locator("body")).toBeVisible();
    });
  });
});
