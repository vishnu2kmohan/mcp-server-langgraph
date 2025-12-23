/**
 * ElicitationDialog Component Tests (TDD)
 *
 * Tests for the elicitation dialog that allows users to:
 * - Request user input through MCP elicitation
 * - Define JSON schemas for structured input
 * - Handle accept/decline actions
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../../api";

// Mock the RTK Query hooks
const mockUseRequestMcpElicitationMutation = vi.fn();

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useRequestMcpElicitationMutation: () =>
      mockUseRequestMcpElicitationMutation(),
  };
});

// Import after mocking
import { ElicitationDialog } from "./ElicitationDialog";

// =============================================================================
// Mock Data
// =============================================================================

const MOCK_ELICITATION_ACCEPT = {
  action: "accept",
  content: { name: "John Doe", email: "john@example.com" },
};

const MOCK_ELICITATION_DECLINE = {
  action: "decline",
  content: null,
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

describe("ElicitationDialog", () => {
  const mockOnClose = vi.fn();
  const mockRequestElicitation = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseRequestMcpElicitationMutation.mockReturnValue([
      mockRequestElicitation,
      { isLoading: false, error: null },
    ]);
  });

  describe("rendering", () => {
    it("renders dialog when open", () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Request User Input")).toBeInTheDocument();
    });

    it("does not render when closed", () => {
      renderWithProvider(
        <ElicitationDialog open={false} onClose={mockOnClose} />,
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  describe("message input", () => {
    it("has a message textarea", () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
    });

    it("allows entering a message", async () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Please enter your details");

      expect(messageInput).toHaveValue("Please enter your details");
    });
  });

  describe("schema input", () => {
    it("has an optional schema textarea", () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      expect(screen.getByLabelText(/schema/i)).toBeInTheDocument();
    });

    it("allows entering a JSON schema", async () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      const schemaInput = screen.getByLabelText(/schema/i);
      const schema = JSON.stringify({
        type: "object",
        properties: { name: { type: "string" } },
      });
      // Use fireEvent for JSON strings with braces
      fireEvent.change(schemaInput, { target: { value: schema } });

      expect(schemaInput).toHaveValue(schema);
    });

    it("shows validation error for invalid JSON", async () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      const schemaInput = screen.getByLabelText(/schema/i);
      // Use fireEvent for invalid JSON with braces
      fireEvent.change(schemaInput, { target: { value: "{ invalid json" } });

      // Should show a validation error (wait for state update)
      await waitFor(() => {
        expect(screen.getByText("Invalid JSON schema")).toBeInTheDocument();
      });
    });
  });

  describe("elicitation request", () => {
    it("sends elicitation request with message", async () => {
      mockRequestElicitation.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_ELICITATION_ACCEPT),
      });

      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      // Enter message
      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your name");

      // Send request
      const sendButton = screen.getByRole("button", { name: /send/i });
      await userEvent.click(sendButton);

      expect(mockRequestElicitation).toHaveBeenCalledWith({
        message: "Enter your name",
        schema: null,
      });
    });

    it("sends elicitation request with schema", async () => {
      mockRequestElicitation.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_ELICITATION_ACCEPT),
      });

      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      // Enter message
      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your details");

      // Enter schema (use fireEvent for JSON with braces)
      const schemaInput = screen.getByLabelText(/schema/i);
      const schema = {
        type: "object",
        properties: { name: { type: "string" } },
      };
      fireEvent.change(schemaInput, {
        target: { value: JSON.stringify(schema) },
      });

      // Send request
      const sendButton = screen.getByRole("button", { name: /send/i });
      await userEvent.click(sendButton);

      expect(mockRequestElicitation).toHaveBeenCalledWith({
        message: "Enter your details",
        schema: schema,
      });
    });

    it("displays accept response", async () => {
      mockRequestElicitation.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_ELICITATION_ACCEPT),
      });

      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      // Enter message and send
      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your name");

      const sendButton = screen.getByRole("button", { name: /send/i });
      await userEvent.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText(/accepted/i)).toBeInTheDocument();
        expect(screen.getByText(/John Doe/)).toBeInTheDocument();
      });
    });

    it("displays decline response", async () => {
      mockRequestElicitation.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_ELICITATION_DECLINE),
      });

      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      // Enter message and send
      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your name");

      const sendButton = screen.getByRole("button", { name: /send/i });
      await userEvent.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText(/declined/i)).toBeInTheDocument();
      });
    });

    it("shows loading state during request", async () => {
      mockRequestElicitation.mockReturnValue({
        unwrap: () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(MOCK_ELICITATION_ACCEPT), 1000),
          ),
      });

      mockUseRequestMcpElicitationMutation.mockReturnValue([
        mockRequestElicitation,
        { isLoading: true, error: null },
      ]);

      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      // Enter message
      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your name");

      // Button should show loading state
      const sendButton = screen.getByRole("button", { name: /sending/i });
      expect(sendButton).toBeDisabled();
    });

    it("shows error when request fails", async () => {
      mockRequestElicitation.mockReturnValue({
        unwrap: () => Promise.reject(new Error("Request failed")),
      });

      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      // Enter message and send
      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your name");

      const sendButton = screen.getByRole("button", { name: /send/i });
      await userEvent.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText(/failed/i)).toBeInTheDocument();
      });
    });
  });

  describe("validation", () => {
    it("disables send button when message is empty", () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      const sendButton = screen.getByRole("button", { name: /send/i });
      expect(sendButton).toBeDisabled();
    });

    it("enables send button when message is provided", async () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your name");

      const sendButton = screen.getByRole("button", { name: /send/i });
      expect(sendButton).toBeEnabled();
    });

    it("disables send button when schema is invalid JSON", async () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Enter your name");

      const schemaInput = screen.getByLabelText(/schema/i);
      // Use fireEvent for invalid JSON with braces
      fireEvent.change(schemaInput, { target: { value: "{ invalid json" } });

      const sendButton = screen.getByRole("button", { name: /send/i });
      expect(sendButton).toBeDisabled();
    });
  });

  describe("dialog actions", () => {
    it("calls onClose when cancel button clicked", async () => {
      renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await userEvent.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("resets form when dialog is reopened", async () => {
      const { rerender } = renderWithProvider(
        <ElicitationDialog open={true} onClose={mockOnClose} />,
      );

      // Enter message
      const messageInput = screen.getByLabelText(/message/i);
      await userEvent.type(messageInput, "Test message");

      expect(messageInput).toHaveValue("Test message");

      // Close and reopen
      rerender(
        <Provider store={createTestStore()}>
          <ElicitationDialog open={false} onClose={mockOnClose} />
        </Provider>,
      );

      rerender(
        <Provider store={createTestStore()}>
          <ElicitationDialog open={true} onClose={mockOnClose} />
        </Provider>,
      );

      // Form should be reset
      const newMessageInput = screen.getByLabelText(/message/i);
      expect(newMessageInput).toHaveValue("");
    });
  });
});
