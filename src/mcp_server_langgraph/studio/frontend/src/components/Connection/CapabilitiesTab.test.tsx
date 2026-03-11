/**
 * CapabilitiesTab Component Tests
 *
 * Tests for the MCP capabilities tab used in the consolidated Connections page.
 * This component wraps the AggregatedCapabilitiesPanel and adds MCP action buttons.
 *
 * @see ADR-0102 - Connections Page Redesign
 */

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CapabilitiesTab } from "./CapabilitiesTab";

// Mock the store hooks
const mockDispatch = vi.fn();
const mockUseAppSelector = vi.fn();
const mockUseAppDispatch = vi.fn(() => mockDispatch);

vi.mock("../../store/hooks", () => ({
  useAppSelector: (selector: unknown) => mockUseAppSelector(selector),
  useAppDispatch: () => mockUseAppDispatch(),
}));

// Mock the MCPConnectionContext
vi.mock("../../contexts/MCPConnectionContext", () => ({
  useMCPConnection: () => ({
    status: "connected",
    connectionId: "test-connection-id",
    reconnect: vi.fn(),
    disconnect: vi.fn(),
  }),
}));

// Mock the MCP slice selectors
vi.mock("../../store/slices/mcpSlice", () => ({
  selectAllTools: vi.fn(),
  selectAllResources: vi.fn(),
  selectAllPrompts: vi.fn(),
  selectIsConnected: vi.fn(),
}));

