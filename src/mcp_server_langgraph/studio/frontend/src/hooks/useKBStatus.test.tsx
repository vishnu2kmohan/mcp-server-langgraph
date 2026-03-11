/**
 * useKBStatus Hook Tests
 *
 * TDD: These tests are written FIRST to define the expected behavior
 * of the useKBStatus hook for KB status integration.
 *
 * Tests verify:
 * 1. Hook fetches KB status from API
 * 2. Returns loading state
 * 3. Returns KB status data (ready, misconfigured, unavailable)
 * 4. Returns error state on failure
 * 5. Provides derived state for UI components
 * 6. Polls for status updates
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { useKBStatus } from "./useKBStatus";

// Mock the RTK Query endpoint
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useGetKBStatusQuery: vi.fn(),
  };
});
import { useGetKBStatusQuery } from "../api";

const mockUseGetKBStatusQuery = useGetKBStatusQuery as ReturnType<typeof vi.fn>;

describe("useKBStatus", () => {
  // Create a minimal Redux store wrapper
  const createWrapper = () => {
    const store = configureStore({
      reducer: {
        // Minimal reducer for tests
        test: (state = {}) => state,
      },
    });

    return ({ children }: { children: ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should return isLoading true when fetching", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.status).toBeUndefined();
    });

    it("should return isLoading false after data loads", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: {
          status: "ready",
          qdrantConnected: true,
          collectionName: "mcp_context",
          vectorsCount: 1500,
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  // ===========================================================================
  // Status Data Tests
  // ===========================================================================

  describe("status data", () => {
    it("should return ready status when KB is configured", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: {
          status: "ready",
          qdrantConnected: true,
          collectionName: "mcp_context",
          vectorsCount: 2500,
          embeddingProvider: "google_vertex",
          embeddingModel: "text-embedding-005",
          embeddingDimensions: 768,
          contextTokenBudget: 2000,
          contextTopK: 5,
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.status).toBe("ready");
      expect(result.current.isReady).toBe(true);
      expect(result.current.isMisconfigured).toBe(false);
      expect(result.current.isUnavailable).toBe(false);
      expect(result.current.collectionName).toBe("mcp_context");
      expect(result.current.vectorsCount).toBe(2500);
    });

    it("should return misconfigured status when Qdrant is not configured", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: {
          status: "misconfigured",
          qdrantConnected: false,
          message: "Missing QDRANT_URL configuration",
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.status).toBe("misconfigured");
      expect(result.current.isReady).toBe(false);
      expect(result.current.isMisconfigured).toBe(true);
      expect(result.current.statusMessage).toBe(
        "Missing QDRANT_URL configuration",
      );
    });

    it("should return unavailable status when Qdrant connection fails", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: {
          status: "unavailable",
          qdrantConnected: false,
          collectionName: "mcp_context",
          message: "Unable to connect to Qdrant",
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.status).toBe("unavailable");
      expect(result.current.isReady).toBe(false);
      expect(result.current.isUnavailable).toBe(true);
    });
  });

  // ===========================================================================
  // Error State Tests
  // ===========================================================================

  describe("error state", () => {
    it("should return isError true when request fails", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Network error" },
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBeDefined();
    });

    it("should return undefined status on error", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Server error" },
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.status).toBeUndefined();
      expect(result.current.isReady).toBe(false);
    });
  });

  // ===========================================================================
  // Derived State Tests
  // ===========================================================================

  describe("derived state for UI", () => {
    it("should provide kbStatusForUI for StatusBar integration", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: {
          status: "ready",
          qdrantConnected: true,
          collectionName: "mcp_context",
          vectorsCount: 1500,
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.kbStatusForUI).toBe("ready");
    });

    it("should return undefined kbStatusForUI when loading", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.kbStatusForUI).toBeUndefined();
    });

    it("should provide context stats for display", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: {
          status: "ready",
          qdrantConnected: true,
          collectionName: "mcp_context",
          vectorsCount: 1500,
          contextTokenBudget: 2000,
          contextTopK: 5,
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.contextStats).toEqual({
        refsCount: 5, // contextTopK
        tokensUsed: 0, // Will be populated by actual usage
        tokenBudget: 2000,
      });
    });
  });

  // ===========================================================================
  // Refetch Functionality Tests
  // ===========================================================================

  describe("refetch functionality", () => {
    it("should provide refetch function", () => {
      const mockRefetch = vi.fn();
      mockUseGetKBStatusQuery.mockReturnValue({
        data: { status: "ready", qdrantConnected: true },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: mockRefetch,
      });

      const { result } = renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.refetch).toBe(mockRefetch);
    });
  });

  // ===========================================================================
  // Polling Interval Tests
  // ===========================================================================

  describe("polling interval", () => {
    it("should pass polling interval to query hook", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: { status: "ready", qdrantConnected: true },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      renderHook(() => useKBStatus({ pollingInterval: 60000 }), {
        wrapper: createWrapper(),
      });

      expect(mockUseGetKBStatusQuery).toHaveBeenCalledWith(
        undefined,
        expect.objectContaining({
          pollingInterval: 60000,
        }),
      );
    });

    it("should use default polling interval of 5 minutes", () => {
      mockUseGetKBStatusQuery.mockReturnValue({
        data: { status: "ready", qdrantConnected: true },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      renderHook(() => useKBStatus(), {
        wrapper: createWrapper(),
      });

      expect(mockUseGetKBStatusQuery).toHaveBeenCalledWith(
        undefined,
        expect.objectContaining({
          pollingInterval: 300000, // 5 minutes
        }),
      );
    });
  });
});
