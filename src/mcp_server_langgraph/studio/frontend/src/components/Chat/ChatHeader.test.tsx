/**
 * ChatHeader Tests
 *
 * Tests for the chat header component with connection status,
 * session info, and action buttons.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ChatHeader } from "./ChatHeader";

// Mock the RTK Query API hooks used by SaveAsWorkflowButton
vi.mock("../../api", () => ({
  useBootstrapWorkflowMutation: () => [
    vi.fn(),
    { isLoading: false, isSuccess: false, data: null, error: null },
  ],
}));

// Create a minimal store for tests
const createTestStore = () => {
  return configureStore({
    reducer: {
      api: () => ({}),
    },
  });
};

// Wrapper component with Provider
const renderWithProvider = (ui: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{ui}</Provider>);
};

describe("ChatHeader", () => {
  const defaultProps = {
    connectionMode: "websocket" as const,
    isReconnecting: false,
    reconnectAttempts: 0,
    sessionName: "Test Session",
    messageCount: 5,
    onConnect: vi.fn(),
    onClear: vi.fn(),
    sessionId: "session-123",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Connection Status", () => {
    it("should show connected status when websocket mode", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} connectionMode="websocket" />,
      );
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    it("should show REST status when rest mode", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} connectionMode="rest" />,
      );
      expect(screen.getByText("REST")).toBeInTheDocument();
    });

    it("should show disconnected status when disconnected", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} connectionMode="disconnected" />,
      );
      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    it("should show reconnecting status with attempt count", () => {
      renderWithProvider(
        <ChatHeader
          {...defaultProps}
          isReconnecting={true}
          reconnectAttempts={3}
        />,
      );
      expect(screen.getByText("Reconnecting (3/5)...")).toBeInTheDocument();
    });
  });

  describe("Session Info", () => {
    it("should display session name", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} sessionName="My Session" />,
      );
      expect(screen.getByText("My Session")).toBeInTheDocument();
    });

    it("should display message count", () => {
      renderWithProvider(<ChatHeader {...defaultProps} messageCount={10} />);
      expect(screen.getByText("10 messages")).toBeInTheDocument();
    });

    it("should display singular message when count is 1", () => {
      renderWithProvider(<ChatHeader {...defaultProps} messageCount={1} />);
      expect(screen.getByText("1 message")).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should render clear button", () => {
      renderWithProvider(<ChatHeader {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /clear/i }),
      ).toBeInTheDocument();
    });

    it("should call onClear when clear button is clicked", () => {
      renderWithProvider(<ChatHeader {...defaultProps} />);
      const clearButton = screen.getByRole("button", { name: /clear/i });
      fireEvent.click(clearButton);
      expect(defaultProps.onClear).toHaveBeenCalledOnce();
    });

    it("should render SaveAsWorkflowButton when sessionId provided", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} sessionId="session-123" />,
      );
      // SaveAsWorkflowButton renders as a button
      expect(
        screen.getByRole("button", { name: /save as workflow/i }),
      ).toBeInTheDocument();
    });

    it("should not render actions when no session", () => {
      renderWithProvider(
        <ChatHeader
          {...defaultProps}
          sessionId={undefined}
          sessionName={undefined}
        />,
      );
      expect(
        screen.queryByRole("button", { name: /clear/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display MCP error when provided", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} mcpError="MCP connection failed" />,
      );
      expect(screen.getByText("MCP connection failed")).toBeInTheDocument();
    });

    it("should show retry button when MCP error exists", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} mcpError="Connection error" />,
      );
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should call onConnect when retry is clicked", () => {
      renderWithProvider(<ChatHeader {...defaultProps} mcpError="Error" />);
      const retryButton = screen.getByRole("button", { name: /retry/i });
      fireEvent.click(retryButton);
      expect(defaultProps.onConnect).toHaveBeenCalledOnce();
    });

    it("should display session error when provided", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} sessionError="Failed to load session" />,
      );
      expect(screen.getByText("Failed to load session")).toBeInTheDocument();
    });

    it("should show dismiss button for session error", () => {
      const onClearError = vi.fn();
      renderWithProvider(
        <ChatHeader
          {...defaultProps}
          sessionError="Error"
          onClearError={onClearError}
        />,
      );
      const dismissButton = screen.getByRole("button", { name: /dismiss/i });
      fireEvent.click(dismissButton);
      expect(onClearError).toHaveBeenCalledOnce();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible connection status", () => {
      renderWithProvider(
        <ChatHeader {...defaultProps} connectionMode="websocket" />,
      );
      // Connection status should be visually indicated
      const statusElement = screen.getByText("Connected");
      expect(statusElement).toBeInTheDocument();
    });

    it("should have accessible action buttons", () => {
      renderWithProvider(<ChatHeader {...defaultProps} />);
      const clearButton = screen.getByRole("button", { name: /clear/i });
      expect(clearButton).toBeInTheDocument();
    });
  });
});
