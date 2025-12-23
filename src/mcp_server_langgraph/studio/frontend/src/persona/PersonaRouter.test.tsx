/**
 * PersonaRouter Tests
 *
 * TDD tests for the persona-aware router component that:
 * - Redirects users to their default view based on persona
 * - Blocks access to unauthorized routes
 * - Shows loading state while persona is loading
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter, Routes, Route, useLocation } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { PersonaRouter } from "./PersonaRouter";
import personaReducer, { type SubPersona } from "../store/slices/personaSlice";

// =============================================================================
// Test Setup
// =============================================================================

// Helper to capture current location
const LocationDisplay = () => {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
};

const createTestStore = (
  overrides: {
    persona?: "admin" | "developer" | "user";
    subPersona?: string | null;
    isPersonaLoading?: boolean;
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
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: overrides.isPersonaLoading ?? false,
      },
    },
  });
};

const renderWithRouter = (
  store: ReturnType<typeof createTestStore>,
  initialRoute: string,
  children: React.ReactNode,
) => {
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route
            path="/*"
            element={<PersonaRouter>{children}</PersonaRouter>}
          />
        </Routes>
        <LocationDisplay />
      </MemoryRouter>
    </Provider>,
  );
};

// =============================================================================
// Tests
// =============================================================================

describe("PersonaRouter", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should show loading spinner when persona is loading", () => {
      const store = createTestStore({ isPersonaLoading: true });
      renderWithRouter(store, "/studio/v2/chat", <div>Content</div>);

      expect(screen.getByTestId("persona-loading")).toBeInTheDocument();
    });

    it("should show loading message", () => {
      const store = createTestStore({ isPersonaLoading: true });
      renderWithRouter(store, "/studio/v2/chat", <div>Content</div>);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it("should render children when persona is loaded", () => {
      const store = createTestStore({ isPersonaLoading: false });
      renderWithRouter(store, "/studio/v2/chat", <div>Protected Content</div>);

      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  describe("Index Route Redirect", () => {
    it("should redirect admin to /studio/v2/admin on index route", async () => {
      const store = createTestStore({
        persona: "admin",
        subPersona: "admin",
      });
      renderWithRouter(
        store,
        "/studio/v2",
        <Routes>
          <Route index element={<div>Index</div>} />
          <Route path="admin" element={<div>Admin Page</div>} />
        </Routes>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("location")).toHaveTextContent(
          "/studio/v2/admin",
        );
      });
    });

    it("should redirect bob to /studio/v2/chat on index route", async () => {
      const store = createTestStore({
        persona: "user",
        subPersona: "bob",
      });
      renderWithRouter(
        store,
        "/studio/v2",
        <Routes>
          <Route index element={<div>Index</div>} />
          <Route path="chat" element={<div>Chat Page</div>} />
        </Routes>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("location")).toHaveTextContent(
          "/studio/v2/chat",
        );
      });
    });

    it("should redirect alice-analyst to observability", async () => {
      const store = createTestStore({
        persona: "developer",
        subPersona: "alice-analyst",
      });
      renderWithRouter(
        store,
        "/studio/v2",
        <Routes>
          <Route index element={<div>Index</div>} />
          <Route path="observability" element={<div>Observability</div>} />
        </Routes>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("location")).toHaveTextContent(
          "/studio/v2/observability",
        );
      });
    });
  });

  describe("Route Access Control", () => {
    it("should allow admin to access admin routes", () => {
      const store = createTestStore({
        persona: "admin",
        subPersona: "admin",
      });
      renderWithRouter(
        store,
        "/studio/v2/admin",
        <div data-testid="admin-content">Admin Content</div>,
      );

      expect(screen.getByTestId("admin-content")).toBeInTheDocument();
    });

    it("should allow developer to access chat routes", () => {
      const store = createTestStore({
        persona: "developer",
        subPersona: "alice-builder",
      });
      renderWithRouter(
        store,
        "/studio/v2/chat",
        <div data-testid="chat-content">Chat Content</div>,
      );

      expect(screen.getByTestId("chat-content")).toBeInTheDocument();
    });

    it("should show access denied for unauthorized route", async () => {
      const store = createTestStore({
        persona: "user",
        subPersona: "bob",
      });
      renderWithRouter(
        store,
        "/studio/v2/admin",
        <div data-testid="admin-content">Admin Content</div>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("access-denied")).toBeInTheDocument();
      });
    });

    it("should show request access link on access denied", async () => {
      const store = createTestStore({
        persona: "user",
        subPersona: "bob",
      });
      renderWithRouter(store, "/studio/v2/admin", <div>Admin Content</div>);

      await waitFor(() => {
        expect(screen.getByText(/request access/i)).toBeInTheDocument();
      });
    });
  });

  describe("Persona-specific routing", () => {
    it("should allow auditor to access audit routes", () => {
      const store = createTestStore({
        persona: "admin",
        subPersona: "auditor",
      });
      renderWithRouter(
        store,
        "/studio/v2/audit",
        <div data-testid="audit-content">Audit Content</div>,
      );

      expect(screen.getByTestId("audit-content")).toBeInTheDocument();
    });

    it("should allow compliance-officer to access compliance routes", () => {
      const store = createTestStore({
        persona: "developer",
        subPersona: "compliance-officer",
      });
      renderWithRouter(
        store,
        "/studio/v2/compliance",
        <div data-testid="compliance-content">Compliance Content</div>,
      );

      expect(screen.getByTestId("compliance-content")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA role for loading state", () => {
      const store = createTestStore({ isPersonaLoading: true });
      renderWithRouter(store, "/studio/v2/chat", <div>Content</div>);

      const loading = screen.getByTestId("persona-loading");
      expect(loading).toHaveAttribute("role", "status");
    });

    it("should have proper ARIA role for access denied", async () => {
      const store = createTestStore({
        persona: "user",
        subPersona: "bob",
      });
      renderWithRouter(store, "/studio/v2/admin", <div>Admin</div>);

      await waitFor(() => {
        const denied = screen.getByTestId("access-denied");
        expect(denied).toHaveAttribute("role", "alert");
      });
    });
  });
});
