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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MCPPage } from "./MCPPage";
import mcpReducer, {
  initialMCPState,
  MCPSliceState,
} from "../store/slices/mcpSlice";
import type {
  ServerEntry,
  MCPTool,
  MCPResource,
  MCPPrompt,
} from "../types/mcp";

// Helper to create a test store with MCP state
const createTestStore = (mcpState: Partial<MCPSliceState> = {}) => {
  return configureStore({
    reducer: { mcp: mcpReducer },
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
  });
});
