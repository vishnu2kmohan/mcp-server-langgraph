/**
 * useBatchApprovals Hook Tests
 *
 * TDD tests for batch approval API hook.
 *
 * Features:
 * - Batch approve multiple requests
 * - Batch reject multiple requests
 * - Loading states
 * - Error handling
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

// =============================================================================
// Tests
// =============================================================================

describe("useBatchApprovals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Export", () => {
    it("should export useBatchApprovals hook", async () => {
      const module = await import("./useBatchApprovals");
      expect(module.useBatchApprovals).toBeDefined();
    });
  });

  describe("Initial State", () => {
    it("should return initial state with loading false", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const { result } = renderHook(() => useBatchApprovals());

      expect(result.current.isApproving).toBe(false);
      expect(result.current.isRejecting).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe("Batch Approve", () => {
    it("should provide batchApprove function", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const { result } = renderHook(() => useBatchApprovals());

      expect(typeof result.current.batchApprove).toBe("function");
    });

    it("should set isApproving to true during request", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      // Mock fetch
      const mockFetch = vi.fn().mockImplementation(() =>
        new Promise((resolve) => setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ succeeded: 2, failed: 0, results: [] }),
        }), 100))
      );
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useBatchApprovals());

      act(() => {
        result.current.batchApprove(["req-001", "req-002"]);
      });

      expect(result.current.isApproving).toBe(true);

      await waitFor(() => {
        expect(result.current.isApproving).toBe(false);
      });

      vi.unstubAllGlobals();
    });

    it("should call API with correct request body", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ succeeded: 2, failed: 0, results: [] }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useBatchApprovals());

      await act(async () => {
        await result.current.batchApprove(["req-001", "req-002"], "Verified");
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/agents/requests/batch/approve"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            request_ids: ["req-001", "req-002"],
            reason: "Verified",
          }),
        })
      );

      vi.unstubAllGlobals();
    });
  });

  describe("Batch Reject", () => {
    it("should provide batchReject function", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const { result } = renderHook(() => useBatchApprovals());

      expect(typeof result.current.batchReject).toBe("function");
    });

    it("should set isRejecting to true during request", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const mockFetch = vi.fn().mockImplementation(() =>
        new Promise((resolve) => setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ succeeded: 1, failed: 0, results: [] }),
        }), 100))
      );
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useBatchApprovals());

      act(() => {
        result.current.batchReject(["req-001"]);
      });

      expect(result.current.isRejecting).toBe(true);

      await waitFor(() => {
        expect(result.current.isRejecting).toBe(false);
      });

      vi.unstubAllGlobals();
    });
  });

  describe("Error Handling", () => {
    it("should set error on failed request", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useBatchApprovals());

      await act(async () => {
        await result.current.batchApprove(["req-001"]);
      });

      expect(result.current.error).not.toBeNull();

      vi.unstubAllGlobals();
    });

    it("should clear error on subsequent successful request", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const mockFetch = vi.fn()
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ succeeded: 1, failed: 0, results: [] }),
        });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useBatchApprovals());

      // First call fails
      await act(async () => {
        await result.current.batchApprove(["req-001"]);
      });
      expect(result.current.error).not.toBeNull();

      // Second call succeeds
      await act(async () => {
        await result.current.batchApprove(["req-001"]);
      });
      expect(result.current.error).toBeNull();

      vi.unstubAllGlobals();
    });
  });

  describe("Return Values", () => {
    it("should return batch operation results", async () => {
      const { useBatchApprovals } = await import("./useBatchApprovals");

      const mockResponse = {
        succeeded: 2,
        failed: 1,
        results: [
          { request_id: "req-001", success: true, message: "Approved" },
          { request_id: "req-002", success: true, message: "Approved" },
          { request_id: "req-003", success: false, message: "Not found" },
        ],
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useBatchApprovals());

      let response;
      await act(async () => {
        response = await result.current.batchApprove(["req-001", "req-002", "req-003"]);
      });

      expect(response).toEqual(mockResponse);

      vi.unstubAllGlobals();
    });
  });
});
