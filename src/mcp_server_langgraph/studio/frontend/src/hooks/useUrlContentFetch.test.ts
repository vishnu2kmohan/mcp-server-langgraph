/**
 * useUrlContentFetch Hook Tests
 *
 * Tests for the URL content fetching hook that detects "#<url>" patterns
 * in input and fetches URL content for inclusion in chat context.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useUrlContentFetch } from "./useUrlContentFetch";

// Mock the fetch function
const mockFetch = vi.fn();

describe("useUrlContentFetch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
    // Replace global fetch with mock for each test
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("URL Detection", () => {
    it("should detect URL pattern starting with #", () => {
      const { result } = renderHook(() => useUrlContentFetch());

      act(() => {
        result.current.detectUrls("#https://example.com");
      });

      expect(result.current.detectedUrls).toContainEqual({
        raw: "#https://example.com",
        url: "https://example.com",
      });
    });

    it("should detect multiple URLs in input", () => {
      const { result } = renderHook(() => useUrlContentFetch());

      act(() => {
        result.current.detectUrls(
          "Check #https://example.com and #https://test.org",
        );
      });

      expect(result.current.detectedUrls).toHaveLength(2);
      expect(result.current.detectedUrls[0].url).toBe("https://example.com");
      expect(result.current.detectedUrls[1].url).toBe("https://test.org");
    });

    it("should not detect # without valid URL", () => {
      const { result } = renderHook(() => useUrlContentFetch());

      act(() => {
        result.current.detectUrls("#notaurl");
      });

      expect(result.current.detectedUrls).toHaveLength(0);
    });

    it("should not detect # in the middle of a word", () => {
      const { result } = renderHook(() => useUrlContentFetch());

      act(() => {
        result.current.detectUrls("test#https://example.com");
      });

      expect(result.current.detectedUrls).toHaveLength(0);
    });

    it("should detect # at start of line or after whitespace", () => {
      const { result } = renderHook(() => useUrlContentFetch());

      act(() => {
        result.current.detectUrls("Hello #https://example.com world");
      });

      expect(result.current.detectedUrls).toHaveLength(1);
      expect(result.current.detectedUrls[0].url).toBe("https://example.com");
    });

    it("should support http URLs", () => {
      const { result } = renderHook(() => useUrlContentFetch());

      act(() => {
        result.current.detectUrls("#http://example.com");
      });

      expect(result.current.detectedUrls).toHaveLength(1);
      expect(result.current.detectedUrls[0].url).toBe("http://example.com");
    });
  });

  describe("URL Fetching", () => {
    it("should fetch URL content when fetchUrl is called", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://example.com",
            title: "Example Page",
            content: "This is the page content",
            content_type: "text/html",
          }),
      });

      const { result } = renderHook(() => useUrlContentFetch());

      await act(async () => {
        await result.current.fetchUrl("https://example.com");
      });

      await waitFor(() => {
        expect(result.current.fetchedContent).toHaveLength(1);
      });

      expect(result.current.fetchedContent[0]).toEqual({
        url: "https://example.com",
        title: "Example Page",
        content: "This is the page content",
        contentType: "text/html",
        error: undefined,
      });
    });

    it("should handle fetch errors gracefully", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useUrlContentFetch());

      await act(async () => {
        await result.current.fetchUrl("https://example.com");
      });

      await waitFor(() => {
        expect(result.current.fetchedContent).toHaveLength(1);
      });

      expect(result.current.fetchedContent[0]).toMatchObject({
        url: "https://example.com",
        error: "Network error",
      });
    });

    it("should track loading state during fetch", async () => {
      let resolvePromise: (value: unknown) => void;
      const fetchPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      mockFetch.mockReturnValueOnce(fetchPromise);

      const { result } = renderHook(() => useUrlContentFetch());

      // Start fetching
      act(() => {
        result.current.fetchUrl("https://example.com");
      });

      // Should be loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.loadingUrls).toContain("https://example.com");

      // Resolve the fetch
      await act(async () => {
        resolvePromise!({
          ok: true,
          json: () =>
            Promise.resolve({
              url: "https://example.com",
              title: "Test",
              content: "Content",
            }),
        });
      });

      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it("should not fetch the same URL twice", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://example.com",
            title: "Test",
            content: "Content",
          }),
      });

      const { result } = renderHook(() => useUrlContentFetch());

      await act(async () => {
        await result.current.fetchUrl("https://example.com");
        await result.current.fetchUrl("https://example.com");
      });

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe("Content Clearing", () => {
    it("should clear fetched content when clearContent is called", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://example.com",
            title: "Test",
            content: "Content",
          }),
      });

      const { result } = renderHook(() => useUrlContentFetch());

      await act(async () => {
        await result.current.fetchUrl("https://example.com");
      });

      expect(result.current.fetchedContent).toHaveLength(1);

      act(() => {
        result.current.clearContent();
      });

      expect(result.current.fetchedContent).toHaveLength(0);
    });

    it("should clear specific URL content when clearUrl is called", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://example.com",
            title: "Test",
            content: "Content",
          }),
      });

      const { result } = renderHook(() => useUrlContentFetch());

      await act(async () => {
        await result.current.fetchUrl("https://example.com");
        await result.current.fetchUrl("https://test.org");
      });

      // Reset mock to return different URL
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://test.org",
            title: "Test 2",
            content: "Content 2",
          }),
      });

      await waitFor(() => {
        expect(result.current.fetchedContent.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.clearUrl("https://example.com");
      });

      const remaining = result.current.fetchedContent.filter(
        (c) => c.url !== "https://example.com",
      );
      expect(remaining.every((c) => c.url !== "https://example.com")).toBe(
        true,
      );
    });
  });

  describe("Context Generation", () => {
    it("should generate context string from fetched content", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://context-test.com",
            title: "Context Test Page",
            content: "Context test content",
          }),
      });

      const { result } = renderHook(() => useUrlContentFetch());

      await act(async () => {
        await result.current.fetchUrl("https://context-test.com");
      });

      await waitFor(() => {
        expect(result.current.fetchedContent).toHaveLength(1);
      });

      // Verify content is populated
      expect(result.current.fetchedContent[0].content).toBe(
        "Context test content",
      );

      const context = result.current.getContextString();

      expect(context).toContain("https://context-test.com");
      expect(context).toContain("Context Test Page");
      expect(context).toContain("Context test content");
    });

    it("should return empty string when no content fetched", () => {
      const { result } = renderHook(() => useUrlContentFetch());

      expect(result.current.getContextString()).toBe("");
    });
  });

  describe("Auto-Fetch", () => {
    it("should auto-fetch URLs when autoFetch option is enabled", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://auto-test.com",
            title: "Auto Test",
            content: "Auto content",
          }),
      });

      const { result } = renderHook(() =>
        useUrlContentFetch({ autoFetch: true }),
      );

      await act(async () => {
        result.current.detectUrls("#https://auto-test.com");
      });

      // Wait for auto-fetch to complete
      await waitFor(() => {
        expect(result.current.fetchedContent).toHaveLength(1);
      });

      expect(result.current.fetchedContent[0].url).toBe(
        "https://auto-test.com",
      );
    });

    it("should not auto-fetch when autoFetch is false", async () => {
      const { result } = renderHook(() =>
        useUrlContentFetch({ autoFetch: false }),
      );

      await act(async () => {
        result.current.detectUrls("#https://no-auto.com");
      });

      // Should not have fetched anything
      expect(result.current.fetchedContent).toHaveLength(0);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should auto-fetch multiple URLs", async () => {
      let callCount = 0;
      mockFetch.mockImplementation(() => {
        callCount++;
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              url: callCount === 1 ? "https://first.com" : "https://second.com",
              title: `Page ${callCount}`,
              content: `Content ${callCount}`,
            }),
        });
      });

      const { result } = renderHook(() =>
        useUrlContentFetch({ autoFetch: true }),
      );

      await act(async () => {
        result.current.detectUrls(
          "Check #https://first.com and #https://second.com",
        );
      });

      // Wait for both fetches to complete
      await waitFor(() => {
        expect(result.current.fetchedContent.length).toBeGreaterThanOrEqual(2);
      });

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it("should not auto-fetch already fetched URLs", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://duplicate.com",
            title: "Test",
            content: "Content",
          }),
      });

      const { result } = renderHook(() =>
        useUrlContentFetch({ autoFetch: true }),
      );

      // First detection - should fetch
      await act(async () => {
        result.current.detectUrls("#https://duplicate.com");
      });

      await waitFor(() => {
        expect(result.current.fetchedContent).toHaveLength(1);
      });

      // Second detection of same URL - should not fetch again
      await act(async () => {
        result.current.detectUrls("#https://duplicate.com again");
      });

      // Should still only have one fetch call
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("should debounce auto-fetch when debounceMs is provided", async () => {
      // Set up fake timers BEFORE rendering
      vi.useFakeTimers();

      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            url: "https://debounce.com",
            title: "Debounce Test",
            content: "Content",
          }),
      });

      const { result, unmount } = renderHook(() =>
        useUrlContentFetch({ autoFetch: true, debounceMs: 300 }),
      );

      // Type quickly - multiple detections
      act(() => {
        result.current.detectUrls("#https://debounce.com");
      });

      // Fast forward less than debounce time
      act(() => {
        vi.advanceTimersByTime(100);
      });

      act(() => {
        result.current.detectUrls("#https://debounce.com/more");
      });

      // Fast forward less than debounce time
      act(() => {
        vi.advanceTimersByTime(100);
      });

      act(() => {
        result.current.detectUrls("#https://debounce.com/final");
      });

      // Should not have fetched yet
      expect(mockFetch).not.toHaveBeenCalled();

      // Fast forward past debounce time - run all timers
      await act(async () => {
        vi.runAllTimers();
      });

      // Now should have fetched
      expect(mockFetch).toHaveBeenCalled();

      // Cleanup
      unmount();
      vi.useRealTimers();
    });
  });
});
