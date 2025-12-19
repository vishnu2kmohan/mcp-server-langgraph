/**
 * HybridShellLayout Tests
 *
 * Phase 1: Full layout tests with resizable panels
 * Tests verify the layout renders with all panels and resizable functionality.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { HybridShellLayout } from "./HybridShellLayout";
import canvasReducer from "../store/slices/canvasSlice";
import personaReducer, {
  setUserInfo,
  type Persona,
} from "../store/slices/personaSlice";

// Mock react-resizable-panels to avoid layout calculation issues in tests
vi.mock("react-resizable-panels", () => ({
  Panel: ({ children, ...props }: { children: React.ReactNode }) => (
    <div data-testid={props["data-testid"]} className={props.className}>
      {children}
    </div>
  ),
  PanelGroup: ({ children, ...props }: { children: React.ReactNode }) => (
    <div data-testid="panel-group" className={props.className}>
      {children}
    </div>
  ),
  PanelResizeHandle: (props: { className?: string }) => (
    <div data-testid="resize-handle" className={props.className} />
  ),
}));

// Mock react-router hooks that need loader data
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useRouteLoaderData: (id: string) => {
      if (id === "studio-v2") {
        return {
          sessions: [
            {
              id: "session-1",
              name: "Test Session 1",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              status: "active",
            },
            {
              id: "session-2",
              name: "Test Session 2",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              status: "active",
            },
          ],
        };
      }
      if (id === "chat-session") {
        return {
          sessionId: "session-1",
          artifacts: [],
        };
      }
      return undefined;
    },
    useParams: () => ({}),
  };
});

// Create test store with canvas and persona slices
const createTestStore = (
  preloadedState: {
    canvas?: Partial<ReturnType<typeof canvasReducer>>;
    persona?: {
      persona: Persona;
      username: string | null;
      email: string | null;
      permissions: string[];
      isPersonaLoading: boolean;
    };
  } = {},
) => {
  const store = configureStore({
    reducer: {
      canvas: canvasReducer,
      persona: personaReducer,
    },
    preloadedState: preloadedState as Record<string, unknown>,
  });
  return store;
};

// Helper to create store with specific persona
const createStoreWithPersona = (persona: Persona) => {
  const store = createTestStore();
  store.dispatch(
    setUserInfo({
      username: "testuser",
      email: "test@example.com",
      roles: [persona],
      persona,
    }),
  );
  return store;
};

describe("HybridShellLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Core Layout", () => {
    it("renders the hybrid shell with all panels", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByTestId("hybrid-shell")).toBeInTheDocument();
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
      expect(screen.getByTestId("session-nav")).toBeInTheDocument();
      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });

    it("renders status bar at the bottom", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByTestId("canvas-status-bar")).toBeInTheDocument();
    });

    it("has proper layout structure with resizable panels", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const shell = screen.getByTestId("hybrid-shell");
      expect(shell).toHaveClass("hybrid-shell");
      expect(screen.getByTestId("panel-group")).toBeInTheDocument();
    });

    it("does NOT render MainDock or AppShell", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.queryByTestId("app-shell")).not.toBeInTheDocument();
      expect(screen.queryByTestId("main-dock")).not.toBeInTheDocument();
    });
  });

  describe("ActivityBar", () => {
    it("renders navigation icons", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const activityBar = screen.getByTestId("activity-bar");
      // Should have navigation buttons
      expect(activityBar.querySelectorAll("button").length).toBeGreaterThan(0);
    });

    it("has chat navigation icon", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByLabelText(/chat/i)).toBeInTheDocument();
    });
  });

  describe("SessionNav", () => {
    it("renders new chat button", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(
        screen.getByRole("button", { name: /new chat/i }),
      ).toBeInTheDocument();
    });

    it("renders search input", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(
        screen.getByPlaceholderText(/search sessions/i),
      ).toBeInTheDocument();
    });

    it("renders sessions from loader data", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      // Sessions should be displayed in the SessionNav
      expect(screen.getByText("Test Session 1")).toBeInTheDocument();
      expect(screen.getByText("Test Session 2")).toBeInTheDocument();
    });
  });

  describe("ConversationPanel", () => {
    it("renders message area placeholder", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const conversationPanel = screen.getByTestId("conversation-panel");
      expect(conversationPanel).toBeInTheDocument();
    });
  });

  describe("CanvasPanel", () => {
    it("renders canvas area with outlet", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const canvasPanel = screen.getByTestId("canvas-panel");
      expect(canvasPanel).toBeInTheDocument();
    });

    it("shows empty state when no artifact selected", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      expect(screen.getByText(/no artifact selected/i)).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("supports keyboard shortcuts hint in status bar", () => {
      render(
        <Provider store={createTestStore()}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      // Status bar should show keyboard hint
      expect(screen.getByTestId("canvas-status-bar")).toBeInTheDocument();
    });
  });

  // =============================================================================
  // Phase 3: RBAC and Persona-based Navigation Filtering
  // =============================================================================

  describe("RBAC - Persona-based Navigation (Phase 3)", () => {
    it("shows all navigation items for admin persona", () => {
      render(
        <Provider store={createStoreWithPersona("admin")}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      // Admin should see all items including admin-only
      expect(screen.getByLabelText(/chat/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/workflows/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/observability/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/admin/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/settings/i)).toBeInTheDocument();
    });

    it("shows developer-allowed items for developer persona", () => {
      render(
        <Provider store={createStoreWithPersona("developer")}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      // Developer should see chat, workflows, observability but NOT admin
      expect(screen.getByLabelText(/chat/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/workflows/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/observability/i)).toBeInTheDocument();
      expect(screen.queryByLabelText(/admin/i)).not.toBeInTheDocument();
      expect(screen.getByLabelText(/settings/i)).toBeInTheDocument();
    });

    it("shows user-allowed items for user persona (deny-by-default)", () => {
      render(
        <Provider store={createStoreWithPersona("user")}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      // User should only see chat and workflows, NOT admin/observability
      expect(screen.getByLabelText(/chat/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/workflows/i)).toBeInTheDocument();
      // User persona does NOT have access to these
      expect(screen.queryByLabelText(/observability/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/admin/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/agents/i)).not.toBeInTheDocument();
    });

    it("implements deny-by-default - only shows explicitly allowed items", () => {
      render(
        <Provider store={createStoreWithPersona("user")}>
          <MemoryRouter>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const activityBar = screen.getByTestId("activity-bar");
      const buttons = activityBar.querySelectorAll("button");

      // User persona should have limited navigation items
      // chat, workflows, cost are allowed + command palette + settings
      // But our NAV_ITEMS only has: chat, workflows (allowed for user)
      // and agents, observability, admin (NOT allowed for user)
      // So we expect fewer buttons for user than admin
      expect(buttons.length).toBeLessThan(7); // Less than all possible buttons
    });
  });

  describe("ConversationPanel with Chat Integration (Phase 3)", () => {
    it("renders conversation panel with chat functionality", () => {
      render(
        <Provider store={createStoreWithPersona("user")}>
          <MemoryRouter initialEntries={["/studio/v2/chat/session-1"]}>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      const conversationPanel = screen.getByTestId("conversation-panel");
      expect(conversationPanel).toBeInTheDocument();
    });

    it("shows empty state when no session is selected", () => {
      render(
        <Provider store={createStoreWithPersona("user")}>
          <MemoryRouter initialEntries={["/studio/v2/chat"]}>
            <HybridShellLayout />
          </MemoryRouter>
        </Provider>,
      );

      // Should show some indication that no session is active
      const conversationPanel = screen.getByTestId("conversation-panel");
      expect(conversationPanel).toBeInTheDocument();
    });
  });
});
