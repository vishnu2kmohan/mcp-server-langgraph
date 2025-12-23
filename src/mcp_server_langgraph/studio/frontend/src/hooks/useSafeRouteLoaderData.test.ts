/**
 * useSafeRouteLoaderData Tests
 *
 * Tests for the safe wrapper around useRouteLoaderData that handles
 * cases where the component is not within a data router context.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { createElement } from "react";
import { UNSAFE_DataRouterContext } from "react-router";
import {
  useIsDataRouter,
  useSafeRouteLoaderData,
} from "./useSafeRouteLoaderData";

// Helper to wrap hook in DataRouterContext
const createWrapper = (contextValue: unknown) => {
  return ({ children }: { children: React.ReactNode }) =>
    createElement(
      UNSAFE_DataRouterContext.Provider,
      { value: contextValue },
      children,
    );
};

describe("useSafeRouteLoaderData", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("useIsDataRouter", () => {
    it("should return false when not in a data router context", () => {
      // GIVEN: No data router context (null)
      const wrapper = createWrapper(null);

      // WHEN: Calling useIsDataRouter
      const { result } = renderHook(() => useIsDataRouter(), { wrapper });

      // THEN: Should return false
      expect(result.current).toBe(false);
    });

    it("should return true when in a data router context", () => {
      // GIVEN: A valid data router context
      const mockContext = {
        router: {
          state: {
            loaderData: {},
          },
        },
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useIsDataRouter
      const { result } = renderHook(() => useIsDataRouter(), { wrapper });

      // THEN: Should return true
      expect(result.current).toBe(true);
    });

    it("should return true when context exists but router is empty", () => {
      // GIVEN: A context object without router (edge case)
      const mockContext = {};
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useIsDataRouter
      const { result } = renderHook(() => useIsDataRouter(), { wrapper });

      // THEN: Should return true (context is not null)
      expect(result.current).toBe(true);
    });
  });

  describe("useSafeRouteLoaderData", () => {
    it("should return undefined when not in a data router context", () => {
      // GIVEN: No data router context (null)
      const wrapper = createWrapper(null);

      // WHEN: Calling useSafeRouteLoaderData
      const { result } = renderHook(
        () => useSafeRouteLoaderData<{ data: string }>("test-route"),
        { wrapper },
      );

      // THEN: Should return undefined
      expect(result.current).toBeUndefined();
    });

    it("should return undefined when router state is missing", () => {
      // GIVEN: Context without router.state
      const mockContext = {
        router: {},
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData
      const { result } = renderHook(
        () => useSafeRouteLoaderData<{ data: string }>("test-route"),
        { wrapper },
      );

      // THEN: Should return undefined
      expect(result.current).toBeUndefined();
    });

    it("should return undefined when router is missing", () => {
      // GIVEN: Context without router
      const mockContext = {};
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData
      const { result } = renderHook(
        () => useSafeRouteLoaderData<{ data: string }>("test-route"),
        { wrapper },
      );

      // THEN: Should return undefined
      expect(result.current).toBeUndefined();
    });

    it("should return loader data when route ID exists", () => {
      // GIVEN: Valid context with loader data for the route
      const mockLoaderData = { sessions: [{ id: "1" }], artifacts: [] };
      const mockContext = {
        router: {
          state: {
            loaderData: {
              "studio-v2": mockLoaderData,
            },
          },
        },
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData with matching route ID
      const { result } = renderHook(
        () => useSafeRouteLoaderData<typeof mockLoaderData>("studio-v2"),
        { wrapper },
      );

      // THEN: Should return the loader data
      expect(result.current).toEqual(mockLoaderData);
      expect(result.current?.sessions).toHaveLength(1);
    });

    it("should return undefined when route ID does not exist in loaderData", () => {
      // GIVEN: Valid context with loader data for a different route
      const mockContext = {
        router: {
          state: {
            loaderData: {
              "other-route": { data: "value" },
            },
          },
        },
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData with non-matching route ID
      const { result } = renderHook(
        () => useSafeRouteLoaderData<{ data: string }>("studio-v2"),
        { wrapper },
      );

      // THEN: Should return undefined
      expect(result.current).toBeUndefined();
    });

    it("should return undefined when loaderData is empty", () => {
      // GIVEN: Valid context with empty loaderData
      const mockContext = {
        router: {
          state: {
            loaderData: {},
          },
        },
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData
      const { result } = renderHook(
        () => useSafeRouteLoaderData<{ data: string }>("studio-v2"),
        { wrapper },
      );

      // THEN: Should return undefined
      expect(result.current).toBeUndefined();
    });

    it("should return undefined when loaderData is undefined", () => {
      // GIVEN: Valid context without loaderData property
      const mockContext = {
        router: {
          state: {
            // No loaderData property
          },
        },
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData
      const { result } = renderHook(
        () => useSafeRouteLoaderData<{ data: string }>("studio-v2"),
        { wrapper },
      );

      // THEN: Should return undefined
      expect(result.current).toBeUndefined();
    });

    it("should handle nested loader data correctly", () => {
      // GIVEN: Valid context with nested data structure
      const mockLoaderData = {
        session: {
          id: "session-1",
          messages: [{ id: "msg-1", content: "Hello" }],
        },
        artifacts: [],
      };
      const mockContext = {
        router: {
          state: {
            loaderData: {
              "chat-session": mockLoaderData,
            },
          },
        },
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData
      const { result } = renderHook(
        () => useSafeRouteLoaderData<typeof mockLoaderData>("chat-session"),
        { wrapper },
      );

      // THEN: Should return the complete nested data
      expect(result.current).toEqual(mockLoaderData);
      expect(result.current?.session.id).toBe("session-1");
      expect(result.current?.session.messages).toHaveLength(1);
    });

    it("should memoize result based on context and routeId", () => {
      // GIVEN: Valid context with loader data
      const mockLoaderData = { data: "test" };
      const mockContext = {
        router: {
          state: {
            loaderData: {
              "test-route": mockLoaderData,
            },
          },
        },
      };
      const wrapper = createWrapper(mockContext);

      // WHEN: Calling useSafeRouteLoaderData multiple times
      const { result, rerender } = renderHook(
        () => useSafeRouteLoaderData<typeof mockLoaderData>("test-route"),
        { wrapper },
      );

      const firstResult = result.current;
      rerender();
      const secondResult = result.current;

      // THEN: Should return the same reference (memoized)
      expect(firstResult).toBe(secondResult);
    });
  });
});
