/**
 * CommandPalette Tests
 *
 * Tests for the Cmd+K command palette component.
 * Features:
 * - Keyboard shortcut activation (Cmd+K / Ctrl+K)
 * - Search filtering
 * - Navigation actions
 * - Keyboard navigation (arrow keys, enter, escape)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { CommandPalette } from "./CommandPalette";
import personaReducer from "../../store/slices/personaSlice";
import authReducer from "../../store/slices/authSlice";
import { TestRouter } from "../../test-utils";

// Mock navigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Create test store
const createTestStore = (persona: "admin" | "developer" | "user" = "admin") => {
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
        user: {
          id: "user-1",
          username: "testuser",
          email: "test@example.com",
          roles: persona === "admin" ? ["admin"] : ["user"],
          persona,
        },
        tokens: null,
        currentOrg: null,
        organizations: [],
        isInitializing: false,
        isLoading: false,
        error: null,
      },
    },
  });
};

const renderWithProviders = (
  persona: "admin" | "developer" | "user" = "admin",
) => {
  const store = createTestStore(persona);
  return render(
    <Provider store={store}>
      <TestRouter>
        <CommandPalette />
      </TestRouter>
    </Provider>,
  );
};

describe("CommandPalette", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Visibility", () => {
    it("should not be visible by default", () => {
      renderWithProviders();
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should open on Cmd+K keydown", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("should open on Ctrl+K keydown", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", ctrlKey: true });

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("should close on Escape keydown", async () => {
      renderWithProviders();

      // Open
      fireEvent.keyDown(document, { key: "k", metaKey: true });
      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Close
      fireEvent.keyDown(document, { key: "Escape" });
      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });

    it("should close when clicking backdrop", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });
      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Click backdrop
      const backdrop = screen.getByTestId("command-palette-backdrop");
      fireEvent.click(backdrop);

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });
  });

  describe("Search Input", () => {
    it("should render search input when open", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
      });
    });

    it("should focus search input on open", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        const input = screen.getByPlaceholderText(/search/i);
        expect(document.activeElement).toBe(input);
      });
    });

    it("should filter commands based on search", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/search/i);
      await userEvent.type(input, "chat");

      // Should show chat-related commands (CHAT group header exists)
      await waitFor(() => {
        expect(screen.getByText("CHAT")).toBeInTheDocument();
        expect(screen.getByText("Go to Chat")).toBeInTheDocument();
      });
    });
  });

  describe("Command Groups", () => {
    it("should show CHAT group", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("CHAT")).toBeInTheDocument();
      });
    });

    it("should show NAVIGATION group", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("NAVIGATION")).toBeInTheDocument();
      });
    });

    it("should show WORKFLOW group for admin", async () => {
      renderWithProviders("admin");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("WORKFLOW")).toBeInTheDocument();
      });
    });

    it("should NOT show ADMIN group for user persona", async () => {
      renderWithProviders("user");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.queryByText("ADMIN")).not.toBeInTheDocument();
      });
    });
  });

  describe("Navigation Commands", () => {
    it("should show Go to Chat command", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Go to Chat")).toBeInTheDocument();
      });
    });

    it("should show Go to Projects command", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Go to Projects")).toBeInTheDocument();
      });
    });

    it("should navigate when command is clicked", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Go to Chat")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Go to Chat"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/chat");
    });

    it("should close palette after navigation", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Go to Chat")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Go to Chat"));

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });
  });

  describe("Keyboard Navigation", () => {
    it("should highlight first command by default", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        const firstCommand = screen.getAllByRole("button", {
          name: /ask ai|go to|new|clear|toggle|get ai|shared/i,
        })[0];
        expect(firstCommand).toHaveAttribute("data-selected", "true");
      });
    });

    it("should move selection down with ArrowDown", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      fireEvent.keyDown(document, { key: "ArrowDown" });

      // Second command should be selected
      await waitFor(() => {
        const commands = screen.getAllByRole("button", {
          name: /ask ai|go to|new|clear|toggle|get ai|shared/i,
        });
        expect(commands[1]).toHaveAttribute("data-selected", "true");
      });
    });

    it("should move selection up with ArrowUp", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Move down first
      fireEvent.keyDown(document, { key: "ArrowDown" });
      fireEvent.keyDown(document, { key: "ArrowUp" });

      // First command should be selected again
      await waitFor(() => {
        const commands = screen.getAllByRole("button", {
          name: /ask ai|go to|new|clear|toggle|get ai|shared/i,
        });
        expect(commands[0]).toHaveAttribute("data-selected", "true");
      });
    });

    it("should execute selected command on Enter", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      fireEvent.keyDown(document, { key: "Enter" });

      // First command should have been executed
      expect(mockNavigate).toHaveBeenCalled();
    });
  });

  describe("Keyboard Shortcuts Display", () => {
    it("should show keyboard shortcuts for commands", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        // Should show shortcut hints like "⌘N" or "Ctrl+N" - use getAllByText since there are multiple shortcuts
        const shortcuts = screen.getAllByText(/⌘|ctrl/i);
        expect(shortcuts.length).toBeGreaterThan(0);
      });
    });
  });

  describe("RBAC Filtering", () => {
    it("should show admin commands for admin persona", async () => {
      renderWithProviders("admin");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("ADMIN")).toBeInTheDocument();
        expect(screen.getByText("Go to Admin Dashboard")).toBeInTheDocument();
      });
    });

    it("should show workflow commands for developer persona", async () => {
      renderWithProviders("developer");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("WORKFLOW")).toBeInTheDocument();
        expect(screen.getByText("Go to Workflows")).toBeInTheDocument();
      });
    });

    it("should only show basic commands for user persona", async () => {
      renderWithProviders("user");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("AI")).toBeInTheDocument();
        expect(screen.getByText("CHAT")).toBeInTheDocument();
        expect(screen.getByText("WORKFLOW")).toBeInTheDocument(); // Users can now see Shared Workflows
        expect(screen.queryByText("ADMIN")).not.toBeInTheDocument();
      });
    });
  });

  describe("Action Commands", () => {
    it("should show New Session command", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });
    });

    it("should show Clear Messages command", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Clear Messages")).toBeInTheDocument();
      });
    });
  });

  describe("AI Commands", () => {
    it("should show AI Assistant command for all personas", async () => {
      renderWithProviders("user");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("AI")).toBeInTheDocument();
        expect(screen.getByText("Ask AI Assistant")).toBeInTheDocument();
      });
    });

    it("should show Get Suggestions command for developers", async () => {
      renderWithProviders("developer");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Get AI Suggestions")).toBeInTheDocument();
      });
    });

    it("should show Toggle Voice command", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Toggle Voice Input")).toBeInTheDocument();
      });
    });

    it("should navigate to chat when Ask AI Assistant is clicked", async () => {
      renderWithProviders();

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Ask AI Assistant")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Ask AI Assistant"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/chat");
    });
  });

  describe("Shared Workflows Command", () => {
    it("should show Shared Workflows command for user persona", async () => {
      renderWithProviders("user");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Shared Workflows")).toBeInTheDocument();
      });
    });

    it("should navigate to shared workflows page", async () => {
      renderWithProviders("user");

      fireEvent.keyDown(document, { key: "k", metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("Shared Workflows")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Shared Workflows"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/shared-workflows");
    });
  });
});
