/**
 * useNativeCapabilities Hook Tests
 *
 * TDD: These tests are written FIRST to define the expected behavior
 * of the useNativeCapabilities hook for native tool capability detection.
 *
 * Tests verify:
 * 1. Hook fetches native capabilities for a model from API
 * 2. Returns loading state
 * 3. Returns capabilities data (web_search, code_execution)
 * 4. Provides convenience booleans (supportsWebSearch, supportsCodeExecution)
 * 5. Returns error state on failure
 * 6. Provides refetch function
 * 7. Handles unsupported models gracefully
 * 8. Skips fetching when skip option is true
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { useNativeCapabilities } from "./useNativeCapabilities";
import type { NativeToolCapabilityCamelCase } from "../types/tools";

// Mock the RTK Query endpoint
vi.mock("../api", () => ({
  useGetNativeCapabilitiesQuery: vi.fn(),
}));

import { useGetNativeCapabilitiesQuery } from "../api";

const mockUseGetNativeCapabilitiesQuery =
  useGetNativeCapabilitiesQuery as ReturnType<typeof vi.fn>;

// Sample capability data for tests
const mockAnthropicCapabilities: NativeToolCapabilityCamelCase[] = [
  {
    toolName: "web_search",
    supported: true,
    providerType: "web_search_20250305",
    enabled: true,
  },
  {
    toolName: "code_execution",
    supported: true,
    providerType: "code_execution_20250825",
    enabled: true,
  },
];

const mockGoogleCapabilities: NativeToolCapabilityCamelCase[] = [
  {
    toolName: "web_search",
    supported: true,
    providerType: "googleSearch",
    enabled: true,
  },
  {
    toolName: "code_execution",
    supported: false,
    providerType: null,
    enabled: false,
  },
];

const mockDisabledCapabilities: NativeToolCapabilityCamelCase[] = [
  {
    toolName: "web_search",
    supported: true,
    providerType: "web_search_20250305",
    enabled: false, // Feature flag disabled
  },
  {
    toolName: "code_execution",
    supported: true,
    providerType: "code_execution_20250825",
    enabled: false, // Feature flag disabled
  },
];

describe("useNativeCapabilities", () => {
  // Create a minimal Redux store wrapper
  const createWrapper = () => {
    const store = configureStore({
      reducer: {
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
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isFetching: true,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(true);
      expect(result.current.capabilities).toEqual([]);
    });

    it("should return isLoading false after data loads", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.capabilities).toHaveLength(2);
    });
  });

  // ===========================================================================
  // Data Fetching Tests
  // ===========================================================================

  describe("data fetching", () => {
    it("should return capabilities for Anthropic model", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.capabilities).toHaveLength(2);
      expect(result.current.nativeProvider).toBe("anthropic");
      expect(result.current.masterEnabled).toBe(true);
    });

    it("should return capabilities for Google model", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "gemini-2.0-flash",
          nativeProvider: "google",
          capabilities: mockGoogleCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "gemini-2.0-flash" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.nativeProvider).toBe("google");
      expect(result.current.supportsWebSearch).toBe(true);
      expect(result.current.supportsCodeExecution).toBe(false);
    });

    it("should skip fetching when skip option is true", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      renderHook(
        () =>
          useNativeCapabilities({
            modelId: "claude-sonnet-4-20250514",
            skip: true,
          }),
        { wrapper: createWrapper() },
      );

      expect(mockUseGetNativeCapabilitiesQuery).toHaveBeenCalledWith(
        { modelId: "claude-sonnet-4-20250514" },
        { skip: true },
      );
    });

    it("should skip fetching when modelId is empty", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      renderHook(() => useNativeCapabilities({ modelId: "" }), {
        wrapper: createWrapper(),
      });

      expect(mockUseGetNativeCapabilitiesQuery).toHaveBeenCalledWith(
        { modelId: "" },
        { skip: true },
      );
    });
  });

  // ===========================================================================
  // Convenience Boolean Tests
  // ===========================================================================

  describe("convenience booleans", () => {
    it("should return supportsWebSearch true when web_search is supported and enabled", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.supportsWebSearch).toBe(true);
    });

    it("should return supportsCodeExecution true when code_execution is supported and enabled", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.supportsCodeExecution).toBe(true);
    });

    it("should return supportsCodeExecution false when code_execution is not supported", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "gemini-2.0-flash",
          nativeProvider: "google",
          capabilities: mockGoogleCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "gemini-2.0-flash" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.supportsCodeExecution).toBe(false);
    });

    it("should return hasNativeTools true when any capability is supported and enabled", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.hasNativeTools).toBe(true);
    });

    it("should return hasNativeTools false when masterEnabled is false", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: false, // Master switch off
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.hasNativeTools).toBe(false);
    });

    it("should return false for capabilities when feature flags are disabled", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockDisabledCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      // Supported but NOT enabled
      expect(result.current.supportsWebSearch).toBe(false);
      expect(result.current.supportsCodeExecution).toBe(false);
      expect(result.current.hasNativeTools).toBe(false);
    });
  });

  // ===========================================================================
  // Tool Availability Helper Tests
  // ===========================================================================

  describe("isToolAvailable helper", () => {
    it("should return true for available tool", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isToolAvailable("web_search")).toBe(true);
      expect(result.current.isToolAvailable("code_execution")).toBe(true);
    });

    it("should return false for unavailable tool", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "gemini-2.0-flash",
          nativeProvider: "google",
          capabilities: mockGoogleCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "gemini-2.0-flash" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isToolAvailable("code_execution")).toBe(false);
    });

    it("should return false for unknown tool", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isToolAvailable("unknown_tool")).toBe(false);
    });

    it("should return false when masterEnabled is false", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: false,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isToolAvailable("web_search")).toBe(false);
    });
  });

  // ===========================================================================
  // Get Capability Helper Tests
  // ===========================================================================

  describe("getCapability helper", () => {
    it("should return capability for known tool", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      const cap = result.current.getCapability("web_search");
      expect(cap).toBeDefined();
      expect(cap?.providerType).toBe("web_search_20250305");
    });

    it("should return undefined for unknown tool", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      const cap = result.current.getCapability("unknown_tool");
      expect(cap).toBeUndefined();
    });
  });

  // ===========================================================================
  // Error State Tests
  // ===========================================================================

  describe("error state", () => {
    it("should return isError true on failure", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        error: { status: 500, data: "Internal Server Error" },
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBeDefined();
    });

    it("should return empty capabilities on error", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        error: { status: 500, data: "Internal Server Error" },
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.capabilities).toEqual([]);
      expect(result.current.supportsWebSearch).toBe(false);
      expect(result.current.supportsCodeExecution).toBe(false);
    });
  });

  // ===========================================================================
  // Refetch Tests
  // ===========================================================================

  describe("refetch", () => {
    it("should provide refetch function", () => {
      const mockRefetch = vi.fn();
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "claude-sonnet-4-20250514",
          nativeProvider: "anthropic",
          capabilities: mockAnthropicCapabilities,
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: mockRefetch,
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.refetch).toBe(mockRefetch);
    });
  });

  // ===========================================================================
  // Unsupported Model Tests
  // ===========================================================================

  describe("unsupported models", () => {
    it("should handle model with no native support", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "gpt-4",
          nativeProvider: null,
          capabilities: [],
          masterEnabled: true,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "gpt-4" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.nativeProvider).toBeNull();
      expect(result.current.capabilities).toEqual([]);
      expect(result.current.supportsWebSearch).toBe(false);
      expect(result.current.supportsCodeExecution).toBe(false);
      expect(result.current.hasNativeTools).toBe(false);
    });

    it("should handle unknown model gracefully", () => {
      mockUseGetNativeCapabilitiesQuery.mockReturnValue({
        data: {
          modelId: "unknown-model-xyz",
          nativeProvider: null,
          capabilities: [],
          masterEnabled: false,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useNativeCapabilities({ modelId: "unknown-model-xyz" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.isError).toBe(false);
      expect(result.current.hasNativeTools).toBe(false);
    });
  });
});
