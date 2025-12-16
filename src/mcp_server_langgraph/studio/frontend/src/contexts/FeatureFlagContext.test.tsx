/**
 * FeatureFlagContext Tests
 *
 * TDD tests for the feature flags context and hook.
 * Tests cover:
 * - Provider initialization
 * - Hook usage
 * - Feature flag checking
 * - Loading states
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import React from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import {
  FeatureFlagProvider,
  useFeatureFlags,
  useFeatureFlag,
} from "./FeatureFlagContext";

// Mock the api module
vi.mock("../api", () => ({
  useGetFeatureFlagsQuery: vi.fn(),
  api: {
    reducerPath: "api",
    reducer: () => ({}),
    middleware:
      () => (next: (action: unknown) => unknown) => (action: unknown) =>
        next(action),
  },
}));

import { useGetFeatureFlagsQuery } from "../api";

// Create a minimal test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      api: () => ({}),
    },
  });
};

// Wrapper component for tests
const createWrapper = () => {
  const store = createTestStore();
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      Provider,
      { store },
      React.createElement(FeatureFlagProvider, null, children),
    );
};

describe("FeatureFlagContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useFeatureFlags", () => {
    it("should return all feature flags", async () => {
      const mockFlags = {
        workflows: true,
        sessions: true,
        cost_dashboard: false,
        observability: true,
        code_export: true,
        ai_suggestions: true,
        mcp_websocket: false,
      };

      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: mockFlags,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      expect(result.current.flags).toEqual(mockFlags);
    });

    it("should return loading state", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });

    it("should return error state", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      expect(result.current.isError).toBe(true);
    });
  });

  describe("useFeatureFlag", () => {
    it("should return true for enabled feature", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: { workflows: true },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlag("workflows"), {
        wrapper,
      });

      expect(result.current).toBe(true);
    });

    it("should return false for disabled feature", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: { cost_dashboard: false },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlag("cost_dashboard"), {
        wrapper,
      });

      expect(result.current).toBe(false);
    });

    it("should return false for unknown feature", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: { workflows: true },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlag("unknown_feature"), {
        wrapper,
      });

      expect(result.current).toBe(false);
    });

    it("should return false while loading", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlag("workflows"), {
        wrapper,
      });

      expect(result.current).toBe(false);
    });

    it("should return false on error", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlag("workflows"), {
        wrapper,
      });

      expect(result.current).toBe(false);
    });
  });

  describe("FeatureFlagProvider", () => {
    it("should provide context to children", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: { test_feature: true },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlag("test_feature"), {
        wrapper,
      });

      expect(result.current).toBe(true);
    });
  });

  describe("Default values", () => {
    it("should provide default empty flags when data is undefined", () => {
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      expect(result.current.flags).toEqual({});
    });
  });
});
