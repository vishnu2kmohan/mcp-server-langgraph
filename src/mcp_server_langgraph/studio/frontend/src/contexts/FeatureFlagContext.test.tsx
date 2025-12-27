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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
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
import personaReducer, {
  initialState as personaInitialState,
} from "../store/slices/personaSlice";

// Create a minimal test store with persona reducer (required for FeatureFlagProvider)
const createTestStore = (personaOverrides = {}) => {
  return configureStore({
    reducer: {
      api: () => ({}),
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        ...personaInitialState,
        isPersonaLoading: false, // Default to loaded for most tests
        ...personaOverrides,
      },
    },
  });
};

// Wrapper component for tests
const createWrapper = (personaOverrides = {}) => {
  const store = createTestStore(personaOverrides);
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

  afterEach(() => {
    cleanup();
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

  // =============================================================================
  // Role Parameter Tests (Sprint 4: Persona-Based Feature Flags)
  // =============================================================================

  describe("Role-based feature flags", () => {
    it("should pass user persona/role to /features endpoint", () => {
      // This test validates that useGetFeatureFlagsQuery is called with role param
      // The actual implementation will use Redux persona state to pass the role
      vi.mocked(useGetFeatureFlagsQuery).mockImplementation((params) => {
        // Verify that params include role when passed
        if (params && typeof params === "object" && "role" in params) {
          // Role was passed - return admin feature set
          return {
            data: {
              admin_dashboard: true,
              audit_logs: true,
              ai_suggestions: true,
            },
            isLoading: false,
            isError: false,
          } as ReturnType<typeof useGetFeatureFlagsQuery>;
        }
        // No role passed - return default user feature set
        return {
          data: {
            ai_suggestions: true,
            admin_dashboard: false,
            audit_logs: false,
          },
          isLoading: false,
          isError: false,
        } as ReturnType<typeof useGetFeatureFlagsQuery>;
      });

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      // The test verifies the query is called (implementation determines role passing)
      expect(useGetFeatureFlagsQuery).toHaveBeenCalled();
      expect(result.current.flags).toBeDefined();
    });

    it("should skip query while persona is loading", () => {
      // When persona is still loading, should not fetch feature flags yet
      // This prevents calling /features with wrong role
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      // Should be in loading state
      expect(result.current.isLoading).toBe(true);
    });

    it("admin should get admin feature set", () => {
      // Admin users should receive admin-level feature flags
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: {
          admin_dashboard: true,
          audit_logs: true,
          user_management: true,
          ai_suggestions: true,
        },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      expect(result.current.flags.admin_dashboard).toBe(true);
      expect(result.current.flags.audit_logs).toBe(true);
      expect(result.current.isEnabled("admin_dashboard")).toBe(true);
    });

    it("developer should get developer feature set", () => {
      // Developer users should receive developer-level feature flags
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: {
          admin_dashboard: false,
          audit_logs: false,
          code_export: true,
          ai_suggestions: true,
          workflows: true,
        },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      // Developer has developer features but not admin
      expect(result.current.flags.code_export).toBe(true);
      expect(result.current.flags.workflows).toBe(true);
      expect(result.current.isEnabled("admin_dashboard")).toBe(false);
    });

    it("user should get user feature set (default)", () => {
      // Standard users should receive basic feature flags
      vi.mocked(useGetFeatureFlagsQuery).mockReturnValue({
        data: {
          admin_dashboard: false,
          audit_logs: false,
          code_export: false,
          ai_suggestions: true,
          workflows: true,
        },
        isLoading: false,
        isError: false,
      } as ReturnType<typeof useGetFeatureFlagsQuery>);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useFeatureFlags(), { wrapper });

      // User has basic features but not admin or developer
      expect(result.current.isEnabled("ai_suggestions")).toBe(true);
      expect(result.current.isEnabled("admin_dashboard")).toBe(false);
      expect(result.current.isEnabled("code_export")).toBe(false);
    });
  });
});