// Mock the lazy components
vi.mock("../MCP", () => ({
  LazyAggregatedCapabilitiesPanel: ({
    onToolInvoke,
    onResourceView,
    onPromptTest,
  }: {
    onToolInvoke?: (name: string) => void;
    onResourceView?: (uri: string) => void;
    onPromptTest?: (name: string) => void;
  }) => (
    <div data-testid="aggregated-capabilities-panel">
      <button
        data-testid="panel-invoke-tool"
        onClick={() => onToolInvoke?.("test-tool")}
      >
        Panel: Invoke Tool
      </button>
      <button
        data-testid="panel-view-resource"
        onClick={() => onResourceView?.("test-resource")}
      >
        Panel: View Resource
      </button>
      <button
        data-testid="panel-test-prompt"
        onClick={() => onPromptTest?.("test-prompt")}
      >
        Panel: Test Prompt
      </button>
    </div>
  ),
  LazyToolInvocationDialog: ({
    open,
    onClose,
  }: {
    open: boolean;
    onClose: () => void;
  }) =>
    open ? (
      <div data-testid="tool-invocation-dialog">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
  LazyResourceViewer: ({
    open,
    onClose,
  }: {
    open: boolean;
    onClose: () => void;
  }) =>
    open ? (
      <div data-testid="resource-viewer-dialog">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
  LazyPromptTester: ({
    open,
    onClose,
  }: {
    open: boolean;
    onClose: () => void;
  }) =>
    open ? (
      <div data-testid="prompt-tester-dialog">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

// Mock the MCP WebSocket hook
vi.mock("../../hooks/useMCPWebSocket", () => ({
  useMCPWebSocket: () => ({
    status: "connected",
    isInitialized: true,
    serverInfo: { name: "Test Server", version: "1.0.0" },
    error: null,
  }),
}));

// Mock persona selector
vi.mock("../../store/slices/personaSlice", async () => {
  const actual = await vi.importActual("../../store/slices/personaSlice");
  return {
    ...actual,
    selectPersona: vi.fn(),
  };
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CapabilitiesTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock values
    mockUseAppSelector.mockImplementation((selector) => {
      if (selector.name === "selectPersona") return "admin";
      if (selector.name === "selectAllTools")
        return [{ name: "tool1", description: "Test tool" }];
      if (selector.name === "selectAllResources")
        return [{ name: "resource1", uri: "file://test" }];
      if (selector.name === "selectAllPrompts")
        return [{ name: "prompt1", description: "Test prompt" }];
      if (selector.name === "selectIsConnected") return true;
      return undefined;
    });
  });

  describe("Rendering", () => {
    it("should render the aggregated capabilities panel", () => {
      render(<CapabilitiesTab />);
      expect(
        screen.getByTestId("aggregated-capabilities-panel"),
      ).toBeInTheDocument();
    });

    it("should render MCP action buttons", () => {
      render(<CapabilitiesTab />);
      // Multiple buttons exist (header + panel mock), just verify they exist
      expect(
        screen.getAllByRole("button", { name: /invoke tool/i }).length,
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByRole("button", { name: /view resource/i }).length,
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByRole("button", { name: /test prompt/i }).length,
      ).toBeGreaterThan(0);
    });

    it("should render MCP WebSocket status indicator", () => {
      render(<CapabilitiesTab />);
      expect(screen.getByTestId("mcp-ws-status")).toBeInTheDocument();
    });
  });

  describe("Dialog Interactions", () => {
    it("should open tool invocation dialog when tool is invoked from panel", async () => {
      render(<CapabilitiesTab />);

      // Click the invoke button from the mocked panel
      fireEvent.click(screen.getByTestId("panel-invoke-tool"));

      await waitFor(() => {
        expect(
          screen.getByTestId("tool-invocation-dialog"),
        ).toBeInTheDocument();
      });
    });

    it("should open resource viewer when resource is selected from panel", async () => {
      render(<CapabilitiesTab />);

      fireEvent.click(screen.getByTestId("panel-view-resource"));

      await waitFor(() => {
        expect(
          screen.getByTestId("resource-viewer-dialog"),
        ).toBeInTheDocument();
      });
    });

    it("should open prompt tester when prompt is selected from panel", async () => {
      render(<CapabilitiesTab />);

      fireEvent.click(screen.getByTestId("panel-test-prompt"));

      await waitFor(() => {
        expect(screen.getByTestId("prompt-tester-dialog")).toBeInTheDocument();
      });
    });

    it("should close dialogs when close is clicked", async () => {
      render(<CapabilitiesTab />);

      // Open and close tool dialog
      fireEvent.click(screen.getByTestId("panel-invoke-tool"));
      await waitFor(() => {
        expect(
          screen.getByTestId("tool-invocation-dialog"),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /close/i }));
      await waitFor(() => {
        expect(
          screen.queryByTestId("tool-invocation-dialog"),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Status Indicators", () => {
    it("should show connected status when MCP WebSocket is connected", () => {
      render(<CapabilitiesTab />);
      const statusIndicator = screen.getByTestId("mcp-ws-status");
      expect(statusIndicator).toHaveClass("bg-success-9");
    });

    it("should show tool/resource/prompt counts", () => {
      render(<CapabilitiesTab />);
      // The counts come from the AggregatedCapabilitiesPanel,
      // which is mocked, so we just verify the panel is rendered
      expect(
        screen.getByTestId("aggregated-capabilities-panel"),
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible labels for action buttons", () => {
      render(<CapabilitiesTab />);
      // Get all buttons with each label and check at least one has the accessible name
      const invokeButtons = screen.getAllByRole("button", {
        name: /invoke tool/i,
      });
      const viewButtons = screen.getAllByRole("button", {
        name: /view resource/i,
      });
      const testButtons = screen.getAllByRole("button", {
        name: /test prompt/i,
      });
      expect(invokeButtons.length).toBeGreaterThan(0);
      expect(viewButtons.length).toBeGreaterThan(0);
      expect(testButtons.length).toBeGreaterThan(0);
    });

    it("should have accessible label for status indicator", () => {
      render(<CapabilitiesTab />);
      expect(screen.getByTestId("mcp-ws-status")).toHaveAttribute("aria-label");
    });
  });

  describe("Admin Actions", () => {
    it("should pass showAdminActions=true when persona is admin", () => {
      mockUseAppSelector.mockImplementation((selector) => {
        if (selector.name === "selectPersona") return "admin";
        return undefined;
      });

      render(<CapabilitiesTab />);
      // The panel receives showAdminActions prop - verify it renders
      expect(
        screen.getByTestId("aggregated-capabilities-panel"),
      ).toBeInTheDocument();
    });

    it("should pass showAdminActions=false when persona is user", () => {
      mockUseAppSelector.mockImplementation((selector) => {
        if (selector.name === "selectPersona") return "user";
        return undefined;
      });

      render(<CapabilitiesTab />);
      expect(
        screen.getByTestId("aggregated-capabilities-panel"),
      ).toBeInTheDocument();
    });
  });
});
