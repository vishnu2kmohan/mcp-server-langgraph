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
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  ClarificationDialog,
  type ClarificationDialogProps,
  type AgentClarificationRequestCamelCase,
} from "./ClarificationDialog";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Data
// =============================================================================

// Mock data uses camelCase per ADR-0091 Phase 10
const mockTextClarificationRequest: AgentClarificationRequestCamelCase = {
  requestId: "clar-001",
  sessionId: "session-001",
  taskId: "task-001",
  agentName: "Research Assistant",
  clarificationType: "text",
  question: "Which date range should I use for the analysis?",
  options: [],
  placeholder: "Enter date range (e.g., 2024-01-01 to 2024-12-31)",
  required: true,
  context: {
    dataSource: "sales_data",
  },
  requestedAt: "2024-01-15T10:36:00Z",
};

const mockChoiceClarificationRequest: AgentClarificationRequestCamelCase = {
  requestId: "clar-002",
  sessionId: "session-001",
  taskId: "task-002",
  agentName: "Data Analyst",
  clarificationType: "choice",
  question: "Which analysis approach should I use?",
  options: [
    {
      id: "fast",
      label: "Fast Analysis",
      description: "~30 seconds, 85% accuracy",
      isRecommended: false,
    },
    {
      id: "thorough",
      label: "Thorough Analysis",
      description: "~5 minutes, 98% accuracy",
      isRecommended: true,
    },
  ],
  placeholder: null,
  required: true,
  context: {},
  requestedAt: "2024-01-15T10:36:00Z",
};

