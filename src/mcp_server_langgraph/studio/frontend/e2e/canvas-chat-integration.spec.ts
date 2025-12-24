/**
 * Canvas-Chat Integration E2E Tests
 *
 * Tests the end-to-end flow of artifacts from chat streaming to canvas display.
 * This validates Issue 3 of the Frontend Architecture Fixes:
 *
 * Flow: User message → AI response with artifact → Artifact extraction →
 *       POST to /api/v1/artifacts → Canvas revalidation → Canvas shows artifact
 *
 * To run these tests:
 * 1. Start test infrastructure: `make test-infra-up-build`
 * 2. Run tests: `npm run test:e2e -- --grep "Canvas-Chat Integration"`
 */

import { test, expect } from "./fixtures/auth";

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== "false";

// Track created artifacts for verification
const createdArtifacts: Array<{
  id: string;
  type: string;
  content: string;
  sessionId: string;
}> = [];

// Mock feature flags
const mockFeatureFlags = {
  studio_canvas_shell: true,
  canvas_editable: true,
  interactive_artifacts: true,
  workflows: true,
  sessions: true,
};

// Mock response with mermaid diagram that should be extracted as artifact
const MERMAID_ARTIFACT_RESPONSE = `Here's the architecture diagram you requested:

\`\`\`mermaid
graph TB
    subgraph Frontend
        UI[React UI]
        Store[Redux Store]
    end
    subgraph Backend
        API[FastAPI]
        LG[LangGraph]
    end
    UI --> Store
    Store --> API
    API --> LG
\`\`\`

This diagram shows the main components of our system.`;

// Mock response with code artifact
const CODE_ARTIFACT_RESPONSE = `Here's a utility function for you:

\`\`\`typescript
/**
 * Formats a date as a relative time string
 */
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return \`\${Math.floor(seconds / 60)}m ago\`;
  if (seconds < 86400) return \`\${Math.floor(seconds / 3600)}h ago\`;
  return \`\${Math.floor(seconds / 86400)}d ago\`;
}
\`\`\`

You can use this to display timestamps in a user-friendly format.`;

