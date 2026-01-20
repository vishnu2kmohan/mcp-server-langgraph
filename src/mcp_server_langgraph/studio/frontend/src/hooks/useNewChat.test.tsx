/**
 * Tests for useNewChat hook
 *
 * TDD: Tests for new chat session creation with authenticatedFetch integration.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";

// Mock react-router
const mockNavigate = vi.fn();
const mockRevalidate = vi.fn();
vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
  useRevalidator: () => ({ revalidate: mockRevalidate }),
}));

// Mock authenticatedFetch - create mock as module-level variable
const mockAuthenticatedFetch = vi.fn();
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: (...args: unknown[]) => mockAuthenticatedFetch(...args),
}));

// Mock intendedRoute
const mockSetIntendedRoute = vi.fn();
vi.mock("../utils/intendedRoute", () => ({
  setIntendedRoute: (...args: unknown[]) => mockSetIntendedRoute(...args),
}));

// Mock telemetry context
const mockTrackSessionCreation = vi.fn();
vi.mock("../contexts/TelemetryContext", () => ({
  useSessionTelemetry: () => ({
    trackSessionCreation: mockTrackSessionCreation,
  }),
}));

import { useNewChat } from "./useNewChat";

describe("useNewChat", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default mock for successful response
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ id: "default-id", name: "New Chat" }),
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("successful session creation", () => {
    it("should create a session and navigate to it", async () => {
      const sessionId = "new-session-123";
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: sessionId, name: "New Chat" }),
      });

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
        "/api/v1/sessions",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ name: "New Chat" }),
          onAuthFailure: expect.any(Function),
        }),
      );
      expect(mockNavigate).toHaveBeenCalledWith(`/studio/chat/${sessionId}`);
      expect(result.current.error).toBeNull();
    });

    it("should use custom session name", async () => {
      const sessionId = "custom-session-456";
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: sessionId, name: "My Custom Chat" }),
      });

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat({ name: "My Custom Chat" });
      });

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
        "/api/v1/sessions",
        expect.objectContaining({
          body: JSON.stringify({ name: "My Custom Chat" }),
        }),
      );
    });

    it("should use custom base path for navigation", async () => {
      const sessionId = "custom-path-789";
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: sessionId, name: "New Chat" }),
      });

      const { result } = renderHook(() =>
        useNewChat({ basePath: "/custom/path" }),
      );

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(mockNavigate).toHaveBeenCalledWith(`/custom/path/${sessionId}`);
    });

    it("should track successful session creation", async () => {
      const sessionId = "tracked-session";
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: sessionId, name: "New Chat" }),
      });

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(mockTrackSessionCreation).toHaveBeenCalledWith(
        expect.objectContaining({
          sessionId,
          sessionName: "New Chat",
          success: true,
          durationMs: expect.any(Number),
        }),
      );
    });
  });

  describe("loading state", () => {
    it("should set isCreating to false after completion", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "test", name: "New Chat" }),
      });

      const { result } = renderHook(() => useNewChat());

      expect(result.current.isCreating).toBe(false);

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(result.current.isCreating).toBe(false);
    });

    it("should set isCreating to false after error", async () => {
      mockAuthenticatedFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useNewChat());

      expect(result.current.isCreating).toBe(false);

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(result.current.isCreating).toBe(false);
    });
  });

  describe("error handling", () => {
    it("should handle API error response", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Session limit exceeded" }),
      });

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(result.current.error).toBe("Session limit exceeded");
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should handle network errors", async () => {
      mockAuthenticatedFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(result.current.error).toBe("Network error");
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should track failed session creation", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Creation failed" }),
      });

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(mockTrackSessionCreation).toHaveBeenCalledWith(
        expect.objectContaining({
          success: false,
          error: "Creation failed",
          durationMs: expect.any(Number),
        }),
      );
    });

    it("should clear error on successful retry", async () => {
      // First call fails
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Temporary error" }),
      });

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(result.current.error).toBe("Temporary error");

      // Second call succeeds
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "retry-success", name: "New Chat" }),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("authentication failure handling", () => {
    it("should provide onAuthFailure callback to authenticatedFetch", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "test-123", name: "New Chat" }),
      });

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      // Verify onAuthFailure is passed
      const callOptions = mockAuthenticatedFetch.mock.calls[0][1];
      expect(callOptions).toHaveProperty("onAuthFailure");
      expect(typeof callOptions.onAuthFailure).toBe("function");
    });

    it("should navigate to login when auth fails", async () => {
      // Capture the onAuthFailure callback
      mockAuthenticatedFetch.mockImplementationOnce(
        async (_url: string, options: { onAuthFailure?: () => void }) => {
          // Simulate 401 scenario where onAuthFailure is called
          options.onAuthFailure?.();
          return {
            ok: false,
            json: async () => ({ detail: "Unauthorized" }),
          };
        },
      );

      const { result } = renderHook(() => useNewChat());

      await act(async () => {
        await result.current.createNewChat();
      });

      // Should navigate to login
      expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
    });
  });
});
