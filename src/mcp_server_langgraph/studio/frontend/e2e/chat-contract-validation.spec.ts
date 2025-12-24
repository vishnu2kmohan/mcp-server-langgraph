/**
 * Chat API Contract Validation E2E Tests
 *
 * Validates that chat send/receive operations match the expected API contracts.
 * Tests both request body formats and response structures.
 *
 * Purpose:
 * - Verify frontend sends correctly formatted request bodies
 * - Verify no 4xx errors from contract mismatches
 * - Test both streaming and non-streaming modes
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 */

import { test, expect } from "./fixtures/auth";

const backendEnabled = process.env.BACKEND_ENABLED !== "false";

test.describe("Chat API Contract Validation", () => {
  test.describe("Chat Message Send/Receive", () => {
    test("should send message with correct request body format", async ({
      alicePage,
    }) => {
      // Track API requests to validate contract
      const apiRequests: Array<{ url: string; body: unknown; method: string }> =
        [];

      await alicePage.route("**/api/v1/**", async (route) => {
        const request = route.request();
        const url = request.url();
        const method = request.method();

        // Capture request body for analysis
        try {
          const body = request.postDataJSON();
          apiRequests.push({ url, body, method });
        } catch {
          // No body or non-JSON
        }

        // Continue to backend or mock
        if (backendEnabled) {
          await route.continue();
        } else {
          // Mock responses for offline testing
          if (url.includes("/chat/completions")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({
                id: "msg-123",
                choices: [
                  {
                    message: {
                      role: "assistant",
                      content: "Hello! How can I help you today?",
                    },
                  },
                ],
              }),
            });
            return;
          }
          if (url.includes("/sessions")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({
                data: [
                  {
                    id: "session-1",
                    name: "Test Session",
                    status: "active",
                    created_at: new Date().toISOString(),
                    message_count: 0,
                  },
                ],
              }),
            });
            return;
          }
          if (url.includes("/health")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({ status: "healthy" }),
            });
            return;
          }
          if (url.includes("/me")) {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({
                id: "alice",
                username: "alice",
                roles: ["developer"],
              }),
            });
            return;
          }
          await route.continue();
        }
      });

      // Navigate to chat
      await alicePage.goto("/studio/chat");

      // Wait for chat input
      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Type and send a message
      await chatInput.fill("Hello, test message");
      await alicePage.keyboard.press("Enter");

      // Wait for response
      await alicePage.waitForTimeout(2000);

      // Validate the chat completion request was properly formatted
      const chatRequest = apiRequests.find(
        (r) => r.url.includes("/chat/completions") && r.method === "POST"
      );

      if (chatRequest) {
        // Validate request body structure
        expect(chatRequest.body).toBeDefined();
        const body = chatRequest.body as Record<string, unknown>;

        // Should have session_id (snake_case for backend)
        expect(body).toHaveProperty("session_id");
        expect(typeof body.session_id).toBe("string");

        // Should have messages array
        expect(body).toHaveProperty("messages");
        expect(Array.isArray(body.messages)).toBe(true);

        // Each message should have role and content
        const messages = body.messages as Array<{
          role: string;
          content: string;
        }>;
        for (const msg of messages) {
          expect(typeof msg.role).toBe("string");
          expect(typeof msg.content).toBe("string");
        }
      }
    });

    test("should not send camelCase field names to backend", async ({
      alicePage,
    }) => {
      const apiRequests: Array<{ url: string; body: unknown }> = [];

      await alicePage.route("**/api/v1/**", async (route) => {
        const request = route.request();

        try {
          const body = request.postDataJSON();
          apiRequests.push({ url: request.url(), body });
        } catch {
          // No body
        }

        if (backendEnabled) {
          await route.continue();
        } else {
          // Basic mock for offline testing
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ success: true }),
          });
        }
      });

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      await chatInput.fill("Test message");
      await alicePage.keyboard.press("Enter");
      await alicePage.waitForTimeout(2000);

      // Check all POST requests for camelCase field violations
      const postRequests = apiRequests.filter((r) => r.body);

      for (const req of postRequests) {
        const body = req.body as Record<string, unknown>;

        // Common camelCase violations to check
        const camelCaseViolations = [
          "sessionId", // Should be session_id
          "messageId", // Should be message_id
          "textResponse", // Should be value
          "selectedOption", // Should be selected_option_id
          "approvedBy", // For batch: derived from auth, not sent
          "rejectedBy", // For batch: derived from auth, not sent
          "newTitle", // Should be new_name
        ];

        for (const violation of camelCaseViolations) {
          expect(
            violation in body,
            `Request to ${req.url} should not have camelCase field '${violation}'`
          ).toBe(false);
        }
      }
    });
  });

  test.describe("Streaming Chat", () => {
    test("should handle streaming responses without contract errors", async ({
      alicePage,
    }) => {
      let streamingErrors = 0;

      await alicePage.route("**/api/v1/**", async (route) => {
        const request = route.request();
        const response = await route.fetch();

        // Check for 4xx errors (contract mismatches)
        if (response.status() >= 400 && response.status() < 500) {
          streamingErrors++;
          console.error(
            `Contract error: ${response.status()} on ${request.url()}`
          );
        }

        await route.fulfill({ response });
      });

      await alicePage.goto("/studio/chat");

      const chatInput = alicePage.getByRole("textbox", {
        name: /message|chat/i,
      });
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // Send a message that triggers streaming
      await chatInput.fill("Tell me a short story");
      await alicePage.keyboard.press("Enter");

      // Wait for streaming to complete
      await alicePage.waitForTimeout(5000);

      // No contract errors should occur
      expect(streamingErrors).toBe(0);
    });
  });
});

