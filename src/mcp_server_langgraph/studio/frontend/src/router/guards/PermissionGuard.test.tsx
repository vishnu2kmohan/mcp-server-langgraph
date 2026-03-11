/**
 * PermissionGuard Tests
 *
 * TDD tests for the permission-based route guard.
 * Uses Redux state (persona and visible_modules) for permission derivation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { PermissionGuard } from "./PermissionGuard";
import personaReducer from "../../store/slices/personaSlice";
import authReducer from "../../store/slices/authSlice";

// =============================================================================
// Test Setup
// =============================================================================

interface CreateTestStoreOptions {
  persona?: "admin" | "developer" | "user";
  visibleModules?: string[];
  isPersonaLoading?: boolean;
}

const createTestStore = ({
  persona = "developer",
  visibleModules = [],
  isPersonaLoading = false,
}: CreateTestStoreOptions = {}) =>
  configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona,
        subPersona: null,
        username:
          persona === "admin"
            ? "admin"
            : persona === "developer"
              ? "alice"
              : "bob",
        email: `${persona}@example.com`,
        permissions: [],
        isPersonaLoading,
        visibleModules,
        featureFlags: {},
        apiVersion: "2",
      },
      auth: {
        user: {
          id: `user-${persona}`,
          username:
            persona === "admin"
              ? "admin"
              : persona === "developer"
                ? "alice"
                : "bob",
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
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/protected" element={children} />
        <Route
          path="/unauthorized"
          element={<div data-testid="unauthorized-page">Unauthorized</div>}
        />
        <Route
          path="/login"
          element={<div data-testid="login-page">Login</div>}
        />
        <Route
          path="/studio/chat"
          element={<div data-testid="fallback-page">Chat Fallback</div>}
        />
      </Routes>
    </MemoryRouter>
  </Provider>
);

// =============================================================================
// Tests
// =============================================================================

describe("PermissionGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Permission Checking", () => {
    it("should render children when developer has read permission", () => {
      // Developers have read access to all modules
      const store = createTestStore({ persona: "developer" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["sessions:read"]}>
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });

    it("should render children when user has module in visible_modules", () => {
      // User persona with compliance in visible_modules
      const store = createTestStore({
        persona: "user",
        visibleModules: ["compliance"],
      });

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["compliance:view"]}>
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });

    it("should redirect when user lacks required permission", () => {
      // User persona without admin:access permission
      const store = createTestStore({ persona: "user" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["admin:access"]}
            fallbackPath="/unauthorized"
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("unauthorized-page")).toBeInTheDocument();
    });

    it("should check multiple permissions with AND logic by default", () => {
      // User has sessions in visible_modules but not admin
      const store = createTestStore({
        persona: "user",
        visibleModules: ["sessions"],
      });

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["sessions:view", "admin:access"]}
            fallbackPath="/unauthorized"
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      // Should redirect because admin:access fails
      expect(screen.getByTestId("unauthorized-page")).toBeInTheDocument();
    });

    it("should check multiple permissions with OR logic when specified", () => {
      // Developer has read access, should pass with OR logic
      const store = createTestStore({ persona: "developer" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["sessions:read", "admin:access"]}
            requireAll={false}
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      // Should render because sessions:read passes (developer has read access)
      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });
  });

  describe("Admin Bypass", () => {
    it("should always allow admin to access protected routes", () => {
      // Admin bypasses all permission checks
      const store = createTestStore({ persona: "admin" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["super:secret:permission"]}>
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });

    it("should allow admin to access admin-only routes", () => {
      const store = createTestStore({ persona: "admin" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["admin:access"]}>
            <div data-testid="protected-content">Admin Panel</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });
  });

  describe("Developer Access", () => {
    it("should allow developer read access to all modules", () => {
      const store = createTestStore({ persona: "developer" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["compliance:read"]}>
            <div data-testid="protected-content">Compliance Dashboard</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });

    it("should deny developer access to admin:access", () => {
      const store = createTestStore({ persona: "developer" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["admin:access"]}
            fallbackPath="/unauthorized"
          >
            <div data-testid="protected-content">Admin Panel</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("unauthorized-page")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator while persona is loading", () => {
      const store = createTestStore({
        persona: "developer",
        isPersonaLoading: true,
      });

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["sessions:read"]}
            loadingComponent={<div data-testid="loading">Loading...</div>}
          >
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("loading")).toBeInTheDocument();
    });

    it("should render null by default during loading", () => {
      const store = createTestStore({
        persona: "developer",
        isPersonaLoading: true,
      });

      const { container } = render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["sessions:read"]}>
            <div data-testid="protected-content">Protected Content</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(
        container.querySelector('[data-testid="protected-content"]'),
      ).toBeNull();
      expect(container.querySelector('[data-testid="loading"]')).toBeNull();
    });
  });

  describe("Visible Modules", () => {
    it("should grant access when module is in visible_modules", () => {
      const store = createTestStore({
        persona: "user",
        visibleModules: ["audit", "compliance"],
      });

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["audit:view"]}>
            <div data-testid="protected-content">Audit Log</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("protected-content")).toBeInTheDocument();
    });

    it("should deny access when module is not in visible_modules", () => {
      const store = createTestStore({
        persona: "user",
        visibleModules: ["audit"],
      });

      render(
        <TestWrapper store={store}>
          <PermissionGuard
            requiredPermissions={["compliance:view"]}
            fallbackPath="/unauthorized"
          >
            <div data-testid="protected-content">Compliance Dashboard</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("unauthorized-page")).toBeInTheDocument();
    });
  });

  describe("Outlet Integration", () => {
    it("should render Outlet when no children provided", () => {
      const store = createTestStore({ persona: "developer" });

      render(
        <Provider store={store}>
          <MemoryRouter initialEntries={["/protected/child"]}>
            <Routes>
              <Route
                path="/protected"
                element={
                  <PermissionGuard requiredPermissions={["sessions:read"]} />
                }
              >
                <Route
                  path="child"
                  element={<div data-testid="child-route">Child Route</div>}
                />
              </Route>
            </Routes>
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByTestId("child-route")).toBeInTheDocument();
    });
  });

  describe("Default Fallback", () => {
    it("should redirect to /studio/chat by default when access denied", () => {
      const store = createTestStore({ persona: "user" });

      render(
        <TestWrapper store={store}>
          <PermissionGuard requiredPermissions={["admin:access"]}>
            <div data-testid="protected-content">Admin Panel</div>
          </PermissionGuard>
        </TestWrapper>,
      );

      expect(screen.getByTestId("fallback-page")).toBeInTheDocument();
    });
  });
});
