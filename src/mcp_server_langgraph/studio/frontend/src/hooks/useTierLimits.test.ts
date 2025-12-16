/**
 * useTierLimits Hook Tests
 *
 * TDD tests for the tier limits hook.
 * Tests cover:
 * - Tier-based limits calculation
 * - Session counting
 * - Approaching/at limit detection
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import React from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useTierLimits } from "./useTierLimits";

// Mock the api module
vi.mock("../api", () => ({
  useListSessionsQuery: vi.fn(),
  api: {
    reducerPath: "api",
    reducer: () => ({}),
    middleware:
      () => (next: (action: unknown) => unknown) => (action: unknown) =>
        next(action),
  },
}));

import { useListSessionsQuery } from "../api";

// Create a minimal test store
const createTestStore = (authState: {
  currentOrg: { tier: string } | null;
}) => {
  return configureStore({
    reducer: {
      auth: () => authState,
      api: () => ({}),
    },
  });
};

// Wrapper component for tests
const createWrapper = (authState: { currentOrg: { tier: string } | null }) => {
  const store = createTestStore(authState);
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(Provider, { store }, children);
};

describe("useTierLimits", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Tier Limits", () => {
    it("should return 5 session limit for shared tier", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.maxSessions).toBe(5);
    });

    it("should return 20 session limit for hybrid tier", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "hybrid" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.maxSessions).toBe(20);
    });

    it("should return -1 (unlimited) session limit for dedicated tier", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "dedicated" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.maxSessions).toBe(-1);
    });
  });

  describe("Current Usage", () => {
    it("should return current session count", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [{}, {}, {}], total: 3 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.activeSessions).toBe(3);
    });

    it("should return 0 when no sessions", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.activeSessions).toBe(0);
    });
  });

  describe("Limit Status", () => {
    it("should indicate approaching limit at 80%", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [{}, {}, {}, {}], total: 4 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.isApproachingLimit).toBe(true);
    });

    it("should not indicate approaching limit below 80%", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [{}, {}], total: 2 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.isApproachingLimit).toBe(false);
    });

    it("should indicate at limit when at max", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [{}, {}, {}, {}, {}], total: 5 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.isAtLimit).toBe(true);
    });

    it("should never indicate approaching/at limit for unlimited tier", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: Array(100).fill({}), total: 100 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "dedicated" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.isApproachingLimit).toBe(false);
      expect(result.current.isAtLimit).toBe(false);
    });
  });

  describe("Tier Info", () => {
    it("should return current tier name", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "hybrid" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.tier).toBe("hybrid");
    });

    it("should suggest next tier for upgrade", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.nextTier).toBe("hybrid");
    });

    it("should suggest dedicated tier when on hybrid", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "hybrid" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.nextTier).toBe("dedicated");
    });

    it("should return null next tier when on dedicated", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "dedicated" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.nextTier).toBeNull();
    });
  });

  describe("Loading State", () => {
    it("should indicate loading when sessions are loading", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: undefined,
        isLoading: true,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: { tier: "shared" },
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });
  });

  describe("Default Values", () => {
    it("should use shared tier limits when no org is set", () => {
      vi.mocked(useListSessionsQuery).mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
      } as ReturnType<typeof useListSessionsQuery>);

      const wrapper = createWrapper({
        currentOrg: null,
      });

      const { result } = renderHook(() => useTierLimits(), { wrapper });

      expect(result.current.maxSessions).toBe(5);
      expect(result.current.tier).toBe("shared");
    });
  });
});
