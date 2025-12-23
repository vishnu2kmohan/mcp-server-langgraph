/**
 * ClarificationDialog Component Tests
 *
 * TDD tests for the agent clarification request dialog.
 *
 * Features:
 * - Display clarification question
 * - Text input for free-form responses
 * - Choice selection for multiple options
 * - Confirmation (yes/no) dialogs
 * - Loading states
 * - Keyboard accessibility
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  ClarificationDialog,
  type ClarificationDialogProps,
  type AgentClarificationRequest,
} from "./ClarificationDialog";

// =============================================================================
// Test Data
// =============================================================================

const mockTextClarificationRequest: AgentClarificationRequest = {
  request_id: "clar-001",
  session_id: "session-001",
  task_id: "task-001",
  agent_name: "Research Assistant",
  clarification_type: "text",
  question: "Which date range should I use for the analysis?",
  options: [],
  placeholder: "Enter date range (e.g., 2024-01-01 to 2024-12-31)",
  required: true,
  context: {
    data_source: "sales_data",
  },
  requested_at: "2024-01-15T10:36:00Z",
};

const mockChoiceClarificationRequest: AgentClarificationRequest = {
  request_id: "clar-002",
  session_id: "session-001",
  task_id: "task-002",
  agent_name: "Data Analyst",
  clarification_type: "choice",
  question: "Which analysis approach should I use?",
  options: [
    {
      id: "fast",
      label: "Fast Analysis",
      description: "~30 seconds, 85% accuracy",
      is_recommended: false,
    },
    {
      id: "thorough",
      label: "Thorough Analysis",
      description: "~5 minutes, 98% accuracy",
      is_recommended: true,
    },
  ],
  placeholder: null,
  required: true,
  context: {},
  requested_at: "2024-01-15T10:36:00Z",
};

const mockConfirmationRequest: AgentClarificationRequest = {
  request_id: "clar-003",
  session_id: "session-001",
  task_id: "task-003",
  agent_name: "File Manager",
  clarification_type: "confirmation",
  question: "This will delete 150 records. Are you sure you want to proceed?",
  options: [],
  placeholder: null,
  required: true,
  context: {
    record_count: 150,
    operation: "delete",
  },
  requested_at: "2024-01-15T10:36:00Z",
};

const defaultTextProps: ClarificationDialogProps = {
  request: mockTextClarificationRequest,
  isOpen: true,
  onClose: vi.fn(),
  onRespond: vi.fn(),
  currentUser: "user@example.com",
};

const defaultChoiceProps: ClarificationDialogProps = {
  request: mockChoiceClarificationRequest,
  isOpen: true,
  onClose: vi.fn(),
  onRespond: vi.fn(),
  currentUser: "user@example.com",
};

const defaultConfirmationProps: ClarificationDialogProps = {
  request: mockConfirmationRequest,
  isOpen: true,
  onClose: vi.fn(),
  onRespond: vi.fn(),
  currentUser: "user@example.com",
};

// =============================================================================
// Tests
// =============================================================================

describe("ClarificationDialog", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render when isOpen is true", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(<ClarificationDialog {...defaultTextProps} isOpen={false} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render dialog title", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(screen.getByText(/agent needs your input/i)).toBeInTheDocument();
    });

    it("should render close button", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(screen.getByTestId("close-dialog")).toBeInTheDocument();
    });

    it("should call onClose when close button clicked", () => {
      const onClose = vi.fn();
      render(<ClarificationDialog {...defaultTextProps} onClose={onClose} />);

      fireEvent.click(screen.getByTestId("close-dialog"));

      expect(onClose).toHaveBeenCalled();
    });

    it("should display agent name", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(screen.getByText(/Research Assistant/)).toBeInTheDocument();
    });

    it("should display the question", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(
        screen.getByText("Which date range should I use for the analysis?"),
      ).toBeInTheDocument();
    });
  });

  describe("Text Input Type", () => {
    it("should render textarea for text type", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(screen.getByTestId("text-input")).toBeInTheDocument();
    });

    it("should show placeholder text", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(
        screen.getByPlaceholderText(
          "Enter date range (e.g., 2024-01-01 to 2024-12-31)",
        ),
      ).toBeInTheDocument();
    });

    it("should call onRespond with text value when submitted", async () => {
      const onRespond = vi.fn();
      const user = userEvent.setup();
      render(
        <ClarificationDialog {...defaultTextProps} onRespond={onRespond} />,
      );

      await user.type(
        screen.getByTestId("text-input"),
        "2024-01-01 to 2024-06-30",
      );
      await user.click(screen.getByTestId("submit-button"));

      await waitFor(() => {
        expect(onRespond).toHaveBeenCalledWith({
          request_id: "clar-001",
          value: "2024-01-01 to 2024-06-30",
          responded_by: "user@example.com",
        });
      });
    });

    it("should disable submit button when input is empty for required field", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(screen.getByTestId("submit-button")).toBeDisabled();
    });

    it("should enable submit button when input has value", async () => {
      const user = userEvent.setup();
      render(<ClarificationDialog {...defaultTextProps} />);

      await user.type(screen.getByTestId("text-input"), "some value");

      expect(screen.getByTestId("submit-button")).toBeEnabled();
    });
  });

  describe("Choice Type", () => {
    it("should render options for choice type", () => {
      render(<ClarificationDialog {...defaultChoiceProps} />);

      expect(screen.getByText("Fast Analysis")).toBeInTheDocument();
      expect(screen.getByText("Thorough Analysis")).toBeInTheDocument();
    });

    it("should display option descriptions", () => {
      render(<ClarificationDialog {...defaultChoiceProps} />);

      expect(screen.getByText("~30 seconds, 85% accuracy")).toBeInTheDocument();
      expect(screen.getByText("~5 minutes, 98% accuracy")).toBeInTheDocument();
    });

    it("should mark recommended option", () => {
      render(<ClarificationDialog {...defaultChoiceProps} />);

      expect(screen.getByText("Recommended")).toBeInTheDocument();
    });

    it("should call onRespond with selected option when submitted", async () => {
      const onRespond = vi.fn();
      const user = userEvent.setup();
      render(
        <ClarificationDialog {...defaultChoiceProps} onRespond={onRespond} />,
      );

      await user.click(screen.getByTestId("option-fast"));
      await user.click(screen.getByTestId("submit-button"));

      await waitFor(() => {
        expect(onRespond).toHaveBeenCalledWith({
          request_id: "clar-002",
          selected_option_id: "fast",
          responded_by: "user@example.com",
        });
      });
    });

    it("should disable submit button when no option selected", () => {
      render(<ClarificationDialog {...defaultChoiceProps} />);

      expect(screen.getByTestId("submit-button")).toBeDisabled();
    });

    it("should enable submit button when option is selected", async () => {
      const user = userEvent.setup();
      render(<ClarificationDialog {...defaultChoiceProps} />);

      await user.click(screen.getByTestId("option-thorough"));

      expect(screen.getByTestId("submit-button")).toBeEnabled();
    });
  });

  describe("Confirmation Type", () => {
    it("should render yes/no buttons for confirmation type", () => {
      render(<ClarificationDialog {...defaultConfirmationProps} />);

      expect(screen.getByTestId("confirm-yes")).toBeInTheDocument();
      expect(screen.getByTestId("confirm-no")).toBeInTheDocument();
    });

    it("should not render submit button for confirmation type", () => {
      render(<ClarificationDialog {...defaultConfirmationProps} />);

      expect(screen.queryByTestId("submit-button")).not.toBeInTheDocument();
    });

    it("should call onRespond with confirmed=true when Yes clicked", async () => {
      const onRespond = vi.fn();
      const user = userEvent.setup();
      render(
        <ClarificationDialog
          {...defaultConfirmationProps}
          onRespond={onRespond}
        />,
      );

      await user.click(screen.getByTestId("confirm-yes"));

      await waitFor(() => {
        expect(onRespond).toHaveBeenCalledWith({
          request_id: "clar-003",
          confirmed: true,
          responded_by: "user@example.com",
        });
      });
    });

    it("should call onRespond with confirmed=false when No clicked", async () => {
      const onRespond = vi.fn();
      const user = userEvent.setup();
      render(
        <ClarificationDialog
          {...defaultConfirmationProps}
          onRespond={onRespond}
        />,
      );

      await user.click(screen.getByTestId("confirm-no"));

      await waitFor(() => {
        expect(onRespond).toHaveBeenCalledWith({
          request_id: "clar-003",
          confirmed: false,
          responded_by: "user@example.com",
        });
      });
    });

    it("should display warning styling for destructive confirmations", () => {
      render(<ClarificationDialog {...defaultConfirmationProps} />);

      expect(screen.getByTestId("confirmation-warning")).toBeInTheDocument();
    });
  });

  describe("Loading States", () => {
    it("should disable all inputs when submitting", () => {
      render(<ClarificationDialog {...defaultTextProps} isSubmitting />);

      expect(screen.getByTestId("text-input")).toBeDisabled();
    });

    it("should show loading spinner when submitting", () => {
      render(<ClarificationDialog {...defaultTextProps} isSubmitting />);

      expect(screen.getByTestId("submit-loading")).toBeInTheDocument();
    });

    it("should disable yes/no buttons when submitting confirmation", () => {
      render(
        <ClarificationDialog {...defaultConfirmationProps} isSubmitting />,
      );

      expect(screen.getByTestId("confirm-yes")).toBeDisabled();
      expect(screen.getByTestId("confirm-no")).toBeDisabled();
    });
  });

  describe("Keyboard Accessibility", () => {
    it("should close on Escape key", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(<ClarificationDialog {...defaultTextProps} onClose={onClose} />);

      await user.keyboard("{Escape}");

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should display error message when provided", () => {
      render(
        <ClarificationDialog
          {...defaultTextProps}
          error="Failed to submit response"
        />,
      );

      expect(screen.getByText(/failed to submit/i)).toBeInTheDocument();
    });
  });

  describe("Context Display", () => {
    it("should display context information when available", () => {
      render(<ClarificationDialog {...defaultTextProps} />);

      expect(screen.getByText(/sales_data/)).toBeInTheDocument();
    });

    it("should display destructive operation warning", () => {
      render(<ClarificationDialog {...defaultConfirmationProps} />);

      // Context shows record_count and operation
      expect(screen.getByText(/record_count/)).toBeInTheDocument();
      // 150 appears in both question and context
      expect(screen.getAllByText(/150/).length).toBeGreaterThan(0);
    });
  });
});
