/**
 * PersonaGuard Tests
 *
 * Tests for persona-based route guard.
 * Uses Redux personaSlice for persona state.
 *
 * Sprint 4: Added tests for ModuleGuard using server-provided visible_modules.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { PersonaGuard, ModuleGuard } from "./PersonaGuard";
import personaReducer, { initialState } from "../../store/slices/personaSlice";
import type { Persona } from "../../types/auth";
import type { ModuleId } from "../../persona/PersonaVariants";

// Create test store with persona state
const createTestStore = (
  persona: Persona,
  isPersonaLoading: boolean = false,
  visibleModules: ModuleId[] = [],
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
        visibleModules,
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
  visibleModules: ModuleId[] = [],
) => {
  const store = createTestStore(persona, isLoading, visibleModules);
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

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should render loading spinner when persona is loading", () => {
    // Arrange & Act
    renderWithStore(
      "user",
      <PersonaGuard allowedPersonas={["admin"]}>
        <div>Admin Content</div>
      </PersonaGuard>,
      "/",
      true, // isLoading
    );

    // Assert - should show loading spinner instead of blank page
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
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

/**
 * Sprint 4: ModuleGuard Tests
 * Tests for module-based access control using server-provided visible_modules.
 */
describe("ModuleGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should render loading spinner when persona is loading", () => {
    // Arrange & Act
    renderWithStore(
      "user",
      <ModuleGuard requiredModule="admin">
        <div>Admin Module</div>
      </ModuleGuard>,
      "/",
      true, // isLoading
      [],
    );

    // Assert
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Admin Module")).not.toBeInTheDocument();
  });

  it("should render children when user has required module in visibleModules", () => {
    // Arrange & Act - User has "admin" in their visible modules
    renderWithStore(
      "admin",
      <ModuleGuard requiredModule="admin">
        <div>Admin Module</div>
      </ModuleGuard>,
      "/",
      false,
      ["chat", "admin", "audit"], // Server-provided visible modules
    );

    // Assert
    expect(screen.getByText("Admin Module")).toBeInTheDocument();
  });

  it("should redirect when user lacks required module", () => {
    // Arrange & Act - User does NOT have "admin" in their visible modules
    renderWithStore(
      "user",
      <Routes>
        <Route
          path="/admin"
          element={
            <ModuleGuard requiredModule="admin" fallbackPath="/unauthorized">
              <div>Admin Module</div>
            </ModuleGuard>
          }
        />
        <Route path="/unauthorized" element={<div>Unauthorized</div>} />
      </Routes>,
      "/admin",
      false,
      ["chat", "help"], // Bob's visible modules - no admin
    );

    // Assert
    expect(screen.getByText("Unauthorized")).toBeInTheDocument();
    expect(screen.queryByText("Admin Module")).not.toBeInTheDocument();
  });

  it("should allow alice-builder access to mcp module", () => {
    // Arrange & Act - Alice builder has access to MCP
    renderWithStore(
      "developer",
      <ModuleGuard requiredModule="mcp">
        <div>MCP Module</div>
      </ModuleGuard>,
      "/",
      false,
      ["chat", "projects", "workflows", "mcp", "agents"], // alice-builder modules
    );

    // Assert
    expect(screen.getByText("MCP Module")).toBeInTheDocument();
  });

  it("should deny bob access to audit module", () => {
    // Arrange & Act - Bob doesn't have audit module
    renderWithStore(
      "user",
      <Routes>
        <Route
          path="/audit"
          element={
            <ModuleGuard requiredModule="audit">
              <div>Audit Module</div>
            </ModuleGuard>
          }
        />
        <Route path="/studio/chat" element={<div>Chat</div>} />
      </Routes>,
      "/audit",
      false,
      ["chat", "projects", "help"], // bob's modules
    );

    // Assert - redirects to default (chat for user persona)
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.queryByText("Audit Module")).not.toBeInTheDocument();
  });

  it("should allow auditor access to compliance module", () => {
    // Arrange & Act - Auditor has compliance module
    renderWithStore(
      "admin", // auditor has admin base persona
      <ModuleGuard requiredModule="compliance">
        <div>Compliance Module</div>
      </ModuleGuard>,
      "/",
      false,
      ["audit", "compliance", "help"], // auditor modules
    );

    // Assert
    expect(screen.getByText("Compliance Module")).toBeInTheDocument();
  });
});
