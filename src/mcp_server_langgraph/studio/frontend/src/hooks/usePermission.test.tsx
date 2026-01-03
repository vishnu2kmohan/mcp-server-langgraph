/**
 * usePermission Hook Tests
 *
 * TDD tests for permission-based UI hook.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

import {
  usePermission,
  useRoutePermission,
  usePermissions,
} from "./usePermission";
import personaReducer, {
  setPersona,
  setPermissions,
  type Persona,
} from "../store/slices/personaSlice";

// Create test store factory
function createTestStore(
  options: {
    persona?: Persona;
    permissions?: string[];
  } = {},
) {
  const store = configureStore({
    reducer: {
      persona: personaReducer,
    },
  });

  if (options.persona) {
    store.dispatch(setPersona(options.persona));
  }

  if (options.permissions) {
    store.dispatch(setPermissions(options.permissions));
  }

  return store;
}

// Test wrapper factory
function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

describe("usePermission", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  describe("admin persona", () => {
    it("should allow any permission for admin", () => {
      const store = createTestStore({ persona: "admin" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => usePermission("admin:users:write"), {
        wrapper,
      });

      expect(result.current.allowed).toBe(true);
      expect(result.current.reason).toBeNull();
    });

    it("should allow permissions not explicitly granted for admin", () => {
      const store = createTestStore({ persona: "admin" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermission("some:random:permission"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(true);
    });
  });

  describe("developer persona", () => {
    it("should allow explicitly granted permissions", () => {
      const store = createTestStore({
        persona: "developer",
        permissions: ["workflow:create", "workflow:edit"],
      });
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => usePermission("workflow:create"), {
        wrapper,
      });

      expect(result.current.allowed).toBe(true);
      expect(result.current.reason).toBeNull();
    });

    it("should deny permissions not granted", () => {
      const store = createTestStore({
        persona: "developer",
        permissions: ["workflow:create"],
      });
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => usePermission("admin:users:write"), {
        wrapper,
      });

      expect(result.current.allowed).toBe(false);
      expect(result.current.reason).toContain("admin:users:write");
      expect(result.current.reason).toContain("developer");
    });
  });

  describe("user persona", () => {
    it("should deny admin permissions", () => {
      const store = createTestStore({ persona: "user" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermission("admin:dashboard:view"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(false);
      expect(result.current.reason).toContain("user");
    });

    it("should allow explicitly granted permissions", () => {
      const store = createTestStore({
        persona: "user",
        permissions: ["chat:send", "project:view"],
      });
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => usePermission("chat:send"), {
        wrapper,
      });

      expect(result.current.allowed).toBe(true);
    });
  });
});

describe("useRoutePermission", () => {
  describe("admin persona", () => {
    it("should allow any route for admin", () => {
      const store = createTestStore({ persona: "admin" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => useRoutePermission("/studio/admin/users"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(true);
      expect(result.current.reason).toBeNull();
    });
  });

  describe("developer persona", () => {
    it("should allow studio routes", () => {
      const store = createTestStore({ persona: "developer" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => useRoutePermission("/studio/chat"), {
        wrapper,
      });

      expect(result.current.allowed).toBe(true);
    });
  });

  describe("user persona", () => {
    it("should allow permitted routes", () => {
      const store = createTestStore({ persona: "user" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => useRoutePermission("/studio/chat"), {
        wrapper,
      });

      expect(result.current.allowed).toBe(true);
    });

    it("should deny admin routes", () => {
      const store = createTestStore({ persona: "user" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => useRoutePermission("/admin/users"), {
        wrapper,
      });

      expect(result.current.allowed).toBe(false);
      expect(result.current.reason).toContain("/admin/users");
    });
  });
});

describe("usePermissions", () => {
  describe("mode: all", () => {
    it("should require all permissions to be granted", () => {
      const store = createTestStore({
        persona: "developer",
        permissions: ["workflow:create", "workflow:edit"],
      });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermissions(["workflow:create", "workflow:edit"], "all"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(true);
    });

    it("should deny if any permission is missing", () => {
      const store = createTestStore({
        persona: "developer",
        permissions: ["workflow:create"],
      });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermissions(["workflow:create", "workflow:delete"], "all"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(false);
      expect(result.current.reason).toContain("workflow:delete");
    });
  });

  describe("mode: any", () => {
    it("should allow if any permission is granted", () => {
      const store = createTestStore({
        persona: "developer",
        permissions: ["workflow:create"],
      });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermissions(["workflow:create", "admin:users:write"], "any"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(true);
    });

    it("should deny if no permissions are granted", () => {
      const store = createTestStore({
        persona: "developer",
        permissions: [],
      });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermissions(["admin:a", "admin:b"], "any"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(false);
      expect(result.current.reason).toContain(
        "None of the required permissions",
      );
    });
  });

  describe("admin bypass", () => {
    it("should allow all permissions for admin in all mode", () => {
      const store = createTestStore({ persona: "admin" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermissions(["any:permission", "another:one"], "all"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(true);
    });

    it("should allow all permissions for admin in any mode", () => {
      const store = createTestStore({ persona: "admin" });
      const wrapper = createWrapper(store);

      const { result } = renderHook(
        () => usePermissions(["random:permission"], "any"),
        { wrapper },
      );

      expect(result.current.allowed).toBe(true);
    });
  });
});