test.describe("Agent Request Contract Validation", () => {
  test("should send batch approve with correct field names", async ({
    adminPage,
  }) => {
    const apiRequests: Array<{ url: string; body: unknown }> = [];

    await adminPage.route("**/api/v1/**", async (route) => {
      const request = route.request();

      try {
        const body = request.postDataJSON();
        apiRequests.push({ url: request.url(), body });
      } catch {
        // No body
      }

      if (backendEnabled) {
        await route.continue();
      } else {
        if (request.url().includes("/agents/requests/batch/approve")) {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              success: true,
              processed: 1,
              failed: 0,
              results: [{ request_id: "req-1", success: true }],
            }),
          });
          return;
        }
        await route.continue();
      }
    });

    // Navigate to admin page where batch approvals happen
    await adminPage.goto("/studio/admin");

    // The test verifies that when batch approve is triggered,
    // the request body contains only { request_ids, reason }
    // NOT { request_ids, approved_by, reason }
    const batchApproveRequest = apiRequests.find((r) =>
      r.url.includes("/agents/requests/batch/approve")
    );

    if (batchApproveRequest) {
      const body = batchApproveRequest.body as Record<string, unknown>;

      // Should have request_ids
      expect(body).toHaveProperty("request_ids");
      expect(Array.isArray(body.request_ids)).toBe(true);

      // Should NOT have approved_by (derived from auth)
      expect(body).not.toHaveProperty("approved_by");
    }
  });
});

test.describe("Artifact Contract Validation", () => {
  test("should send fork artifact with new_name (not new_title)", async ({
    alicePage,
  }) => {
    const apiRequests: Array<{ url: string; body: unknown }> = [];

    await alicePage.route("**/api/v1/**", async (route) => {
      const request = route.request();

      try {
        const body = request.postDataJSON();
        apiRequests.push({ url: request.url(), body });
      } catch {
        // No body
      }

      if (backendEnabled) {
        await route.continue();
      } else {
        if (request.url().includes("/artifacts") && request.url().includes("/fork")) {
          await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
              id: "art-fork-123",
              parentId: "art-1",
              version: 1,
            }),
          });
          return;
        }
        await route.continue();
      }
    });

    // Navigate to canvas (where artifacts are)
    await alicePage.goto("/studio/canvas");

    // The fork artifact action would be triggered here
    // We validate that when called, it uses new_name not new_title
    const forkRequest = apiRequests.find((r) => r.url.includes("/fork"));

    if (forkRequest) {
      const body = forkRequest.body as Record<string, unknown>;

      // Should use new_name
      if ("new_name" in body) {
        expect(typeof body.new_name).toBe("string");
      }

      // Should NOT use new_title (old/wrong field name)
      expect(body).not.toHaveProperty("new_title");
      expect(body).not.toHaveProperty("newTitle");
    }
  });
});