const mockConfirmationRequest: AgentClarificationRequestCamelCase = {
  requestId: "clar-003",
  sessionId: "session-001",
  taskId: "task-003",
  agentName: "File Manager",
  clarificationType: "confirmation",
  question: "This will delete 150 records. Are you sure you want to proceed?",
  options: [],
  placeholder: null,
  required: true,
  context: {
    recordCount: 150,
    operation: "delete",
  },
  requestedAt: "2024-01-15T10:36:00Z",
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
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} isOpen={false} />
        </TestProvider>,
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render dialog title", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/agent needs your input/i)).toBeInTheDocument();
    });

    it("should render close button", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("close-dialog")).toBeInTheDocument();
    });

    it("should call onClose when close button clicked", () => {
      const onClose = vi.fn();
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} onClose={onClose} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("close-dialog"));

      expect(onClose).toHaveBeenCalled();
    });

    it("should display agent name", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/Research Assistant/)).toBeInTheDocument();
    });

    it("should display the question", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      expect(
        screen.getByText("Which date range should I use for the analysis?"),
      ).toBeInTheDocument();
    });
  });

  describe("Text Input Type", () => {
    it("should render textarea for text type", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("text-input")).toBeInTheDocument();
    });

    it("should show placeholder text", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

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
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} onRespond={onRespond} />
        </TestProvider>,
      );

      await user.type(
        screen.getByTestId("text-input"),
        "2024-01-01 to 2024-06-30",
      );
      await user.click(screen.getByTestId("submit-button"));

      await waitFor(() => {
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onRespond).toHaveBeenCalledWith({
          requestId: "clar-001",
          value: "2024-01-01 to 2024-06-30",
          respondedBy: "user@example.com",
        });
      });
    });

    it("should disable submit button when input is empty for required field", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("submit-button")).toBeDisabled();
    });

    it("should enable submit button when input has value", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      await user.type(screen.getByTestId("text-input"), "some value");

      expect(screen.getByTestId("submit-button")).toBeEnabled();
    });
  });

  describe("Choice Type", () => {
    it("should render options for choice type", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultChoiceProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Fast Analysis")).toBeInTheDocument();
      expect(screen.getByText("Thorough Analysis")).toBeInTheDocument();
    });

    it("should display option descriptions", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultChoiceProps} />
        </TestProvider>,
      );

      expect(screen.getByText("~30 seconds, 85% accuracy")).toBeInTheDocument();
      expect(screen.getByText("~5 minutes, 98% accuracy")).toBeInTheDocument();
    });

    it("should mark recommended option", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultChoiceProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Recommended")).toBeInTheDocument();
    });

    it("should call onRespond with selected option when submitted", async () => {
      const onRespond = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ClarificationDialog {...defaultChoiceProps} onRespond={onRespond} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("option-fast"));
      await user.click(screen.getByTestId("submit-button"));

      await waitFor(() => {
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onRespond).toHaveBeenCalledWith({
          requestId: "clar-002",
          selectedOptionId: "fast",
          respondedBy: "user@example.com",
        });
      });
    });

    it("should disable submit button when no option selected", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultChoiceProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("submit-button")).toBeDisabled();
    });

    it("should enable submit button when option is selected", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ClarificationDialog {...defaultChoiceProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("option-thorough"));

      expect(screen.getByTestId("submit-button")).toBeEnabled();
    });
  });

  describe("Confirmation Type", () => {
    it("should render yes/no buttons for confirmation type", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultConfirmationProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("confirm-yes")).toBeInTheDocument();
      expect(screen.getByTestId("confirm-no")).toBeInTheDocument();
    });

    it("should not render submit button for confirmation type", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultConfirmationProps} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("submit-button")).not.toBeInTheDocument();
    });

    it("should call onRespond with confirmed=true when Yes clicked", async () => {
      const onRespond = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ClarificationDialog
            {...defaultConfirmationProps}
            onRespond={onRespond}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("confirm-yes"));

      await waitFor(() => {
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onRespond).toHaveBeenCalledWith({
          requestId: "clar-003",
          confirmed: true,
          respondedBy: "user@example.com",
        });
      });
    });

    it("should call onRespond with confirmed=false when No clicked", async () => {
      const onRespond = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ClarificationDialog
            {...defaultConfirmationProps}
            onRespond={onRespond}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("confirm-no"));

      await waitFor(() => {
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onRespond).toHaveBeenCalledWith({
          requestId: "clar-003",
          confirmed: false,
          respondedBy: "user@example.com",
        });
      });
    });

    it("should display warning styling for destructive confirmations", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultConfirmationProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("confirmation-warning")).toBeInTheDocument();
    });
  });

  describe("Loading States", () => {
    it("should disable all inputs when submitting", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} isSubmitting />
        </TestProvider>,
      );

      expect(screen.getByTestId("text-input")).toBeDisabled();
    });

    it("should show loading spinner when submitting", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} isSubmitting />
        </TestProvider>,
      );

      expect(screen.getByTestId("submit-loading")).toBeInTheDocument();
    });

    it("should disable yes/no buttons when submitting confirmation", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultConfirmationProps} isSubmitting />
        </TestProvider>,
      );

      expect(screen.getByTestId("confirm-yes")).toBeDisabled();
      expect(screen.getByTestId("confirm-no")).toBeDisabled();
    });
  });

  describe("Keyboard Accessibility", () => {
    it("should close on Escape key", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} onClose={onClose} />
        </TestProvider>,
      );

      await user.keyboard("{Escape}");

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should display error message when provided", () => {
      render(
        <TestProvider>
          <ClarificationDialog
            {...defaultTextProps}
            error="Failed to submit response"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/failed to submit/i)).toBeInTheDocument();
    });
  });

  describe("Context Display", () => {
    it("should display context information when available", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultTextProps} />
        </TestProvider>,
      );

      // Context uses camelCase keys per ADR-0091 Phase 10
      expect(screen.getByText(/dataSource/)).toBeInTheDocument();
    });

    it("should display destructive operation warning", () => {
      render(
        <TestProvider>
          <ClarificationDialog {...defaultConfirmationProps} />
        </TestProvider>,
      );

      // Context shows recordCount and operation (camelCase per ADR-0091 Phase 10)
      expect(screen.getByText(/recordCount/)).toBeInTheDocument();
      // 150 appears in both question and context
      expect(screen.getAllByText(/150/).length).toBeGreaterThan(0);
    });
  });
});
