/**
 * PersonaContext Tests
 *
 * TDD tests for the React context that provides persona state
 * to components without direct Redux access.
 */
import { describe, it, expect } from "vitest";
import { render, screen, renderHook, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import {
  PersonaProvider,
  usePersonaContext,
  useCanAccessModule,
  useDefaultRoute,
} from "./PersonaContext";
import personaReducer, {
  setSubPersona,
  type SubPersona,
} from "../store/slices/personaSlice";

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = (
  overrides: {
    persona?: "admin" | "developer" | "user";
    subPersona?: string | null;
    username?: string;
  } = {},
) => {
  return configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona: overrides.persona ?? "user",
        subPersona: (overrides.subPersona as SubPersona | null) ?? null,
        username: overrides.username ?? "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
    },
  });
};

const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <PersonaProvider>{children}</PersonaProvider>
      </Provider>
    );
  };
};

// =============================================================================
// PersonaProvider Tests
// =============================================================================

describe("PersonaContext", () => {
  describe("PersonaProvider", () => {
    it("should render children", () => {
      const store = createTestStore();
      render(
        <Provider store={store}>
          <PersonaProvider>
            <div data-testid="child">Child Content</div>
          </PersonaProvider>
        </Provider>,
      );

      expect(screen.getByTestId("child")).toBeInTheDocument();
    });

    it("should throw error when usePersonaContext is used outside provider", () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      const TestComponent = () => {
        usePersonaContext();
        return null;
      };

      expect(() => render(<TestComponent />)).toThrow(
        "usePersonaContext must be used within a PersonaProvider",
      );

      consoleSpy.mockRestore();
    });
  });

  describe("usePersonaContext", () => {
    it("should return current persona", () => {
      const store = createTestStore({ persona: "admin" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.persona).toBe("admin");
    });

    it("should return sub-persona when set", () => {
      const store = createTestStore({ subPersona: "alice-builder" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.subPersona).toBe("alice-builder");
    });

    it("should return username", () => {
      const store = createTestStore({ username: "alice" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.username).toBe("alice");
    });

    it("should return visible modules for admin", () => {
      const store = createTestStore({ persona: "admin", subPersona: "admin" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.visibleModules).toContain("chat");
      expect(result.current.visibleModules).toContain("admin");
      expect(result.current.visibleModules).toContain("compliance");
    });

    it("should return limited modules for bob", () => {
      const store = createTestStore({ persona: "user", subPersona: "bob" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.visibleModules).toContain("chat");
      expect(result.current.visibleModules).toContain("projects");
      expect(result.current.visibleModules).not.toContain("admin");
    });

    it("should update when persona changes", () => {
      const store = createTestStore({ persona: "user" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.persona).toBe("user");

      act(() => {
        store.dispatch(setSubPersona("alice-builder"));
      });

      expect(result.current.persona).toBe("developer");
      expect(result.current.subPersona).toBe("alice-builder");
    });

    it("should provide isAdmin helper", () => {
      const store = createTestStore({ persona: "admin" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isAdmin).toBe(true);
    });

    it("should provide isDeveloper helper", () => {
      const store = createTestStore({ persona: "developer" });
      const { result } = renderHook(() => usePersonaContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isDeveloper).toBe(true);
    });
  });

  describe("useCanAccessModule", () => {
    it("should return true for accessible module", () => {
      const store = createTestStore({ persona: "admin", subPersona: "admin" });
      const { result } = renderHook(() => useCanAccessModule("admin"), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toBe(true);
    });

    it("should return false for inaccessible module", () => {
      const store = createTestStore({ persona: "user", subPersona: "bob" });
      const { result } = renderHook(() => useCanAccessModule("admin"), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toBe(false);
    });

    it("should allow chat access for all personas", () => {
      const store = createTestStore({ persona: "user", subPersona: "bob" });
      const { result } = renderHook(() => useCanAccessModule("chat"), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toBe(true);
    });
  });

  describe("useDefaultRoute", () => {
    it("should return admin default route for admin", () => {
      const store = createTestStore({ persona: "admin", subPersona: "admin" });
      const { result } = renderHook(() => useDefaultRoute(), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toBe("/studio/v2/admin");
    });

    it("should return chat route for bob", () => {
      const store = createTestStore({ persona: "user", subPersona: "bob" });
      const { result } = renderHook(() => useDefaultRoute(), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toBe("/studio/v2/chat");
    });

    it("should return observability route for alice-analyst", () => {
      const store = createTestStore({
        persona: "developer",
        subPersona: "alice-analyst",
      });
      const { result } = renderHook(() => useDefaultRoute(), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toBe("/studio/v2/observability");
    });
  });
});
