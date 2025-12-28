/**
 * useTokenUsage Tests
 *
 * TDD tests for the Token Usage hook.
 * Tests cover:
 * - Per-session token usage tracking
 * - Input vs output token breakdown
 * - Cost estimation
 * - Context window usage
 * - Historical usage data
 * - Authentication with authenticatedFetch
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";

// Mock dependencies
const mockNavigate = vi.fn();
const mockAuthenticatedFetch = vi.fn();
const mockSetIntendedRoute = vi.fn();

vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: (...args: unknown[]) => mockAuthenticatedFetch(...args),
}));

vi.mock("../utils/intendedRoute", () => ({
  setIntendedRoute: (...args: unknown[]) => mockSetIntendedRoute(...args),
}));

import { useTokenUsage } from "./useTokenUsage";

describe("useTokenUsage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default successful response
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          inputTokens: 100,
          outputTokens: 200,
          totalTokens: 300,
        }),
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // Authentication Tests
  // ===========================================================================

  describe("authentication", () => {
    it("should use authenticatedFetch for API calls", async () => {
      renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(mockAuthenticatedFetch).toHaveBeenCalled();
      });

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
        "/api/v1/sessions/session-1/token-usage",
        expect.objectContaining({
          onAuthFailure: expect.any(Function),
        }),
      );
    });

    it("should navigate to login on auth failure", async () => {
      mockAuthenticatedFetch.mockImplementationOnce(
        async (_url: string, options: { onAuthFailure?: () => void }) => {
          options.onAuthFailure?.();
          return { ok: false, status: 401 };
        },
      );

      renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(mockSetIntendedRoute).toHaveBeenCalled();
      });

      expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should start with loading state when fetching", () => {
      mockAuthenticatedFetch.mockImplementation(() => new Promise(() => {}));
      const { result } = renderHook(() => useTokenUsage("session-1"));

      expect(result.current.isLoading).toBe(true);
    });

    it("should set loading to false after fetch completes", async () => {
      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  // ===========================================================================
  // Token Data Tests
  // ===========================================================================

  describe("token data", () => {
    it("should fetch and return token usage data", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 1500,
            outputTokens: 3000,
            totalTokens: 4500,
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.inputTokens).toBe(1500);
        expect(result.current.outputTokens).toBe(3000);
        expect(result.current.totalTokens).toBe(4500);
      });
    });

    it("should return zero values when no data", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 0,
            outputTokens: 0,
            totalTokens: 0,
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.inputTokens).toBe(0);
        expect(result.current.outputTokens).toBe(0);
        expect(result.current.totalTokens).toBe(0);
      });
    });
  });

  // ===========================================================================
  // Cost Estimation Tests
  // ===========================================================================

  describe("cost estimation", () => {
    it("should calculate estimated cost based on token usage", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 1000,
            outputTokens: 2000,
            totalTokens: 3000,
            inputCostPer1k: 0.003,
            outputCostPer1k: 0.015,
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        // Input: 1000 tokens * $0.003/1k = $0.003
        // Output: 2000 tokens * $0.015/1k = $0.03
        // Total: $0.033
        expect(result.current.estimatedCost).toBeCloseTo(0.033, 3);
      });
    });

    it("should return null cost when pricing not configured", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 1000,
            outputTokens: 2000,
            totalTokens: 3000,
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.estimatedCost).toBeNull();
      });
    });
  });

  // ===========================================================================
  // Context Window Tests
  // ===========================================================================

  describe("context window", () => {
    it("should calculate context window usage percentage", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 1000,
            outputTokens: 2000,
            totalTokens: 3000,
            contextWindowSize: 128000,
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.contextWindowUsage).toBeCloseTo(2.34, 1);
        expect(result.current.contextWindowSize).toBe(128000);
      });
    });

    it("should provide context window warning when usage is high", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 50000,
            outputTokens: 50000,
            totalTokens: 100000,
            contextWindowSize: 128000,
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.contextWindowUsage).toBeGreaterThan(75);
        expect(result.current.isContextWindowNearLimit).toBe(true);
      });
    });
  });

  // ===========================================================================
  // Historical Data Tests
  // ===========================================================================

  describe("historical data", () => {
    it("should return historical usage data when available", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 1000,
            outputTokens: 2000,
            totalTokens: 3000,
            history: [
              { timestamp: "2024-01-01T00:00:00Z", tokens: 500 },
              { timestamp: "2024-01-01T01:00:00Z", tokens: 1500 },
              { timestamp: "2024-01-01T02:00:00Z", tokens: 3000 },
            ],
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.history).toHaveLength(3);
        expect(result.current.history?.[0].tokens).toBe(500);
      });
    });
  });

  // ===========================================================================
  // Refresh Tests
  // ===========================================================================

  describe("refresh", () => {
    it("should refresh token data", async () => {
      mockAuthenticatedFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 100,
            outputTokens: 200,
            totalTokens: 300,
          }),
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.totalTokens).toBe(300);
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(mockAuthenticatedFetch).toHaveBeenCalledTimes(2);
    });
  });

  // ===========================================================================
  // Error Handling Tests
  // ===========================================================================

  describe("error handling", () => {
    it("should handle fetch errors gracefully", async () => {
      mockAuthenticatedFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.error).toBe("Failed to load token usage");
        expect(result.current.isLoading).toBe(false);
      });
    });

    it("should handle non-OK responses", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() => useTokenUsage("session-1"));

      await waitFor(() => {
        expect(result.current.error).toBe("Failed to load token usage");
      });
    });
  });

  // ===========================================================================
  // Session Change Tests
  // ===========================================================================

  describe("session change", () => {
    it("should fetch new data when session ID changes", async () => {
      mockAuthenticatedFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            inputTokens: 100,
            outputTokens: 200,
            totalTokens: 300,
          }),
      });

      const { result, rerender } = renderHook(
        ({ sessionId }) => useTokenUsage(sessionId),
        { initialProps: { sessionId: "session-1" } },
      );

      await waitFor(() => {
        expect(result.current.totalTokens).toBe(300);
      });

      rerender({ sessionId: "session-2" });

      await waitFor(() => {
        expect(mockAuthenticatedFetch).toHaveBeenCalledTimes(2);
      });
    });
  });
});
