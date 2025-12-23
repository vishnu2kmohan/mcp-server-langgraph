/**
 * usePersonaRouting Hook Tests
 *
 * TDD tests for persona-based routing hook that integrates with StudioShellLayout.
 * Handles default route redirects and route access validation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { usePersonaRouting } from "./usePersonaRouting";
import personaReducer, { type Persona } from "../store/slices/personaSlice";
import authReducer, { initialAuthState } from "../store/slices/authSlice";
import type { User } from "../types/auth";
import type { ReactNode } from "react";

// Track navigations
const mockNavigate = vi.fn();

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Create test store with persona and auth state
const createTestStore = (
  persona: Persona = "user",
  user: User | null = {
    id: "user-1",
    username: "testuser",
    email: "test@example.com",
    roles: ["user"],
    persona: "user",
  },
) => {
  return configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        ...initialAuthState,
        user,
        isInitializing: false,
      },
    },
  });
};

// Wrapper component for providing context
function createWrapper(
  initialPath: string,
  persona: Persona = "user",
  user: User | null = {
    id: "user-1",
    username: "testuser",
    email: "test@example.com",
    roles: ["user"],
    persona: "user",
  },
) {
  const store = createTestStore(persona, user);

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={[initialPath]}
        >
          <Routes>
            <Route path="/*" element={children} />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
  };
}

describe("usePersonaRouting", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("authentication check", () => {
    it("should return isAuthenticated false when user is null", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/v2/chat", "user", null),
      });

      expect(result.current.isAuthenticated).toBe(false);
    });

    it("should return isAuthenticated true when user exists", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/v2/chat"),
      });

      expect(result.current.isAuthenticated).toBe(true);
    });
  });

  describe("default route redirect", () => {
    it("should NOT redirect on /studio - router index redirect handles it", async () => {
      // The hook should NOT navigate on /studio paths
      // The router has: { index: true, element: <Navigate to="chat" replace /> }
      renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio", "admin"),
      });

      // Wait a bit to ensure no navigation happens
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Hook should NOT intercept - let router handle it
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should redirect from root path / to default route", async () => {
      renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/", "user"),
      });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining("/studio"),
          expect.objectContaining({ replace: true }),
        );
      });
    });

    it("should NOT redirect on /studio/chat - already on valid route", async () => {
      renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/chat", "developer"),
      });

      // Wait a bit to ensure no navigation happens
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Already on a valid route, should not navigate
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe("route access validation", () => {
    it("should allow admin to access admin routes", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/admin", "admin"),
      });

      expect(result.current.canAccessRoute).toBe(true);
    });

    it("should allow admin to access all routes", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/compliance", "admin"),
      });

      expect(result.current.canAccessRoute).toBe(true);
    });

    it("should allow developer to access developer routes", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/chat", "developer"),
      });

      expect(result.current.canAccessRoute).toBe(true);
    });

    it("should allow user to access chat routes", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/chat", "user"),
      });

      expect(result.current.canAccessRoute).toBe(true);
    });
  });

  describe("persona info", () => {
    it("should return current persona", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/chat", "admin"),
      });

      expect(result.current.persona).toBe("admin");
    });

    it("should return default route for persona", () => {
      const { result } = renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/chat", "admin"),
      });

      expect(result.current.defaultRoute).toContain("/studio");
    });
  });

  describe("no navigation when not needed", () => {
    it("should not navigate when already on a valid route", async () => {
      renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/chat", "user"),
      });

      // Wait a bit to ensure no navigation happens
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should not navigate since we're already on a valid route
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should not navigate when not authenticated", async () => {
      renderHook(() => usePersonaRouting(), {
        wrapper: createWrapper("/studio/chat", "user", null),
      });

      // Wait a bit to ensure no navigation happens
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should not navigate - AuthGuard handles unauthenticated users
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });
});
