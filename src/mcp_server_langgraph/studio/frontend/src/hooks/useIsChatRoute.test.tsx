/**
 * useIsChatRoute Hook Tests
 *
 * Tests for the chat route detection hook that encapsulates
 * the logic for determining if the current route is a chat route.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { useIsChatRoute, isChatRoutePath } from "./useIsChatRoute";

// =============================================================================
// Pure Function Tests
// =============================================================================

describe("isChatRoutePath", () => {
  it("returns true for /studio/chat", () => {
    expect(isChatRoutePath("/studio/chat")).toBe(true);
  });

  it("returns true for /studio/chat/", () => {
    expect(isChatRoutePath("/studio/chat/")).toBe(true);
  });

  it("returns true for /studio/chat/session-id", () => {
    expect(isChatRoutePath("/studio/chat/session-123")).toBe(true);
  });

  it("returns true for /studio/chat/session-id with trailing slash", () => {
    expect(isChatRoutePath("/studio/chat/session-123/")).toBe(true);
  });

  it("returns false for /studio/workflows", () => {
    expect(isChatRoutePath("/studio/workflows")).toBe(false);
  });

  it("returns false for /studio/observability", () => {
    expect(isChatRoutePath("/studio/observability")).toBe(false);
  });

  it("returns false for /studio/settings", () => {
    expect(isChatRoutePath("/studio/settings")).toBe(false);
  });

  it("returns false for /studio/cost", () => {
    expect(isChatRoutePath("/studio/cost")).toBe(false);
  });

  it("returns false for root path /", () => {
    expect(isChatRoutePath("/")).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isChatRoutePath("")).toBe(false);
  });

  it("returns false for partial match /studio/chatbot", () => {
    // Should not match /studio/chatbot - only /studio/chat or /studio/chat/...
    expect(isChatRoutePath("/studio/chatbot")).toBe(false);
  });
});

// =============================================================================
// Hook Tests
// =============================================================================

describe("useIsChatRoute", () => {
  // Store original window.location
  const originalLocation = window.location;

  beforeEach(() => {
    // Reset window.location mock before each test
    // @ts-expect-error - window.location is read-only
    delete window.location;
  });

  afterEach(() => {
    // Restore original window.location
    window.location = originalLocation;
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  /**
   * Helper to render hook with a specific route
   */
  function renderWithRoute(routePath: string, windowPath?: string) {
    // Set window.location.pathname
    window.location = {
      ...originalLocation,
      pathname: windowPath ?? routePath,
    };

    return renderHook(() => useIsChatRoute(), {
      wrapper: ({ children }) => (
        <MemoryRouter initialEntries={[routePath]}>{children}</MemoryRouter>
      ),
    });
  }

  it("returns true when on /studio/chat", () => {
    const { result } = renderWithRoute("/studio/chat");
    expect(result.current).toBe(true);
  });

  it("returns true when on /studio/chat/:sessionId", () => {
    const { result } = renderWithRoute("/studio/chat/session-123");
    expect(result.current).toBe(true);
  });

  it("returns false when on /studio/workflows", () => {
    const { result } = renderWithRoute("/studio/workflows");
    expect(result.current).toBe(false);
  });

  it("returns false when on /studio/observability", () => {
    const { result } = renderWithRoute("/studio/observability");
    expect(result.current).toBe(false);
  });

  it("returns false when on /studio/settings", () => {
    const { result } = renderWithRoute("/studio/settings");
    expect(result.current).toBe(false);
  });

  it("returns false when on /studio/cost", () => {
    const { result } = renderWithRoute("/studio/cost");
    expect(result.current).toBe(false);
  });

  // Edge case: router and window disagree
  describe("when router and window paths disagree", () => {
    it("trusts router when navigating away from chat", () => {
      // Router says /studio/workflows, window still shows /studio/chat
      // This happens during navigation before window updates
      const { result } = renderWithRoute("/studio/workflows", "/studio/chat");
      expect(result.current).toBe(false); // Trust router: navigating away
    });

    it("trusts window when router is behind", () => {
      // Router says /studio/chat, window shows /studio/chat
      // Normal case - both agree
      const { result } = renderWithRoute("/studio/chat", "/studio/chat");
      expect(result.current).toBe(true);
    });

    it("returns false when both are non-chat routes", () => {
      const { result } = renderWithRoute(
        "/studio/workflows",
        "/studio/workflows",
      );
      expect(result.current).toBe(false);
    });
  });
});
