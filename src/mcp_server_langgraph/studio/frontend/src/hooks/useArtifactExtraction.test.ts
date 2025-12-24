/**
 * useArtifactExtraction Tests
 *
 * TDD tests for the artifact extraction hook that:
 * - Parses streaming content for artifacts
 * - Transforms artifacts to API format
 * - POSTs to /api/v1/artifacts
 * - Triggers revalidation for canvas refresh
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useArtifactExtraction } from "./useArtifactExtraction";

// Mock fetch globally
const mockFetch = vi.fn();

// Mock getAuthToken
vi.mock("../utils/storage", () => ({
  getAuthToken: () => "test-token",
}));

// Mock useRevalidator since we're not in a real Data Router context
// Use vi.hoisted to ensure mockRevalidate is available before vi.mock runs
const { mockRevalidate } = vi.hoisted(() => ({
  mockRevalidate: vi.fn(),
}));

vi.mock("react-router", () => ({
  useRevalidator: () => ({
    revalidate: mockRevalidate,
    state: "idle",
  }),
}));

// =============================================================================
// Tests
// =============================================================================

describe("useArtifactExtraction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set up global fetch mock
    global.fetch = mockFetch;
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ id: "created-artifact-1", version: 1 }),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("artifact extraction", () => {
    it("should extract mermaid artifacts from content", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      const content =
        "Here is a diagram:\n```mermaid\ngraph TD\n    A-->B\n```";

      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      // Should have called fetch to create artifact
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/artifacts",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            Authorization: "Bearer test-token",
          }),
        }),
      );
    });

    it("should extract chart artifacts from content", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      const content =
        '```chart\n{"type": "bar", "data": [{"name": "A", "value": 10}]}\n```';

      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      expect(mockFetch).toHaveBeenCalled();

      // Verify the payload has type "json" (charts are stored as JSON)
      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.type).toBe("json");
    });

    it("should extract code artifacts from content", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      const content = '```python\nprint("hello")\n```';

      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      expect(mockFetch).toHaveBeenCalled();

      // Verify the payload has type "code" and language in edit_metadata
      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.type).toBe("code");
      expect(body.content_type).toBe("code");
      expect(body.edit_metadata?.language).toBe("python");
    });
  });

  describe("deduplication", () => {
    it("should prevent duplicate extraction via content hash tracking", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      const content = "```mermaid\ngraph TD\n    A-->B\n```";

      // Extract twice with same content
      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });
      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      // Should only have called fetch once
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("should reset extraction state with resetExtraction", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      const content = "```mermaid\ngraph TD\n    A-->B\n```";

      // Extract first time
      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      // Reset
      act(() => {
        result.current.resetExtraction();
      });

      // Extract again - should call fetch again
      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe("type transformations", () => {
    it("should transform Artifact to CreateArtifactRequest correctly with API snake_case format", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      const content = "```mermaid\ngraph TD\n    A-->B\n```";

      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      // Verify CreateArtifactRequest matches backend API schema (snake_case)
      // Backend expects: type, content, content_type, session_id, title, edit_metadata
      expect(body).toMatchObject({
        type: "mermaid",
        content: "graph TD\n    A-->B",
        content_type: "mermaid",
        session_id: "test-session",
      });
      // Should NOT have camelCase keys
      expect(body.sessionId).toBeUndefined();
      expect(body.contentType).toBeUndefined();
    });

    it("should serialize non-string artifact data as JSON", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      // Chart artifacts have object data that needs serialization
      const content =
        '```chart\n{"type": "bar", "data": [{"name": "A", "value": 10}]}\n```';

      await act(async () => {
        await result.current.extractAndSaveArtifacts(content);
      });

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      // Content should be a string (serialized JSON)
      expect(typeof body.content).toBe("string");
    });
  });

  describe("API integration", () => {
    it("should POST to /api/v1/artifacts with correct payload", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      await act(async () => {
        await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/artifacts",
        expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            Authorization: "Bearer test-token",
          }),
        }),
      );
    });

    it("should call onArtifactsExtracted callback with count", async () => {
      const onExtracted = vi.fn();

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
          onArtifactsExtracted: onExtracted,
        }),
      );

      await act(async () => {
        await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
      });

      expect(onExtracted).toHaveBeenCalledWith(1);
    });

    it("should handle API errors gracefully", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      // Should not throw
      await act(async () => {
        const count = await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
        expect(count).toBe(0);
      });
    });

    it("should return 0 for invalid sessionId", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "", // Invalid
        }),
      );

      await act(async () => {
        const count = await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
        expect(count).toBe(0);
      });

      // Should not have called fetch
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("content without artifacts", () => {
    it("should return 0 for plain text content", async () => {
      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      await act(async () => {
        const count = await result.current.extractAndSaveArtifacts(
          "Just some plain text without any code blocks",
        );
        expect(count).toBe(0);
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("loading state", () => {
    it("should set isSaving to true during extraction", async () => {
      // Create a delayed fetch to observe the loading state
      let resolvePromise: () => void;
      const delayedPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      mockFetch.mockImplementationOnce(async () => {
        await delayedPromise;
        return { ok: true, json: async () => ({ id: "1" }) };
      });

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
        }),
      );

      // Start extraction (don't await)
      let extractionPromise: Promise<number>;
      act(() => {
        extractionPromise = result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
      });

      // Should be saving
      expect(result.current.isSaving).toBe(true);

      // Resolve the fetch
      await act(async () => {
        resolvePromise!();
        await extractionPromise;
      });

      // Should no longer be saving
      expect(result.current.isSaving).toBe(false);
    });

    it("should call onSavingChange callback when saving state changes", async () => {
      const onSavingChange = vi.fn();

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
          onSavingChange,
        }),
      );

      await act(async () => {
        await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
      });

      // Should have been called with true (start) and false (end)
      expect(onSavingChange).toHaveBeenCalledWith(true);
      expect(onSavingChange).toHaveBeenCalledWith(false);
    });
  });

  describe("retry logic", () => {
    it("should retry failed requests up to maxRetries", async () => {
      // Fail twice, then succeed
      mockFetch
        .mockRejectedValueOnce(new Error("Network error 1"))
        .mockRejectedValueOnce(new Error("Network error 2"))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ id: "1" }),
        });

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
          maxRetries: 3,
        }),
      );

      await act(async () => {
        const count = await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
        expect(count).toBe(1); // Should succeed after retries
      });

      // Should have been called 3 times (2 failures + 1 success)
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it("should give up after maxRetries exceeded", async () => {
      // Fail all retries
      mockFetch.mockRejectedValue(new Error("Persistent network error"));

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
          maxRetries: 2,
        }),
      );

      await act(async () => {
        const count = await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
        expect(count).toBe(0); // Should fail
      });

      // Should have been called maxRetries + 1 times (initial + retries)
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it("should use exponential backoff between retries", async () => {
      vi.useFakeTimers();

      mockFetch
        .mockRejectedValueOnce(new Error("Error 1"))
        .mockRejectedValueOnce(new Error("Error 2"))
        .mockResolvedValueOnce({ ok: true, json: async () => ({ id: "1" }) });

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
          maxRetries: 3,
          retryDelayMs: 100,
        }),
      );

      // Start extraction
      let extractionPromise: Promise<number>;
      act(() => {
        extractionPromise = result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
      });

      // First call happens immediately
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Advance timer for first retry (100ms)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });
      expect(mockFetch).toHaveBeenCalledTimes(2);

      // Advance timer for second retry (200ms - exponential backoff)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });
      expect(mockFetch).toHaveBeenCalledTimes(3);

      // Cleanup
      await act(async () => {
        await extractionPromise;
      });

      vi.useRealTimers();
    });

    it("should call onRetry callback on each retry attempt", async () => {
      const onRetry = vi.fn();

      mockFetch
        .mockRejectedValueOnce(new Error("Error 1"))
        .mockResolvedValueOnce({ ok: true, json: async () => ({ id: "1" }) });

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
          maxRetries: 3,
          retryDelayMs: 0, // No delay for test speed
          onRetry,
        }),
      );

      await act(async () => {
        await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
      });

      expect(onRetry).toHaveBeenCalledWith(1, expect.any(Error));
    });

    it("should default to no retries when maxRetries is 0", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() =>
        useArtifactExtraction({
          sessionId: "test-session",
          maxRetries: 0,
        }),
      );

      await act(async () => {
        const count = await result.current.extractAndSaveArtifacts(
          "```mermaid\ngraph TD\n```",
        );
        expect(count).toBe(0);
      });

      // Should only try once
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });
});
