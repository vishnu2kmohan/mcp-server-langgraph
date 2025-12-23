/**
 * useRetryableRequest Hook Tests
 *
 * Tests the hook for making retryable HTTP requests with exponential backoff.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useRetryableRequest } from "./useRetryableRequest";

describe("useRetryableRequest", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should return initial state", () => {
      const { result } = renderHook(() => useRetryableRequest());

      expect(result.current.status).toBe("idle");
      expect(result.current.data).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.retryCount).toBe(0);
      expect(result.current.isRetrying).toBe(false);
    });

    it("should expose execute function", () => {
      const { result } = renderHook(() => useRetryableRequest());

      expect(typeof result.current.execute).toBe("function");
    });

    it("should expose cancel function", () => {
      const { result } = renderHook(() => useRetryableRequest());

      expect(typeof result.current.cancel).toBe("function");
    });

    it("should expose forceRetry function", () => {
      const { result } = renderHook(() => useRetryableRequest());

      expect(typeof result.current.forceRetry).toBe("function");
    });

    it("should expose getNextRetryDelay function", () => {
      const { result } = renderHook(() => useRetryableRequest());

      expect(typeof result.current.getNextRetryDelay).toBe("function");
    });
  });

  describe("forceRetry", () => {
    it("should do nothing when no request has been made", () => {
      const { result } = renderHook(() => useRetryableRequest());

      // forceRetry when no request fn exists should be a no-op
      act(() => {
        result.current.forceRetry();
      });

      expect(result.current.status).toBe("idle");
    });

    it("should do nothing when cancelled", async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() =>
        useRetryableRequest({ baseDelayMs: 100, maxRetries: 3 }),
      );

      // Start a request that will fail and schedule retry
      act(() => {
        result.current.execute(mockFetch);
      });

      // Wait for error and retry state
      await waitFor(() => {
        expect(result.current.isRetrying).toBe(true);
      });

      // Cancel
      act(() => {
        result.current.cancel();
      });

      // forceRetry should do nothing when cancelled
      act(() => {
        result.current.forceRetry();
      });

      expect(result.current.status).toBe("cancelled");
    });
  });

  describe("successful request", () => {
    it("should set status to loading during request", async () => {
      let resolvePromise: (value: unknown) => void;
      const mockFetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            resolvePromise = resolve;
          }),
      );

      const { result } = renderHook(() => useRetryableRequest());

      act(() => {
        result.current.execute(mockFetch);
      });

      expect(result.current.status).toBe("loading");

      // Clean up: resolve and wait for state update
      await act(async () => {
        resolvePromise!({ data: "success" });
      });
    });

    it("should set data on successful response", async () => {
      const mockFetch = vi.fn().mockResolvedValue({ data: "success" });

      const { result } = renderHook(() => useRetryableRequest());

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      expect(result.current.status).toBe("success");
      expect(result.current.data).toEqual({ data: "success" });
      expect(result.current.error).toBeNull();
    });

    it("should reset retry count on success", async () => {
      const mockFetch = vi.fn().mockResolvedValue({ data: "success" });

      const { result } = renderHook(() => useRetryableRequest());

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      expect(result.current.retryCount).toBe(0);
    });
  });

  describe("failed request", () => {
    it("should set error on non-retryable failure", async () => {
      // Authentication errors are not retryable
      const authError = new Error("Unauthorized");
      (authError as Error & { status?: number }).status = 401;

      const mockFetch = vi.fn().mockRejectedValue(authError);

      const { result } = renderHook(() => useRetryableRequest());

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      expect(result.current.status).toBe("error");
      expect(result.current.error).not.toBeNull();
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("should classify error correctly", async () => {
      const validationError = new Error("Validation failed");

      const mockFetch = vi.fn().mockRejectedValue(validationError);

      const { result } = renderHook(() => useRetryableRequest());

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      expect(result.current.error).not.toBeNull();
      expect(result.current.error?.message).toContain("Validation failed");
    });
  });

  describe("cancel", () => {
    it("should cancel pending request", async () => {
      let _resolvePromise: (value: unknown) => void;
      const mockFetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            _resolvePromise = resolve;
          }),
      );

      const { result } = renderHook(() => useRetryableRequest());

      act(() => {
        result.current.execute(mockFetch);
      });

      expect(result.current.status).toBe("loading");

      act(() => {
        result.current.cancel();
      });

      expect(result.current.status).toBe("cancelled");
    });

    it("should return null when cancelled during request execution", async () => {
      let resolvePromise: (value: unknown) => void;
      const mockFetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            resolvePromise = resolve;
          }),
      );

      const { result } = renderHook(() => useRetryableRequest());

      let executeResult: unknown;
      act(() => {
        result.current.execute(mockFetch).then((r) => {
          executeResult = r;
        });
      });

      expect(result.current.status).toBe("loading");

      // Cancel while request is in flight
      act(() => {
        result.current.cancel();
      });

      // Resolve the promise after cancellation
      await act(async () => {
        resolvePromise!({ data: "should be ignored" });
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.status).toBe("cancelled");
      expect(executeResult).toBeNull();
    });

    it("should cancel during retry timeout", async () => {
      const networkError = new Error("Network error");
      const mockFetch = vi.fn().mockRejectedValue(networkError);

      const { result } = renderHook(() =>
        useRetryableRequest({ baseDelayMs: 100, maxRetries: 3 }),
      );

      act(() => {
        result.current.execute(mockFetch);
      });

      // Wait for retry state (after first failure, before retry executes)
      await waitFor(() => {
        expect(result.current.isRetrying).toBe(true);
      });

      // Cancel during retry timeout
      act(() => {
        result.current.cancel();
      });

      expect(result.current.status).toBe("cancelled");
      expect(result.current.isRetrying).toBe(false);
    });
  });

  describe("getNextRetryDelay", () => {
    it("should return 0 when no retry pending", () => {
      const { result } = renderHook(() => useRetryableRequest());

      expect(result.current.getNextRetryDelay()).toBe(0);
    });
  });

  describe("config options", () => {
    it("should accept custom maxRetries option", () => {
      const { result } = renderHook(() =>
        useRetryableRequest({ maxRetries: 5 }),
      );

      expect(result.current.status).toBe("idle");
    });

    it("should accept custom baseDelayMs option", () => {
      const { result } = renderHook(() =>
        useRetryableRequest({ baseDelayMs: 500 }),
      );

      expect(result.current.status).toBe("idle");
    });

    it("should call onSuccess callback", async () => {
      const onSuccess = vi.fn();
      const mockFetch = vi.fn().mockResolvedValue({ data: "success" });

      const { result } = renderHook(() => useRetryableRequest({ onSuccess }));

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      expect(onSuccess).toHaveBeenCalledWith({ data: "success" });
    });

    it("should call onError callback on final failure", async () => {
      const onError = vi.fn();
      const mockFetch = vi.fn().mockRejectedValue(new Error("Failed"));

      const { result } = renderHook(() =>
        useRetryableRequest({ onError, maxRetries: 0 }),
      );

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      expect(onError).toHaveBeenCalled();
    });
  });

  describe("retry behavior (with short delays)", () => {
    it("should retry and eventually succeed", async () => {
      const networkError = new Error("Network error");
      const mockFetch = vi
        .fn()
        .mockRejectedValueOnce(networkError)
        .mockResolvedValue({ data: "success" });

      const { result } = renderHook(() =>
        useRetryableRequest({ baseDelayMs: 10, maxRetries: 2 }),
      );

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      // Should eventually succeed after retry
      await waitFor(
        () => {
          expect(result.current.status).toBe("success");
        },
        { timeout: 5000 },
      );

      expect(result.current.data).toEqual({ data: "success" });
    }, 10000);

    it("should track retry count during retries", async () => {
      const networkError = new Error("Network error");
      const mockFetch = vi
        .fn()
        .mockRejectedValueOnce(networkError)
        .mockResolvedValue({ data: "success" });

      const onRetry = vi.fn();
      const { result } = renderHook(() =>
        useRetryableRequest({ baseDelayMs: 10, maxRetries: 2, onRetry }),
      );

      await act(async () => {
        await result.current.execute(mockFetch);
      });

      await waitFor(
        () => {
          expect(result.current.status).toBe("success");
        },
        { timeout: 5000 },
      );

      // onRetry should have been called once (for the retry)
      expect(onRetry).toHaveBeenCalledTimes(1);
    }, 10000);
  });
});
