/**
 * PersonaRouter Tests
 *
 * Tests for persona-based routing that directs users to appropriate sections.
 * Uses Redux for persona and auth state.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { PersonaRouter } from "./PersonaRouter";
import personaReducer from "../store/slices/personaSlice";
import authReducer, { initialAuthState } from "../store/slices/authSlice";
import type { Persona } from "../store/slices/personaSlice";
import type { User } from "../types/auth";

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

describe("PersonaRouter", () => {
  const AdminDashboard = () => <div>Admin Dashboard</div>;
  const StudioWorkflows = () => <div>Studio Workflows</div>;
  const StudioChat = () => <div>Studio Chat</div>;
  const StudioProjects = () => <div>Studio Projects</div>;
  const NotAuthorized = () => <div>Not Authorized</div>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithStore = (
    initialPath: string,
    persona: Persona = "user",
    user: User | null = {
      id: "user-1",
      username: "testuser",
      email: "test@example.com",
      roles: ["user"],
      persona: "user",
    },
  ) => {
    const store = createTestStore(persona, user);
    return {
      store,
      ...render(
        <Provider store={store}>
          <MemoryRouter
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
            initialEntries={[initialPath]}
          >
            <Routes>
              <Route path="/*" element={<PersonaRouter />}>
                <Route path="admin/*">
                  <Route path="dashboard" element={<AdminDashboard />} />
                </Route>
                <Route path="studio/*">
                  <Route path="projects" element={<StudioProjects />} />
                  <Route path="workflows" element={<StudioWorkflows />} />
                  <Route path="chat" element={<StudioChat />} />
                </Route>
                <Route path="not-authorized" element={<NotAuthorized />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </Provider>,
      ),
    };
  };

  describe("Default Routing", () => {
    it("should redirect admin to default route on root path", async () => {
      renderWithStore("/", "admin");

      await waitFor(() => {
        expect(screen.getByText("Studio Projects")).toBeInTheDocument();
      });
    });

    it("should redirect developer to default route on root path", async () => {
      renderWithStore("/", "developer");

      await waitFor(() => {
        expect(screen.getByText("Studio Projects")).toBeInTheDocument();
      });
    });

    it("should redirect user to default route on root path", async () => {
      renderWithStore("/", "user");

      await waitFor(() => {
        expect(screen.getByText("Studio Projects")).toBeInTheDocument();
      });
    });
  });

  describe("Access Control", () => {
    it("should allow admin to access admin routes", async () => {
      renderWithStore("/admin/dashboard", "admin");

      await waitFor(() => {
        expect(screen.getByText("Admin Dashboard")).toBeInTheDocument();
      });
    });

    it("should allow admin to access studio routes", async () => {
      renderWithStore("/studio/workflows", "admin");

      await waitFor(() => {
        expect(screen.getByText("Studio Workflows")).toBeInTheDocument();
      });
    });

    it("should redirect developer away from admin routes", async () => {
      renderWithStore("/admin/dashboard", "developer");

      await waitFor(() => {
        expect(screen.getByText("Not Authorized")).toBeInTheDocument();
      });
    });

    it("should allow developer to access studio routes", async () => {
      renderWithStore("/studio/workflows", "developer");

      await waitFor(() => {
        expect(screen.getByText("Studio Workflows")).toBeInTheDocument();
      });
    });

    it("should allow user to access workflow routes (unified workflows paradigm)", async () => {
      // Users now have access to unified workflows (owned + shared workflows)
      // This is part of the AI-native UX - HEART Adoption improvement
      renderWithStore("/studio/workflows", "user");

      await waitFor(() => {
        expect(screen.getByText("Studio Workflows")).toBeInTheDocument();
      });
    });

    it("should allow user to access chat", async () => {
      renderWithStore("/studio/chat", "user");

      await waitFor(() => {
        expect(screen.getByText("Studio Chat")).toBeInTheDocument();
      });
    });

    it("should allow user to access projects", async () => {
      renderWithStore("/studio/projects", "user");

      await waitFor(() => {
        expect(screen.getByText("Studio Projects")).toBeInTheDocument();
      });
    });
  });

  describe("Authentication Check", () => {
    it("should not render content when not authenticated", async () => {
      renderWithStore("/studio/workflows", "developer", null);

      await waitFor(() => {
        // PersonaRouter returns null when not authenticated
        expect(screen.queryByText("Studio Workflows")).not.toBeInTheDocument();
      });
    });

    it("should render content when authenticated", async () => {
      renderWithStore("/studio/chat", "user");

      await waitFor(() => {
        expect(screen.getByText("Studio Chat")).toBeInTheDocument();
      });
    });
  });

  describe("Route Persistence", () => {
    it("should allow navigation within allowed routes for developer", async () => {
      renderWithStore("/studio/workflows", "developer");

      await waitFor(() => {
        expect(screen.getByText("Studio Workflows")).toBeInTheDocument();
      });
    });

    it("should allow navigation within allowed routes for user", async () => {
      renderWithStore("/studio/chat", "user");

      await waitFor(() => {
        expect(screen.getByText("Studio Chat")).toBeInTheDocument();
      });
    });
  });
});