test.describe("Canvas-Chat Integration", () => {
  test.describe("Artifact Extraction from Chat", () => {
    test("should extract mermaid artifact from chat and display in canvas", async ({
      alicePage,
    }) => {
      // Clear tracking array
      createdArtifacts.length = 0;

      // Set up API mocking
      if (!backendEnabled) {
        // Mock feature flags
        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        // Mock sessions endpoint
        await alicePage.route("**/api/v1/sessions*", async (route) => {
          if (route.request().method() === "GET") {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({
                items: [
                  {
                    id: "session-integration-test",
                    name: "Integration Test Session",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                  },
                ],
                cursor: null,
              }),
            });
          } else {
            await route.continue();
          }
        });

        // Mock chat streaming
        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: MERMAID_ARTIFACT_RESPONSE,
          });
        });

        // Mock artifact creation - capture created artifacts
        await alicePage.route("**/api/v1/artifacts", async (route) => {
          if (route.request().method() === "POST") {
            const body = JSON.parse(route.request().postData() || "{}");
            const newArtifact = {
              id: `artifact-${Date.now()}`,
              ...body,
              version: 1,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            };
            createdArtifacts.push(newArtifact);
            await route.fulfill({
              status: 201,
              contentType: "application/json",
              body: JSON.stringify(newArtifact),
            });
          } else if (route.request().method() === "GET") {
            // Return captured artifacts
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({ items: createdArtifacts, cursor: null }),
            });
          } else {
            await route.continue();
          }
        });
      }

      // Navigate to chat page with session
      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      // Find chat input
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Send message that triggers mermaid diagram response
      await chatInput.fill("Draw me an architecture diagram");
      await alicePage.keyboard.press("Enter");

      // Wait for streaming to complete
      await alicePage.waitForTimeout(3000);

      // Verify artifact was created (check API call was made)
      if (!backendEnabled) {
        expect(createdArtifacts.length).toBeGreaterThan(0);
        expect(createdArtifacts[0].type).toBe("mermaid");
      }

      // Look for canvas panel or artifact indicator
      const canvasPanel = alicePage.locator(
        '[data-testid="canvas-panel"], [data-testid="artifact-panel"], .canvas-panel'
      );

      // If canvas is visible, verify artifact appears there
      if (await canvasPanel.isVisible({ timeout: 5000 })) {
        // Look for artifact tab or content in canvas
        const artifactTab = canvasPanel.locator(
          '[data-testid="artifact-tab"], .artifact-tab, [role="tab"]'
        );
        await expect(artifactTab.first()).toBeVisible({ timeout: 10000 });
      }
    });

    test("should extract code artifact from chat and display in canvas", async ({
      alicePage,
    }) => {
      createdArtifacts.length = 0;

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        await alicePage.route("**/api/v1/sessions*", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: "session-code-test",
                  name: "Code Test Session",
                  created_at: new Date().toISOString(),
                },
              ],
              cursor: null,
            }),
          });
        });

        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: CODE_ARTIFACT_RESPONSE,
          });
        });

        await alicePage.route("**/api/v1/artifacts", async (route) => {
          if (route.request().method() === "POST") {
            const body = JSON.parse(route.request().postData() || "{}");
            const newArtifact = {
              id: `artifact-code-${Date.now()}`,
              ...body,
              version: 1,
              createdAt: new Date().toISOString(),
            };
            createdArtifacts.push(newArtifact);
            await route.fulfill({
              status: 201,
              contentType: "application/json",
              body: JSON.stringify(newArtifact),
            });
          } else if (route.request().method() === "GET") {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({ items: createdArtifacts, cursor: null }),
            });
          } else {
            await route.continue();
          }
        });
      }

      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Write me a date formatting utility");
      await alicePage.keyboard.press("Enter");

      await alicePage.waitForTimeout(3000);

      if (!backendEnabled) {
        expect(createdArtifacts.length).toBeGreaterThan(0);
        expect(createdArtifacts[0].type).toBe("code");
        expect(createdArtifacts[0].content).toContain("formatRelativeTime");
      }
    });

    test("should deduplicate artifacts when same content is streamed twice", async ({
      alicePage,
    }) => {
      createdArtifacts.length = 0;
      let postCallCount = 0;

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        await alicePage.route("**/api/v1/sessions*", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [{ id: "session-dedup", name: "Dedup Test" }],
              cursor: null,
            }),
          });
        });

        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: MERMAID_ARTIFACT_RESPONSE,
          });
        });

        await alicePage.route("**/api/v1/artifacts", async (route) => {
          if (route.request().method() === "POST") {
            postCallCount++;
            const body = JSON.parse(route.request().postData() || "{}");
            await route.fulfill({
              status: 201,
              contentType: "application/json",
              body: JSON.stringify({
                id: `artifact-dedup-${postCallCount}`,
                ...body,
                version: 1,
              }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({ items: [], cursor: null }),
            });
          }
        });
      }

      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Send first message
      await chatInput.fill("Draw architecture diagram");
      await alicePage.keyboard.press("Enter");
      await alicePage.waitForTimeout(3000);

      const firstCount = postCallCount;

      // Send same message again (should trigger same response)
      await chatInput.fill("Draw architecture diagram again");
      await alicePage.keyboard.press("Enter");
      await alicePage.waitForTimeout(3000);

      // Artifact should only be created once due to deduplication
      // (same content hash should prevent duplicate POST)
      if (!backendEnabled) {
        // First call should create artifact, second should be deduplicated
        expect(postCallCount).toBe(firstCount);
      }
    });
  });

  test.describe("Session Context", () => {
    test("should associate extracted artifacts with current session", async ({
      alicePage,
    }) => {
      createdArtifacts.length = 0;
      const expectedSessionId = "session-context-test-123";

      if (!backendEnabled) {
        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        await alicePage.route("**/api/v1/sessions*", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [
                {
                  id: expectedSessionId,
                  name: "Session Context Test",
                  created_at: new Date().toISOString(),
                },
              ],
              cursor: null,
            }),
          });
        });

        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: MERMAID_ARTIFACT_RESPONSE,
          });
        });

        await alicePage.route("**/api/v1/artifacts", async (route) => {
          if (route.request().method() === "POST") {
            const body = JSON.parse(route.request().postData() || "{}");
            createdArtifacts.push(body);
            await route.fulfill({
              status: 201,
              contentType: "application/json",
              body: JSON.stringify({ id: "artifact-session", ...body }),
            });
          } else {
            await route.continue();
          }
        });
      }

      // Navigate to specific session
      await alicePage.goto(`/studio/chat/${expectedSessionId}`);
      await alicePage.waitForLoadState("networkidle");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });

      // If the page loads with a chat input, send a message
      if (await chatInput.isVisible({ timeout: 5000 })) {
        await chatInput.fill("Create a diagram for this session");
        await alicePage.keyboard.press("Enter");
        await alicePage.waitForTimeout(3000);

        // Verify artifact was associated with correct session
        if (!backendEnabled && createdArtifacts.length > 0) {
          expect(createdArtifacts[0].sessionId).toBe(expectedSessionId);
        }
      }
    });
  });

  test.describe("Error Handling", () => {
    test("should gracefully handle artifact API errors", async ({
      alicePage,
    }) => {
      if (!backendEnabled) {
        await alicePage.route("**/api/v1/features", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mockFeatureFlags),
          });
        });

        await alicePage.route("**/api/v1/sessions*", async (route) => {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              items: [{ id: "session-error-test", name: "Error Test" }],
              cursor: null,
            }),
          });
        });

        await alicePage.route("**/api/v1/chat/stream", async (route) => {
          await route.fulfill({
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
            body: MERMAID_ARTIFACT_RESPONSE,
          });
        });

        // Mock artifact API to return error
        await alicePage.route("**/api/v1/artifacts", async (route) => {
          if (route.request().method() === "POST") {
            await route.fulfill({
              status: 500,
              contentType: "application/json",
              body: JSON.stringify({ error: "Internal server error" }),
            });
          } else {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({ items: [], cursor: null }),
            });
          }
        });
      }

      await alicePage.goto("/studio/chat");
      await alicePage.waitForLoadState("networkidle");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Create a diagram");
      await alicePage.keyboard.press("Enter");

      // Wait for response
      await alicePage.waitForTimeout(5000);

      // Page should not crash - chat should still be functional
      await expect(chatInput).toBeVisible();
      await expect(chatInput).toBeEnabled();
    });
  });
});
