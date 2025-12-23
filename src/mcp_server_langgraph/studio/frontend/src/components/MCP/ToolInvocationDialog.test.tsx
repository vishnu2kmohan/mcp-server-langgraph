/**
 * ToolInvocationDialog Component Tests (TDD)
 *
 * Tests for the tool invocation dialog that allows users to:
 * - Select a tool from available tools
 * - Fill in tool arguments based on input schema
 * - Execute the tool and see results
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../../api";

// Mock the RTK Query hooks
const mockUseListMcpToolsQuery = vi.fn();
const mockUseInvokeMcpToolMutation = vi.fn();

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useListMcpToolsQuery: () => mockUseListMcpToolsQuery(),
    useInvokeMcpToolMutation: () => mockUseInvokeMcpToolMutation(),
  };
});

// Import after mocking
import { ToolInvocationDialog } from "./ToolInvocationDialog";

// =============================================================================
// Mock Data
// =============================================================================

const MOCK_TOOLS = {
  tools: [
    {
      name: "read_file",
      description: "Read contents of a file",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string", description: "File path to read" },
        },
        required: ["path"],
      },
    },
    {
      name: "write_file",
      description: "Write content to a file",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string", description: "File path to write" },
          content: { type: "string", description: "Content to write" },
        },
        required: ["path", "content"],
      },
    },
    {
      name: "list_directory",
      description: "List files in a directory",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string", description: "Directory path" },
        },
        required: ["path"],
      },
    },
  ],
};

const MOCK_TOOL_RESULT = {
  content: [
    {
      type: "text",
      text: "File contents: Hello World",
    },
  ],
  isError: false,
};

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const renderWithProvider = (ui: React.ReactElement) => {
  return render(<Provider store={createTestStore()}>{ui}</Provider>);
};

// =============================================================================
// Tests
// =============================================================================

describe("ToolInvocationDialog", () => {
  const mockOnClose = vi.fn();
  const mockInvokeTool = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockUseListMcpToolsQuery.mockReturnValue({
      data: MOCK_TOOLS,
      isLoading: false,
      error: null,
    });

    mockUseInvokeMcpToolMutation.mockReturnValue([
      mockInvokeTool,
      { isLoading: false, error: null },
    ]);
  });

  describe("rendering", () => {
    it("renders dialog when open", () => {
      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Invoke Tool")).toBeInTheDocument();
    });

    it("does not render when closed", () => {
      renderWithProvider(
        <ToolInvocationDialog open={false} onClose={mockOnClose} />
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("shows loading state when fetching tools", () => {
      mockUseListMcpToolsQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it("shows error state when tools fetch fails", () => {
      mockUseListMcpToolsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { message: "Failed to fetch tools" },
      });

      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  describe("tool selection", () => {
    it("displays list of available tools", () => {
      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      expect(screen.getByText("read_file")).toBeInTheDocument();
      expect(screen.getByText("write_file")).toBeInTheDocument();
      expect(screen.getByText("list_directory")).toBeInTheDocument();
    });

    it("shows tool description on selection", async () => {
      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      expect(screen.getByText("Read contents of a file")).toBeInTheDocument();
    });

    it("generates input fields from schema", async () => {
      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      expect(screen.getByLabelText(/path/i)).toBeInTheDocument();
    });
  });

  describe("tool invocation", () => {
    it("invokes tool with correct arguments", async () => {
      mockInvokeTool.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_TOOL_RESULT),
      });

      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      // Select tool
      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      // Fill in arguments
      const pathInput = screen.getByLabelText(/path/i);
      await userEvent.type(pathInput, "/tmp/test.txt");

      // Invoke tool
      const invokeButton = screen.getByRole("button", { name: /invoke/i });
      await userEvent.click(invokeButton);

      expect(mockInvokeTool).toHaveBeenCalledWith({
        name: "read_file",
        arguments: { path: "/tmp/test.txt" },
      });
    });

    it("displays tool result", async () => {
      mockInvokeTool.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_TOOL_RESULT),
      });

      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      // Select tool and fill in arguments
      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      const pathInput = screen.getByLabelText(/path/i);
      await userEvent.type(pathInput, "/tmp/test.txt");

      // Invoke tool
      const invokeButton = screen.getByRole("button", { name: /invoke/i });
      await userEvent.click(invokeButton);

      await waitFor(() => {
        expect(screen.getByText(/Hello World/)).toBeInTheDocument();
      });
    });

    it("shows loading state during invocation", async () => {
      mockInvokeTool.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      mockUseInvokeMcpToolMutation.mockReturnValue([
        mockInvokeTool,
        { isLoading: true, error: null },
      ]);

      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      // Select tool and fill required field
      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      const pathInput = screen.getByLabelText(/path/i);
      await userEvent.type(pathInput, "/tmp/test.txt");

      // Button should show "Invoking..." when loading
      const invokeButton = screen.getByRole("button", { name: /invoking/i });
      expect(invokeButton).toBeDisabled();
    });

    it("displays error result", async () => {
      const errorResult = {
        content: [{ type: "text", text: "File not found" }],
        isError: true,
      };
      mockInvokeTool.mockReturnValue({
        unwrap: () => Promise.resolve(errorResult),
      });

      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      // Select tool and fill in arguments
      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      const pathInput = screen.getByLabelText(/path/i);
      await userEvent.type(pathInput, "/nonexistent.txt");

      // Invoke tool
      const invokeButton = screen.getByRole("button", { name: /invoke/i });
      await userEvent.click(invokeButton);

      await waitFor(() => {
        expect(screen.getByText(/File not found/)).toBeInTheDocument();
      });
    });
  });

  describe("validation", () => {
    it("disables invoke button when required fields are empty", async () => {
      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      // Select tool but don't fill in arguments
      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      const invokeButton = screen.getByRole("button", { name: /invoke/i });
      expect(invokeButton).toBeDisabled();
    });

    it("enables invoke button when required fields are filled", async () => {
      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      // Select tool and fill in required field
      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      const pathInput = screen.getByLabelText(/path/i);
      await userEvent.type(pathInput, "/tmp/test.txt");

      const invokeButton = screen.getByRole("button", { name: /invoke/i });
      expect(invokeButton).toBeEnabled();
    });
  });

  describe("dialog actions", () => {
    it("calls onClose when cancel button clicked", async () => {
      renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await userEvent.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("resets form when dialog is reopened", async () => {
      const { rerender } = renderWithProvider(
        <ToolInvocationDialog open={true} onClose={mockOnClose} />
      );

      // Select tool and fill in arguments
      const toolSelect = screen.getByLabelText(/select tool/i);
      await userEvent.selectOptions(toolSelect, "read_file");

      // Verify tool was selected
      expect(screen.getByText("Read contents of a file")).toBeInTheDocument();

      // Close and reopen
      rerender(
        <Provider store={createTestStore()}>
          <ToolInvocationDialog open={false} onClose={mockOnClose} />
        </Provider>
      );

      rerender(
        <Provider store={createTestStore()}>
          <ToolInvocationDialog open={true} onClose={mockOnClose} />
        </Provider>
      );

      // Form should be reset
      expect(screen.queryByText("Read contents of a file")).not.toBeInTheDocument();
    });
  });
});
