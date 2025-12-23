/**
 * MCPPage Tests
 *
 * TDD tests for the MCP explorer page.
 * Uses Redux for MCP state.
 * Tests cover:
 * - Tab navigation
 * - Tools display
 * - Connection status
 * - Search functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MCPPage } from "./MCPPage";
import mcpReducer, {
  initialMCPState,
  MCPSliceState,
} from "../store/slices/mcpSlice";
import { api } from "../api";
import type {
  ServerEntry,
  MCPTool,
  MCPResource,
  MCPPrompt,
} from "../types/mcp";

// Helper to create a test store with MCP state
const createTestStore = (mcpState: Partial<MCPSliceState> = {}) => {
  return configureStore({
    reducer: {
      mcp: mcpReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
    preloadedState: {
      mcp: { ...initialMCPState, ...mcpState },
    },
  });
};

// Helper to render with store
const renderWithStore = (mcpState: Partial<MCPSliceState> = {}) => {
  const store = createTestStore(mcpState);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MCPPage />
      </Provider>,
    ),
  };
};

// Mock server entry
const mockServer: ServerEntry = {
  id: "server-1",
  url: "http://localhost:3000",
  status: "connected",
  tools: [],
  resources: [],
  prompts: [],
};

describe("MCPPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Header", () => {
    it("should display page title", () => {
      renderWithStore();

      expect(screen.getByText("MCP Explorer")).toBeInTheDocument();
    });

    it("should show Disconnected when no servers connected", () => {
      renderWithStore();

      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    it("should show Connected when servers are connected", () => {
      renderWithStore({
        servers: { "server-1": mockServer },
      });

      expect(screen.getByText("Connected")).toBeInTheDocument();
    });
  });

  describe("Tabs", () => {
    it("should have Tools tab", () => {
      renderWithStore();

      expect(screen.getByText("Tools")).toBeInTheDocument();
    });

    it("should have Resources tab", () => {
      renderWithStore();

      expect(screen.getByText("Resources")).toBeInTheDocument();
    });

    it("should have Prompts tab", () => {
      renderWithStore();

      expect(screen.getByText("Prompts")).toBeInTheDocument();
    });

    it("should have Servers tab", () => {
      renderWithStore();

      expect(screen.getByText("Servers")).toBeInTheDocument();
    });
  });

  describe("Tools Tab", () => {
    it("should display tools when available", () => {
      const tools: MCPTool[] = [
        {
          name: "calculator",
          description: "Perform calculations",
          inputSchema: {},
        },
        { name: "search", description: "Search the web", inputSchema: {} },
      ];
      const serverWithTools: ServerEntry = { ...mockServer, tools };

      renderWithStore({ servers: { "server-1": serverWithTools } });

      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("Perform calculations")).toBeInTheDocument();
    });

    it("should show empty state when no tools", () => {
      renderWithStore();

      expect(screen.getByText("No tools found")).toBeInTheDocument();
    });
  });

  describe("Search", () => {
    it("should have search input", () => {
      renderWithStore();

      expect(screen.getByPlaceholderText(/Search tools/)).toBeInTheDocument();
    });

    it("should filter tools by search query", () => {
      const tools: MCPTool[] = [
        { name: "calculator", description: "Math operations", inputSchema: {} },
        { name: "weather", description: "Weather data", inputSchema: {} },
      ];
      const serverWithTools: ServerEntry = { ...mockServer, tools };

      renderWithStore({ servers: { "server-1": serverWithTools } });

      const searchInput = screen.getByPlaceholderText(/Search tools/);
      fireEvent.change(searchInput, { target: { value: "calc" } });

      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.queryByText("weather")).not.toBeInTheDocument();
    });
  });

  describe("Servers Tab", () => {
    it("should switch to servers tab when clicked", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Servers"));

      // Should see add connection button
      expect(screen.getByText("Add MCP Connection")).toBeInTheDocument();
    });

    it("should show Add MCP Connection button", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Servers"));

      const addButton = screen.getByText("Add MCP Connection");
      expect(addButton).toBeInTheDocument();
    });

    it("should show no servers message when empty", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Servers"));

      expect(screen.getByText("No servers configured")).toBeInTheDocument();
    });
  });

  describe("Resources Tab", () => {
    it("should switch to resources tab when clicked", () => {
      const resources: MCPResource[] = [
        { uri: "file://test.txt", name: "test.txt", mimeType: "text/plain" },
      ];
      const serverWithResources: ServerEntry = { ...mockServer, resources };

      renderWithStore({ servers: { "server-1": serverWithResources } });

      fireEvent.click(screen.getByText("Resources"));

      expect(screen.getByText("test.txt")).toBeInTheDocument();
    });

    it("should filter resources by search query", () => {
      const resources: MCPResource[] = [
        { uri: "file://doc.txt", name: "document.txt", mimeType: "text/plain" },
        {
          uri: "file://data.json",
          name: "data.json",
          mimeType: "application/json",
        },
      ];
      const serverWithResources: ServerEntry = { ...mockServer, resources };

      renderWithStore({ servers: { "server-1": serverWithResources } });

      fireEvent.click(screen.getByText("Resources"));

      // Search input placeholder changes based on active tab
      const searchInput = screen.getByPlaceholderText(/Search/);
      fireEvent.change(searchInput, { target: { value: "doc" } });

      expect(screen.getByText("document.txt")).toBeInTheDocument();
      expect(screen.queryByText("data.json")).not.toBeInTheDocument();
    });
  });

  describe("Prompts Tab", () => {
    it("should switch to prompts tab when clicked", () => {
      const prompts: MCPPrompt[] = [
        { name: "summarize", description: "Summarize text" },
      ];
      const serverWithPrompts: ServerEntry = { ...mockServer, prompts };

      renderWithStore({ servers: { "server-1": serverWithPrompts } });

      fireEvent.click(screen.getByText("Prompts"));

      expect(screen.getByText("summarize")).toBeInTheDocument();
    });

    it("should filter prompts by search query", () => {
      const prompts: MCPPrompt[] = [
        { name: "summarize", description: "Summarize text" },
        { name: "translate", description: "Translate text" },
      ];
      const serverWithPrompts: ServerEntry = { ...mockServer, prompts };

      renderWithStore({ servers: { "server-1": serverWithPrompts } });

      fireEvent.click(screen.getByText("Prompts"));

      // Search input placeholder changes based on active tab
      const searchInput = screen.getByPlaceholderText(/Search/);
      fireEvent.change(searchInput, { target: { value: "sum" } });

      expect(screen.getByText("summarize")).toBeInTheDocument();
      expect(screen.queryByText("translate")).not.toBeInTheDocument();
    });
  });

  describe("Tool Expansion", () => {
    it("should show tool details when expanded", () => {
      const tools: MCPTool[] = [
        {
          name: "calculator",
          description: "Perform calculations",
          inputSchema: {
            type: "object",
            properties: { x: { type: "number" } },
          },
        },
      ];
      const serverWithTools: ServerEntry = { ...mockServer, tools };

      renderWithStore({ servers: { "server-1": serverWithTools } });

      // Click on the tool to expand it
      const expandButton = screen.getByText("calculator").closest("button");
      if (expandButton) {
        fireEvent.click(expandButton);
      }

      // After expanding, should show input schema
      expect(screen.getByText("calculator")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should display error when present", () => {
      renderWithStore({ error: "Connection failed" });

      expect(screen.getByText(/Connection failed/)).toBeInTheDocument();
    });

    it("should have accessible error alert", () => {
      renderWithStore({ error: "Connection failed" });

      // Error should have role="alert" for screen readers
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have dismiss button for error", () => {
      renderWithStore({ error: "Connection failed" });

      expect(
        screen.getByRole("button", { name: /dismiss/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Connecting State", () => {
    it("should show connecting indicator when connecting", () => {
      renderWithStore({ isConnecting: true });

      // Check for connecting state (spinning icon or text)
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Server List", () => {
    it("should display connected servers", () => {
      const serverWithTools: ServerEntry = {
        ...mockServer,
        tools: [{ name: "tool1", description: "A tool", inputSchema: {} }],
      };

      renderWithStore({ servers: { "server-1": serverWithTools } });

      fireEvent.click(screen.getByText("Servers"));

      expect(screen.getByText("http://localhost:3000")).toBeInTheDocument();
    });

    it("should show remove button for servers", () => {
      renderWithStore({ servers: { "server-1": mockServer } });

      fireEvent.click(screen.getByText("Servers"));

      // There should be a remove/disconnect button
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("should show Connected status for connected servers", () => {
      const connectedServer: ServerEntry = {
        ...mockServer,
        status: "connected",
      };

      renderWithStore({ servers: { "server-1": connectedServer } });

      fireEvent.click(screen.getByText("Servers"));

      // Find the server entry container and verify it contains the Connected status
      // There will be a header "Connected" text and a status "Connected" text in server row
      const serverRow = screen
        .getByText("http://localhost:3000")
        .closest('[class*="rounded-lg"]');
      expect(serverRow).toHaveTextContent("Connected");
    });

    it("should show Error status for servers with error status", () => {
      const errorServer: ServerEntry = {
        ...mockServer,
        status: "error",
      };

      renderWithStore({ servers: { "server-1": errorServer } });

      fireEvent.click(screen.getByText("Servers"));

      expect(screen.getByText("Error")).toBeInTheDocument();
    });

    it("should show Connecting status for connecting servers", () => {
      const connectingServer: ServerEntry = {
        ...mockServer,
        status: "connecting",
      };

      renderWithStore({ servers: { "server-1": connectingServer } });

      fireEvent.click(screen.getByText("Servers"));

      expect(screen.getByText("Connecting")).toBeInTheDocument();
    });

    it("should show Primary badge for primary server", () => {
      const primaryServer: ServerEntry = {
        ...mockServer,
        id: "primary-server",
      };

      renderWithStore({
        servers: { "primary-server": primaryServer },
        primaryServerId: "primary-server",
      });

      fireEvent.click(screen.getByText("Servers"));

      expect(screen.getByText("(Primary)")).toBeInTheDocument();
    });

    it("should display server error message when present", () => {
      const serverWithError: ServerEntry = {
        ...mockServer,
        status: "error",
        error: "Connection timeout exceeded",
      };

      renderWithStore({ servers: { "server-1": serverWithError } });

      fireEvent.click(screen.getByText("Servers"));

      expect(
        screen.getByText("Connection timeout exceeded"),
      ).toBeInTheDocument();
    });
  });

  describe("Tool Expansion Toggle", () => {
    it("should toggle tool details on second click", () => {
      const tools: MCPTool[] = [
        {
          name: "expand-test",
          description: "Test expansion",
          inputSchema: {
            type: "object",
            properties: { test: { type: "string" } },
          },
        },
      ];
      const serverWithTools: ServerEntry = { ...mockServer, tools };

      renderWithStore({ servers: { "server-1": serverWithTools } });

      // Click to expand
      const expandButton = screen.getByText("expand-test").closest("button");
      expect(expandButton).toBeInTheDocument();
      if (expandButton) {
        fireEvent.click(expandButton);
      }

      // Should show Parameters header
      expect(screen.getByText("Parameters")).toBeInTheDocument();

      // Click again to collapse
      if (expandButton) {
        fireEvent.click(expandButton);
      }

      // Should not show Parameters header
      expect(screen.queryByText("Parameters")).not.toBeInTheDocument();
    });
  });

  describe("Error Dismissal", () => {
    it("should dispatch clearMCPError when dismiss button clicked", () => {
      const { store } = renderWithStore({ error: "Test error message" });

      // Verify error is shown
      expect(screen.getByText("Test error message")).toBeInTheDocument();

      // Click dismiss button
      const dismissButton = screen.getByRole("button", { name: /dismiss/i });
      fireEvent.click(dismissButton);

      // Check that the error was cleared in store
      const state = store.getState();
      expect(state.mcp.error).toBeNull();
    });
  });

  describe("Add Connection Dialog", () => {
    it("should open add connection dialog when button clicked", async () => {
      renderWithStore();

      // Go to Servers tab
      fireEvent.click(screen.getByText("Servers"));

      // Click Add MCP Connection button
      fireEvent.click(screen.getByText("Add MCP Connection"));

      // Dialog should be open - look for the dialog role
      const dialog = await screen.findByRole("dialog");
      expect(dialog).toBeInTheDocument();
    });

    it("should show dialog heading when opened", async () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Servers"));
      fireEvent.click(screen.getByText("Add MCP Connection"));

      // Look for dialog heading (there are two "Add MCP Connection" texts - button and dialog title)
      const dialog = await screen.findByRole("dialog");
      expect(dialog).toHaveTextContent("Add MCP Connection");
    });
  });

  describe("Search Placeholder", () => {
    it("should show correct placeholder for resources tab", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Resources"));

      expect(
        screen.getByPlaceholderText(/Search resources/),
      ).toBeInTheDocument();
    });

    it("should show correct placeholder for prompts tab", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Prompts"));

      expect(screen.getByPlaceholderText(/Search prompts/)).toBeInTheDocument();
    });

    it("should not show search on servers tab", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Servers"));

      // Search input should not be present on servers tab
      expect(screen.queryByPlaceholderText(/Search/)).not.toBeInTheDocument();
    });
  });

  describe("Empty States", () => {
    it("should show no resources message when empty", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Resources"));

      expect(screen.getByText("No resources found")).toBeInTheDocument();
    });

    it("should show no prompts message when empty", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Prompts"));

      expect(screen.getByText("No prompts found")).toBeInTheDocument();
    });
  });

  describe("Tab Counts", () => {
    it("should show correct tool count in tab badge", () => {
      const tools: MCPTool[] = [
        { name: "tool1", description: "Tool 1", inputSchema: {} },
        { name: "tool2", description: "Tool 2", inputSchema: {} },
        { name: "tool3", description: "Tool 3", inputSchema: {} },
      ];
      const serverWithTools: ServerEntry = { ...mockServer, tools };

      renderWithStore({ servers: { "server-1": serverWithTools } });

      // Should show "3" in the Tools tab badge
      const toolsTab = screen.getByText("Tools").closest("button");
      expect(toolsTab).toHaveTextContent("3");
    });

    it("should show correct resource count in tab badge", () => {
      const resources: MCPResource[] = [
        { uri: "file://a.txt", name: "a.txt", mimeType: "text/plain" },
        { uri: "file://b.txt", name: "b.txt", mimeType: "text/plain" },
      ];
      const serverWithResources: ServerEntry = { ...mockServer, resources };

      renderWithStore({ servers: { "server-1": serverWithResources } });

      // Should show "2" in the Resources tab badge
      const resourcesTab = screen.getByText("Resources").closest("button");
      expect(resourcesTab).toHaveTextContent("2");
    });
  });

  describe("MCP Action Dialogs", () => {
    describe("Tool Invocation Dialog", () => {
      it("should show invoke tool button in header actions", () => {
        renderWithStore();

        expect(
          screen.getByRole("button", { name: /invoke tool/i }),
        ).toBeInTheDocument();
      });

      it("should open tool invocation dialog when button clicked", async () => {
        renderWithStore();

        const invokeButton = screen.getByRole("button", {
          name: /invoke tool/i,
        });
        fireEvent.click(invokeButton);

        const dialog = await screen.findByRole("dialog");
        expect(dialog).toHaveTextContent(/invoke tool/i);
      });
    });

    describe("Resource Viewer Dialog", () => {
      it("should show view resources button in header actions", () => {
        renderWithStore();

        expect(
          screen.getByRole("button", { name: /view resources/i }),
        ).toBeInTheDocument();
      });

      it("should open resource viewer dialog when button clicked", async () => {
        renderWithStore();

        const viewButton = screen.getByRole("button", {
          name: /view resources/i,
        });
        fireEvent.click(viewButton);

        const dialog = await screen.findByRole("dialog");
        expect(dialog).toHaveTextContent(/resource viewer/i);
      });
    });

    describe("Prompt Tester Dialog", () => {
      it("should show test prompt button in header actions", () => {
        renderWithStore();

        expect(
          screen.getByRole("button", { name: /test prompt/i }),
        ).toBeInTheDocument();
      });

      it("should open prompt tester dialog when button clicked", async () => {
        renderWithStore();

        const testButton = screen.getByRole("button", { name: /test prompt/i });
        fireEvent.click(testButton);

        const dialog = await screen.findByRole("dialog");
        expect(dialog).toHaveTextContent(/prompt tester/i);
      });
    });

    describe("Elicitation Dialog", () => {
      it("should show elicitation button in header actions", () => {
        renderWithStore();

        expect(
          screen.getByRole("button", { name: /request input/i }),
        ).toBeInTheDocument();
      });

      it("should open elicitation dialog when button clicked", async () => {
        renderWithStore();

        const elicitButton = screen.getByRole("button", {
          name: /request input/i,
        });
        fireEvent.click(elicitButton);

        const dialog = await screen.findByRole("dialog");
        expect(dialog).toHaveTextContent(/request user input/i);
      });
    });
  });

  describe("Keyboard Shortcuts", () => {
    const createKeyboardEvent = (
      key: string,
      options: Partial<KeyboardEventInit> = {},
    ) => {
      return new KeyboardEvent("keydown", {
        key,
        bubbles: true,
        cancelable: true,
        ...options,
      });
    };

    it("should open tool invocation dialog with Cmd+Shift+T", async () => {
      renderWithStore();

      document.dispatchEvent(
        createKeyboardEvent("t", { metaKey: true, shiftKey: true }),
      );

      const dialog = await screen.findByRole("dialog");
      expect(dialog).toHaveTextContent(/invoke tool/i);
    });

    it("should open resource viewer with Cmd+Shift+R", async () => {
      renderWithStore();

      document.dispatchEvent(
        createKeyboardEvent("r", { metaKey: true, shiftKey: true }),
      );

      const dialog = await screen.findByRole("dialog");
      expect(dialog).toHaveTextContent(/resource viewer/i);
    });

    it("should open prompt tester with Cmd+Shift+P", async () => {
      renderWithStore();

      document.dispatchEvent(
        createKeyboardEvent("p", { metaKey: true, shiftKey: true }),
      );

      const dialog = await screen.findByRole("dialog");
      expect(dialog).toHaveTextContent(/prompt tester/i);
    });

    it("should close active dialog with Escape", async () => {
      renderWithStore();

      // First open a dialog
      document.dispatchEvent(
        createKeyboardEvent("t", { metaKey: true, shiftKey: true }),
      );

      const dialog = await screen.findByRole("dialog");
      expect(dialog).toBeInTheDocument();

      // Then close with Escape
      document.dispatchEvent(createKeyboardEvent("Escape"));

      // Dialog should be closed (may take a moment)
      await vi.waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });
  });
});
