/**
 * useProjectContext Tests
 *
 * TDD tests for the Project Context hook.
 * Tests cover:
 * - Loading project context from API
 * - Context active/inactive states
 * - Updating context content
 * - Error handling
 * - Authentication with authenticatedFetch
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";

// Mock react-router
const mockNavigate = vi.fn();
vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock authenticatedFetch
const mockAuthenticatedFetch = vi.fn();
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: (...args: unknown[]) => mockAuthenticatedFetch(...args),
}));

// Mock intendedRoute
const mockSetIntendedRoute = vi.fn();
vi.mock("../utils/intendedRoute", () => ({
  setIntendedRoute: (...args: unknown[]) => mockSetIntendedRoute(...args),
}));

import { useProjectContext } from "./useProjectContext";

describe("useProjectContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default successful response
    mockAuthenticatedFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ exists: false }),
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("loading state", () => {
    it("should start with loading state", () => {
      mockAuthenticatedFetch.mockImplementation(() => new Promise(() => {}));
      const { result } = renderHook(() => useProjectContext());

      expect(result.current.isLoading).toBe(true);
    });

    it("should set loading to false after fetch completes", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
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
      mockAuthenticatedFetch.mockResolvedValueOnce({
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
      mockAuthenticatedFetch.mockResolvedValueOnce({
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
      mockAuthenticatedFetch.mockResolvedValueOnce({
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
      mockAuthenticatedFetch
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

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
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
      mockAuthenticatedFetch
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

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
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
      mockAuthenticatedFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useProjectContext());

      await waitFor(() => {
        expect(result.current.error).toBe("Failed to load project context");
        expect(result.current.isLoading).toBe(false);
      });
    });

    it("should handle non-OK responses", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
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
      mockAuthenticatedFetch.mockResolvedValue({
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

      expect(mockAuthenticatedFetch).toHaveBeenCalledTimes(2);
    });
  });
});
