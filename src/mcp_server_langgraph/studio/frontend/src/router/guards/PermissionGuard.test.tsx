/**
 * PermissionGuard Tests
 *
 * TDD tests for the permission-based route guard.
 * Integrates with usePermissionCache for RBAC enforcement.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { PermissionGuard } from "./PermissionGuard";
import personaReducer from "../../store/slices/personaSlice";
import authReducer from "../../store/slices/authSlice";
import {
  PermissionCacheProvider,
  usePermissionCache,
} from "../../hooks/usePermissionCache";

// Mock usePermissionCache
vi.mock("../../hooks/usePermissionCache", async () => {
  const actual = await vi.importActual("../../hooks/usePermissionCache");
  return {
    ...actual,
    usePermissionCache: vi.fn(),
  };
});

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = (persona: "admin" | "developer" | "user" = "developer") =>
  configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona,
        username: persona === "admin" ? "admin" : persona === "developer" ? "alice" : "bob",
        email: `${persona}@example.com`,
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        user: {
          id: `user-${persona}`,
          username: persona === "admin" ? "admin" : persona === "developer" ? "alice" : "bob",
          email: `${persona}@example.com`,
          roles: [persona],
          persona,
        },
        tokens: {
          accessToken: "mock-token",
          refreshToken: "mock-refresh",
          expiresAt: Date.now() + 3600000,
          refreshExpiresAt: Date.now() + 86400000,
        },
        currentOrg: null,
        organizations: [],
        isInitializing: false,
        isLoading: false,
        error: null,
      },
    },
  });

const TestWrapper = ({
  children,
  store,
  initialPath = "/protected",
}: {
  children: React.ReactNode;
  store: ReturnType<typeof createTestStore>;
  initialPath?: string;
}) => (
  <Provider store={store}>
    <PermissionCacheProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/protected" element={children} />
          <Route path="/unauthorized" element={<div data-testid="unauthorized-page">Unauthorized</div>} />
          <Route path="/login" element={<div data-testid="login-page">Login</div>} />
        </Routes>
      </MemoryRouter>
    </PermissionCacheProvider>
  </Provider>
);

// =============================================================================
// Tests
// =============================================================================

describe("PermissionGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Permission Checking", () => {
    it("should render children when user has required permission", async () => {
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn().mockResolvedValue(true),
        checkPermissions: vi.fn().mockResolvedValue([true]),
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: false,
        error: null,
      });

      const store = createTestStore("developer");

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["read:sessions"]}>
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("protected-content")).toBeInTheDocument();
      });
    });

    it("should redirect when user lacks required permission", async () => {
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn().mockResolvedValue(false),
        checkPermissions: vi.fn().mockResolvedValue([false]),
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: false,
        error: null,
      });

      const store = createTestStore("user");

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["admin:dashboard"]}
            fallbackPath="/unauthorized"
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("unauthorized-page")).toBeInTheDocument();
      });
    });

    it("should check multiple permissions with AND logic by default", async () => {
      const mockCheckPermissions = vi.fn().mockResolvedValue([true, false]);
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn(),
        checkPermissions: mockCheckPermissions,
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: false,
        error: null,
      });

      const store = createTestStore("developer");

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["read:sessions", "write:sessions"]}
            fallbackPath="/unauthorized"
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("unauthorized-page")).toBeInTheDocument();
      });
    });

    it("should check multiple permissions with OR logic when specified", async () => {
      const mockCheckPermissions = vi.fn().mockResolvedValue([true, false]);
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn(),
        checkPermissions: mockCheckPermissions,
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: false,
        error: null,
      });

      const store = createTestStore("developer");

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["read:sessions", "admin:dashboard"]}
            requireAll={false}
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("protected-content")).toBeInTheDocument();
      });
    });
  });

  describe("Admin Bypass", () => {
    it("should always allow admin to access protected routes", async () => {
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn().mockResolvedValue(true),
        checkPermissions: vi.fn().mockResolvedValue([true]),
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: false,
        error: null,
      });

      const store = createTestStore("admin");

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["super:secret:permission"]}>
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("protected-content")).toBeInTheDocument();
      });
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator while checking permissions", async () => {
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn().mockImplementation(() => new Promise(() => {})), // Never resolves
        checkPermissions: vi.fn().mockImplementation(() => new Promise(() => {})),
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: true,
        error: null,
      });

      const store = createTestStore("developer");

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["read:sessions"]}
            loadingComponent={<div data-testid="loading">Loading...</div>}
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("loading")).toBeInTheDocument();
    });

    it("should render null by default during loading", async () => {
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn().mockImplementation(() => new Promise(() => {})),
        checkPermissions: vi.fn().mockImplementation(() => new Promise(() => {})),
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: true,
        error: null,
      });

      const store = createTestStore("developer");

      const { container } = render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["read:sessions"]}>
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(container.querySelector('[data-testid="protected-content"]')).toBeNull();
    });
  });

  describe("Error Handling", () => {
    it("should redirect to fallback on permission check error", async () => {
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn().mockRejectedValue(new Error("Network error")),
        checkPermissions: vi.fn().mockRejectedValue(new Error("Network error")),
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: false,
        error: "Network error",
      });

      const store = createTestStore("developer");

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["read:sessions"]}
            fallbackPath="/unauthorized"
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("unauthorized-page")).toBeInTheDocument();
      });
    });
  });

  describe("Outlet Integration", () => {
    it("should render Outlet when no children provided", async () => {
      const mockUsePermissionCache = vi.mocked(usePermissionCache);
      mockUsePermissionCache.mockReturnValue({
        checkPermission: vi.fn().mockResolvedValue(true),
        checkPermissions: vi.fn().mockResolvedValue([true]),
        invalidateOnError: vi.fn(),
        invalidateCache: vi.fn(),
        onTokenRefresh: vi.fn(),
        isLoading: false,
        error: null,
      });

      const store = createTestStore("developer");

      render(
        <Provider store={store}>
          <PermissionCacheProvider>
            <MemoryRouter initialEntries={["/protected/child"]}>
              <Routes>
                <Route
                  path="/protected"
                  element={<PermissionGuard requiredPermissions={["read:sessions"]} />}
                >
                  <Route
                    path="child"
                    element={<div data-testid="child-route">Child Route</div>}
                  />
                </Route>
              </Routes>
            </MemoryRouter>
          </PermissionCacheProvider>
        </Provider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("child-route")).toBeInTheDocument();
      });
    });
  });
});
