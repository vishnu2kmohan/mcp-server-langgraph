/**
 * useProjectContext Tests
 *
 * TDD tests for the Project Context hook.
 * Tests cover:
 * - Loading project context from API
 * - Context active/inactive states
 * - Updating context content
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useProjectContext } from "./useProjectContext";

describe("useProjectContext", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    fetchSpy = vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  describe("loading state", () => {
    it("should start with loading state", () => {
      fetchSpy.mockImplementation(() => new Promise(() => {}));
      const { result } = renderHook(() => useProjectContext());

      expect(result.current.isLoading).toBe(true);
    });

    it("should set loading to false after fetch completes", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ exists: false }),
      } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  describe("context detection", () => {
    it("should detect when project context exists", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            exists: true,
            content: "# Project Context\nThis is a test project.",
            path: ".studio/context.md",
          }),
      } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.hasContext).toBe(true);
        expect(result.current.content).toBe(
          "# Project Context\nThis is a test project.",
        );
      });
    });

    it("should detect when project context does not exist", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ exists: false }),
      } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.hasContext).toBe(false);
        expect(result.current.content).toBeNull();
      });
    });
  });

  describe("context path", () => {
    it("should return the context file path when exists", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            exists: true,
            content: "Test",
            path: ".studio/context.md",
          }),
      } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.contextPath).toBe(".studio/context.md");
      });
    });
  });

  describe("updating context", () => {
    it("should update context content", async () => {
      fetchSpy
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              exists: true,
              content: "Original content",
              path: ".studio/context.md",
            }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.content).toBe("Original content");
      });

      await act(async () => {
        await result.current.updateContent("New content");
      });

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/context"),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ content: "New content" }),
        }),
      );
    });
  });

  describe("creating context", () => {
    it("should create new context file", async () => {
      fetchSpy
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ exists: false }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              path: ".studio/context.md",
            }),
        } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.hasContext).toBe(false);
      });

      await act(async () => {
        await result.current.createContext("# New Project\nDescription here.");
      });

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/context"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ content: "# New Project\nDescription here." }),
        }),
      );
    });
  });

  describe("error handling", () => {
    it("should handle fetch errors gracefully", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.error).toBe("Failed to load project context");
        expect(result.current.isLoading).toBe(false);
      });
    });

    it("should handle non-OK responses", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.error).toBe("Failed to load project context");
      });
    });
  });

  describe("refresh", () => {
    it("should refresh context data", async () => {
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            exists: true,
            content: "Refreshed content",
            path: ".studio/context.md",
          }),
      } as Response);

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.content).toBe("Refreshed content");
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });
  });
});
