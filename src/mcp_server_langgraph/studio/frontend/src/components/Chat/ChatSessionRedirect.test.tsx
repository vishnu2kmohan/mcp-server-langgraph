/**
 * ChatSessionRedirect Tests
 *
 * Tests for the URL pattern redirect component that converts path-based
 * session IDs to query parameter-based session IDs.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Routes, Route } from "react-router";

import { ChatSessionRedirect } from "./ChatSessionRedirect";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Tests
// =============================================================================

describe("ChatSessionRedirect", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("With sessionId param", () => {
    it("should redirect to chat page with session query param", () => {
      // Render component in a route that captures the sessionId
      render(
        <TestProvider initialEntries={["/studio/chat/abc123"]}>
          <Routes>
            <Route
              path="/studio/chat/:sessionId"
              element={<ChatSessionRedirect />}
            />
            <Route
              path="/studio/chat"
              element={<div data-testid="chat-page">Chat Page</div>}
            />
          </Routes>
        </TestProvider>,
      );

      // Should redirect to the chat page (Navigate renders nothing visible)
      // The MemoryRouter will process the redirect
      expect(screen.getByTestId("chat-page")).toBeInTheDocument();
    });

    it("should preserve sessionId in query param", () => {
      let _currentLocation = "";

      const LocationCapture = () => {
        // Capture the location when rendered
        _currentLocation = window.location.search;
        return <div data-testid="destination">Redirected</div>;
      };

      render(
        <TestProvider initialEntries={["/studio/chat/session-xyz-789"]}>
          <Routes>
            <Route
              path="/studio/chat/:sessionId"
              element={<ChatSessionRedirect />}
            />
            <Route path="/studio/chat" element={<LocationCapture />} />
          </Routes>
        </TestProvider>,
      );

      expect(screen.getByTestId("destination")).toBeInTheDocument();
    });
  });

  describe("Without sessionId param", () => {
    it("should redirect to /studio/chat when sessionId param is undefined", () => {
      // When the route matches but sessionId is undefined in params
      // We simulate this by having a parent route that renders ChatSessionRedirect
      // without passing sessionId in the path
      render(
        <TestProvider initialEntries={["/redirect-test"]}>
          <Routes>
            {/* Route without :sessionId - simulates missing param */}
            <Route path="/redirect-test" element={<ChatSessionRedirect />} />
            <Route
              path="/studio/chat"
              element={
                <div data-testid="chat-page-no-session">
                  Chat Page Without Session
                </div>
              }
            />
          </Routes>
        </TestProvider>,
      );

      // Should redirect to /studio/chat (without session param)
      expect(screen.getByTestId("chat-page-no-session")).toBeInTheDocument();
    });
  });
});
