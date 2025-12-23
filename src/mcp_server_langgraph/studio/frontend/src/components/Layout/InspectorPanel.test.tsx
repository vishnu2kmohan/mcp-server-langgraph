/**
 * InspectorPanel Component Tests
 *
 * TDD tests for the MCP inspector panel component.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { InspectorPanel } from "./InspectorPanel";
import mcpReducer, { MCPServerState } from "../../store/slices/mcpSlice";

// Create test store
const createTestStore = (servers: Record<string, MCPServerState> = {}) => {
  return configureStore({
    reducer: {
      mcp: mcpReducer,
    },
    preloadedState: {
      mcp: {
        servers,
        error: null,
      },
    },
  });
};

const renderWithProviders = (
  ui: React.ReactElement,
  servers: Record<string, MCPServerState> = {},
) => {
  const store = createTestStore(servers);
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>),
  };
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("InspectorPanel", () => {
  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<InspectorPanel />);
      expect(screen.getByTestId("inspector-panel")).toBeInTheDocument();
    });

    it("should show empty state when no servers", () => {
      renderWithProviders(<InspectorPanel />);
      expect(
        screen.getByText(/select an mcp tool or resource to inspect/i),
      ).toBeInTheDocument();
    });

    it("should display server when present", () => {
      const servers = {
        "test-server": {
          id: "test-server",
          status: "connected" as const,
          tools: [],
          resources: [],
          prompts: [],
        },
      };
      renderWithProviders(<InspectorPanel />, servers);
      expect(screen.getByText("test-server")).toBeInTheDocument();
    });

    it("should display server status badge", () => {
      const servers = {
        "test-server": {
          id: "test-server",
          status: "connected" as const,
          tools: [],
          resources: [],
          prompts: [],
        },
      };
      renderWithProviders(<InspectorPanel />, servers);
      expect(screen.getByText("connected")).toBeInTheDocument();
    });

    it("should display server tools", () => {
      const servers = {
        "test-server": {
          id: "test-server",
          status: "connected" as const,
          tools: [
            { name: "calculator", description: "Math operations" },
            { name: "search", description: "Web search" },
          ],
          resources: [],
          prompts: [],
        },
      };
      renderWithProviders(<InspectorPanel />, servers);
      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("search")).toBeInTheDocument();
    });
  });

  describe("Status Styling", () => {
    it("should show green styling for connected status", () => {
      const servers = {
        "test-server": {
          id: "test-server",
          status: "connected" as const,
          tools: [],
          resources: [],
          prompts: [],
        },
      };
      renderWithProviders(<InspectorPanel />, servers);
      const badge = screen.getByText("connected");
      expect(badge).toHaveClass("text-green-700");
    });

    it("should show yellow styling for connecting status", () => {
      const servers = {
        "test-server": {
          id: "test-server",
          status: "connecting" as const,
          tools: [],
          resources: [],
          prompts: [],
        },
      };
      renderWithProviders(<InspectorPanel />, servers);
      const badge = screen.getByText("connecting");
      expect(badge).toHaveClass("text-yellow-700");
    });

    it("should show red styling for error status", () => {
      const servers = {
        "test-server": {
          id: "test-server",
          status: "error" as const,
          tools: [],
          resources: [],
          prompts: [],
        },
      };
      renderWithProviders(<InspectorPanel />, servers);
      const badge = screen.getByText("error");
      expect(badge).toHaveClass("text-red-700");
    });
  });

  describe("Props", () => {
    it("should accept className prop", () => {
      renderWithProviders(<InspectorPanel className="custom-class" />);
      expect(screen.getByTestId("inspector-panel")).toHaveClass("custom-class");
    });

    it("should accept compact prop for reduced spacing", () => {
      renderWithProviders(<InspectorPanel compact />);
      expect(screen.getByTestId("inspector-panel")).toHaveClass("p-2");
    });

    it("should accept selectedServerId prop to highlight server", () => {
      const servers = {
        "server-1": {
          id: "server-1",
          status: "connected" as const,
          tools: [],
          resources: [],
          prompts: [],
        },
        "server-2": {
          id: "server-2",
          status: "connected" as const,
          tools: [],
          resources: [],
          prompts: [],
        },
      };
      renderWithProviders(
        <InspectorPanel selectedServerId="server-1" />,
        servers,
      );
      const selectedServer = screen.getByTestId("server-card-server-1");
      expect(selectedServer).toHaveClass("ring-2");
    });
  });
});
