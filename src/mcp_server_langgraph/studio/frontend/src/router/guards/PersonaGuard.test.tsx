/**
 * PersonaGuard Tests
 *
 * Tests for persona-based route guard.
 * Uses Redux personaSlice for persona state.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { PersonaGuard } from "./PersonaGuard";
import personaReducer, { initialState } from "../../store/slices/personaSlice";
import type { Persona } from "../../types/auth";

// Create test store with persona state
const createTestStore = (
  persona: Persona,
  isPersonaLoading: boolean = false,
) => {
  return configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        ...initialState,
        persona,
        isPersonaLoading,
      },
    },
  });
};

// Helper to render with store
const renderWithStore = (
  persona: Persona,
  children: React.ReactNode,
  initialPath: string = "/",
  isLoading: boolean = false,
) => {
  const store = createTestStore(persona, isLoading);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={[initialPath]}
        >
          {children}
        </MemoryRouter>
      </Provider>,
    ),
  };
};

describe("PersonaGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render null when persona is loading", () => {
    // Arrange & Act
    const { container } = renderWithStore(
      "user",
      <PersonaGuard allowedPersonas={["admin"]}>
        <div>Admin Content</div>
      </PersonaGuard>,
      "/",
      true, // isLoading
    );

    // Assert
    expect(container.innerHTML).toBe("");
  });

  it("should render children when user has allowed persona", () => {
    // Arrange & Act
    renderWithStore(
      "admin",
      <PersonaGuard allowedPersonas={["admin"]}>
        <div>Admin Content</div>
      </PersonaGuard>,
    );

    // Assert
    expect(screen.getByText("Admin Content")).toBeInTheDocument();
  });

  it("should render children when user has one of multiple allowed personas", () => {
    // Arrange & Act
    renderWithStore(
      "developer",
      <PersonaGuard allowedPersonas={["admin", "developer"]}>
        <div>Dev or Admin Content</div>
      </PersonaGuard>,
    );

    // Assert
    expect(screen.getByText("Dev or Admin Content")).toBeInTheDocument();
  });

  it("should redirect to fallback path when persona not allowed", () => {
    // Arrange & Act
    renderWithStore(
      "user",
      <Routes>
        <Route
          path="/admin"
          element={
            <PersonaGuard
              allowedPersonas={["admin"]}
              fallbackPath="/unauthorized"
            >
              <div>Admin Content</div>
            </PersonaGuard>
          }
        />
        <Route path="/unauthorized" element={<div>Unauthorized</div>} />
      </Routes>,
      "/admin",
    );

    // Assert
    expect(screen.getByText("Unauthorized")).toBeInTheDocument();
    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
  });

  it("should redirect to persona default route when no fallback specified", () => {
    // Arrange & Act
    renderWithStore(
      "user",
      <Routes>
        <Route
          path="/admin"
          element={
            <PersonaGuard allowedPersonas={["admin"]}>
              <div>Admin Content</div>
            </PersonaGuard>
          }
        />
        <Route path="/studio/chat" element={<div>User Chat</div>} />
      </Routes>,
      "/admin",
    );

    // Assert - user persona defaults to /studio/chat
    expect(screen.getByText("User Chat")).toBeInTheDocument();
  });

  it("should redirect developer to workflows when accessing admin", () => {
    // Arrange & Act
    renderWithStore(
      "developer",
      <Routes>
        <Route
          path="/admin"
          element={
            <PersonaGuard allowedPersonas={["admin"]}>
              <div>Admin Content</div>
            </PersonaGuard>
          }
        />
        <Route
          path="/studio/workflows"
          element={<div>Developer Workflows</div>}
        />
      </Routes>,
      "/admin",
    );

    // Assert - developer persona defaults to /studio/workflows
    expect(screen.getByText("Developer Workflows")).toBeInTheDocument();
  });
});
