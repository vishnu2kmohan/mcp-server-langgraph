/**
 * Interactive Artifact Rendering E2E Tests
 *
 * Tests the interactive artifact rendering functionality including:
 * - Mermaid diagram rendering
 * - Chart rendering
 * - SVG with zoom/pan
 * - Sandpack execution for JSX/TSX/MDX
 * - Feature flag toggle behavior
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 *
 * To run these tests:
 * 1. Start test infrastructure: `make test-infra-up-build`
 * 2. Run tests: `npm run test:e2e -- --grep "Artifact Rendering"`
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// Mock assistant responses containing artifacts
const MERMAID_RESPONSE = `Here's a flowchart showing the process:

\`\`\`mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
\`\`\`

This diagram shows a simple decision flow.`;

const CHART_RESPONSE = `Here's a chart showing the data:

\`\`\`chart
{
  "type": "bar",
  "data": [
    {"name": "Jan", "value": 100},
    {"name": "Feb", "value": 150},
    {"name": "Mar", "value": 200}
  ],
  "title": "Monthly Sales"
}
\`\`\`

The chart shows increasing monthly sales.`;

const JSX_RESPONSE = `Here's a React component:

\`\`\`jsx
export default function App() {
  return (
    <div className="p-4 bg-blue-100 rounded">
      <h1>Hello World!</h1>
      <button onClick={() => alert('Clicked!')}>Click me</button>
    </div>
  );
}
\`\`\`

You can run this component to see the result.`;

test.describe("Interactive Artifact Rendering", () => {
  test.beforeEach(async ({ alicePage }) => {
    // Navigate to chat page
    await alicePage.goto("/studio/chat");
    await alicePage.waitForLoadState("networkidle");
  });

  test.describe("Mermaid Diagrams", () => {
    test("should render mermaid diagram from assistant response", async ({
      alicePage,
    }) => {
      // Mock the streaming response if backend is not enabled
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          // Simulate SSE streaming response
          const encoder = new TextEncoder();
          const stream = new ReadableStream({
            start(controller) {
              // Send the mermaid response as SSE events
              const chunks = MERMAID_RESPONSE.split(" ");
              chunks.forEach((chunk, i) => {
                const data = JSON.stringify({
                  type: "content",
                  content: chunk + " ",
                });
                controller.enqueue(encoder.encode(`data: ${data}\n\n`));
              });
              controller.enqueue(
                encoder.encode(`data: {"type": "done"}\n\n`)
              );
              controller.close();
            },
          });

          await route.fulfill({
            status: 200,
            headers: {
              "Content-Type": "text/event-stream",
              "Cache-Control": "no-cache",
            },
            body: MERMAID_RESPONSE,
          });
        });
      }

      // Find the chat input
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Send a message requesting a mermaid diagram
      await chatInput.fill("Draw me a flowchart");
      await alicePage.keyboard.press("Enter");

      // Wait for mermaid diagram to render
      // The diagram should render as SVG within a mermaid container
      const mermaidContainer = alicePage.locator(
        '[data-testid="mermaid-diagram"], .mermaid, [class*="mermaid"]'
      );
      await expect(mermaidContainer.first()).toBeVisible({ timeout: 30000 });

      // Verify SVG is rendered (mermaid renders to SVG)
      const svg = mermaidContainer.locator("svg").first();
      await expect(svg).toBeVisible({ timeout: 10000 });
    });

    test("should display mermaid error for invalid syntax", async ({
      alicePage,
    }) => {
      // This test verifies graceful handling of invalid mermaid syntax
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: "```mermaid\ninvalid syntax here\n```",
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Show me an invalid diagram");
      await alicePage.keyboard.press("Enter");

      // Wait for response - should show error state or fallback to code block
      await alicePage.waitForTimeout(5000);

      // Verify the page doesn't crash (basic stability check)
      await expect(chatInput).toBeVisible();
    });
  });

  test.describe("Charts", () => {
    test("should render interactive chart from chart code block", async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: CHART_RESPONSE,
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Send a message requesting a chart
      await chatInput.fill("Show me monthly sales data as a chart");
      await alicePage.keyboard.press("Enter");

      // Wait for chart container to render
      // Charts typically render using recharts library
      const chartContainer = alicePage.locator(
        '[data-testid="chart-container"], .recharts-wrapper, [class*="recharts"]'
      );
      await expect(chartContainer.first()).toBeVisible({ timeout: 30000 });
    });

    test("should handle malformed chart JSON gracefully", async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: "```chart\n{invalid json}\n```",
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Show me a broken chart");
      await alicePage.keyboard.press("Enter");

      // Wait for response
      await alicePage.waitForTimeout(5000);

      // Verify the page handles the error gracefully
      await expect(chatInput).toBeVisible();
    });
  });

  test.describe("Sandpack Execution", () => {
    test("should show Run button for executable code blocks", async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: JSX_RESPONSE,
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Send a message requesting executable code
      await chatInput.fill("Write me a React component");
      await alicePage.keyboard.press("Enter");

      // Wait for code block with Run button
      const runButton = alicePage.locator(
        'button:has-text("Run"), [data-testid="run-code-button"], button[aria-label*="run" i]'
      );
      await expect(runButton.first()).toBeVisible({ timeout: 30000 });
    });

    test("should not auto-execute code blocks", async ({ alicePage }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: JSX_RESPONSE,
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Write me a React component");
      await alicePage.keyboard.press("Enter");

      // Wait for response
      await alicePage.waitForTimeout(5000);

      // Sandpack preview should NOT be visible until Run is clicked
      // This validates the security-conscious opt-in behavior
      const sandpackPreview = alicePage.locator(
        '[data-testid="sandpack-preview"], .sp-preview, iframe[title*="Sandpack"]'
      );
      await expect(sandpackPreview).not.toBeVisible({ timeout: 2000 });
    });

    test("should show Sandpack preview after clicking Run", async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: JSX_RESPONSE,
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Write me a React component");
      await alicePage.keyboard.press("Enter");

      // Wait for Run button and click it
      const runButton = alicePage.locator(
        'button:has-text("Run"), [data-testid="run-code-button"], button[aria-label*="run" i]'
      );
      await expect(runButton.first()).toBeVisible({ timeout: 30000 });
      await runButton.first().click();

      // Sandpack preview should now be visible
      const sandpackPreview = alicePage.locator(
        '[data-testid="sandpack-preview"], .sp-preview, iframe[title*="Sandpack"]'
      );
      await expect(sandpackPreview.first()).toBeVisible({ timeout: 15000 });
    });
  });

  test.describe("Feature Flag", () => {
    test("should fall back to plain code when interactive_artifacts flag is false", async ({
      alicePage,
    }) => {
      // Mock feature flags API to return interactive_artifacts: false
      await alicePage.route("**/api/v1/settings/feature-flags", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            interactive_artifacts: false,
            studio_canvas_shell: true,
            workflows: true,
            sessions: true,
          }),
        });
      });

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: MERMAID_RESPONSE,
          });
        });
      }

      // Reload to pick up mocked feature flags
      await alicePage.reload();
      await alicePage.waitForLoadState("networkidle");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Draw me a flowchart");
      await alicePage.keyboard.press("Enter");

      // Wait for response
      await alicePage.waitForTimeout(5000);

      // Mermaid should render as plain code block, not interactive diagram
      // Look for code element instead of SVG
      const codeBlock = alicePage.locator("pre code, .code-block");
      await expect(codeBlock.first()).toBeVisible({ timeout: 10000 });

      // SVG mermaid diagram should NOT be visible
      const mermaidSvg = alicePage.locator(".mermaid svg");
      await expect(mermaidSvg).not.toBeVisible({ timeout: 2000 });
    });
  });

  test.describe("Rich Content Rendering", () => {
    test("should render markdown formatting in assistant responses", async ({
      alicePage,
    }) => {
      const markdownResponse = `Here's a formatted response:

**Bold text** and *italic text*

- List item 1
- List item 2
- List item 3

\`inline code\` and a link: [Example](https://example.com)`;

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: markdownResponse,
          });
        });
      }

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Format some text for me");
      await alicePage.keyboard.press("Enter");

      // Wait for response
      await alicePage.waitForTimeout(5000);

      // Verify markdown is rendered (bold should become <strong>)
      const boldText = alicePage.locator("strong:has-text('Bold text')");
      await expect(boldText.first()).toBeVisible({ timeout: 10000 });
    });
  });
});
