/**
 * PromptTester Component Tests (TDD)
 *
 * Tests for the prompt tester that allows users to:
 * - View available MCP prompts
 * - Fill in prompt arguments
 * - Execute prompts and see generated messages
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../../api";

// Mock the RTK Query hooks
const mockUseListMcpPromptsQuery = vi.fn();
const mockUseGetMcpPromptMutation = vi.fn();

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useListMcpPromptsQuery: () => mockUseListMcpPromptsQuery(),
    useGetMcpPromptMutation: () => mockUseGetMcpPromptMutation(),
  };
});

// Import after mocking
import { PromptTester } from "./PromptTester";

// =============================================================================
// Mock Data
// =============================================================================

const MOCK_PROMPTS = {
  prompts: [
    {
      name: "summarize",
      description: "Summarize the given text",
      arguments: [
        { name: "text", description: "Text to summarize", required: true },
        { name: "length", description: "Summary length", required: false },
      ],
    },
    {
      name: "translate",
      description: "Translate text to another language",
      arguments: [
        { name: "text", description: "Text to translate", required: true },
        { name: "language", description: "Target language", required: true },
      ],
    },
    {
      name: "greet",
      description: "Generate a greeting",
      arguments: [
        { name: "name", description: "Name to greet", required: true },
      ],
    },
  ],
};

const MOCK_PROMPT_RESULT = {
  messages: [
    {
      role: "user",
      content: {
        type: "text",
        text: "Please summarize the following:\n\nHello world, this is a test.",
      },
    },
  ],
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

describe("PromptTester", () => {
  const mockOnClose = vi.fn();
  const mockGetPrompt = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockUseListMcpPromptsQuery.mockReturnValue({
      data: MOCK_PROMPTS,
      isLoading: false,
      error: null,
    });

    mockUseGetMcpPromptMutation.mockReturnValue([
      mockGetPrompt,
      { isLoading: false, error: null },
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders dialog when open", () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Prompt Tester")).toBeInTheDocument();
    });

    it("does not render when closed", () => {
      renderWithProvider(<PromptTester open={false} onClose={mockOnClose} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("shows loading state when fetching prompts", () => {
      mockUseListMcpPromptsQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it("shows error state when prompts fetch fails", () => {
      mockUseListMcpPromptsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { message: "Failed to fetch prompts" },
      });

      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  describe("prompt selection", () => {
    it("displays list of available prompts", () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      expect(screen.getByText("summarize")).toBeInTheDocument();
      expect(screen.getByText("translate")).toBeInTheDocument();
      expect(screen.getByText("greet")).toBeInTheDocument();
    });

    it("shows prompt description on selection", async () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      expect(screen.getByText("Summarize the given text")).toBeInTheDocument();
    });

    it("generates argument fields from prompt arguments", async () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      // Check for required argument
      expect(screen.getByLabelText(/text/i)).toBeInTheDocument();
      // Check for optional argument
      expect(screen.getByLabelText(/length/i)).toBeInTheDocument();
    });

    it("marks required arguments", async () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      // Required argument should have asterisk in its label
      const textInput = screen.getByLabelText(/^text\*/i);
      expect(textInput).toBeInTheDocument();
    });
  });

  describe("prompt execution", () => {
    it("executes prompt with correct arguments", async () => {
      mockGetPrompt.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_PROMPT_RESULT),
      });

      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      // Select prompt
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      // Fill in arguments
      const textInput = screen.getByLabelText(/text/i);
      await userEvent.type(textInput, "Hello world, this is a test.");

      // Execute prompt
      const executeButton = screen.getByRole("button", { name: /execute/i });
      await userEvent.click(executeButton);

      expect(mockGetPrompt).toHaveBeenCalledWith({
        name: "summarize",
        arguments: { text: "Hello world, this is a test." },
      });
    });

    it("displays generated messages", async () => {
      mockGetPrompt.mockReturnValue({
        unwrap: () => Promise.resolve(MOCK_PROMPT_RESULT),
      });

      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      // Select prompt and fill in arguments
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      const textInput = screen.getByLabelText(/text/i);
      await userEvent.type(textInput, "Hello world");

      // Execute prompt
      const executeButton = screen.getByRole("button", { name: /execute/i });
      await userEvent.click(executeButton);

      await waitFor(() => {
        expect(screen.getByText(/Please summarize/)).toBeInTheDocument();
      });
    });

    it("shows loading state during execution", async () => {
      mockGetPrompt.mockReturnValue({
        unwrap: () =>
          new Promise((resolve) =>
            setTimeout(() => resolve(MOCK_PROMPT_RESULT), 1000),
          ),
      });

      mockUseGetMcpPromptMutation.mockReturnValue([
        mockGetPrompt,
        { isLoading: true, error: null },
      ]);

      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      // Select prompt and fill required field
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      const textInput = screen.getByLabelText(/text/i);
      await userEvent.type(textInput, "Hello world");

      // Button should show loading state
      const executeButton = screen.getByRole("button", { name: /executing/i });
      expect(executeButton).toBeDisabled();
    });

    it("shows error when execution fails", async () => {
      mockGetPrompt.mockReturnValue({
        unwrap: () => Promise.reject(new Error("Failed to execute prompt")),
      });

      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      // Select prompt and fill in arguments
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      const textInput = screen.getByLabelText(/text/i);
      await userEvent.type(textInput, "Hello world");

      // Execute prompt
      const executeButton = screen.getByRole("button", { name: /execute/i });
      await userEvent.click(executeButton);

      await waitFor(() => {
        expect(screen.getByText(/failed/i)).toBeInTheDocument();
      });
    });
  });

  describe("validation", () => {
    it("disables execute button when required fields are empty", async () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      // Select prompt but don't fill in arguments
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      const executeButton = screen.getByRole("button", { name: /execute/i });
      expect(executeButton).toBeDisabled();
    });

    it("enables execute button when required fields are filled", async () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      // Select prompt and fill in required field
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      const textInput = screen.getByLabelText(/text/i);
      await userEvent.type(textInput, "Hello world");

      const executeButton = screen.getByRole("button", { name: /execute/i });
      expect(executeButton).toBeEnabled();
    });

    it("validates all required fields for multi-argument prompts", async () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      // Select translate prompt (2 required fields)
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "translate");

      // Fill only one field
      const textInput = screen.getByLabelText(/text/i);
      await userEvent.type(textInput, "Hello");

      // Button should still be disabled
      const executeButton = screen.getByRole("button", { name: /execute/i });
      expect(executeButton).toBeDisabled();

      // Fill the second required field
      const languageInput = screen.getByLabelText(/language/i);
      await userEvent.type(languageInput, "Spanish");

      // Now button should be enabled
      expect(executeButton).toBeEnabled();
    });
  });

  describe("dialog actions", () => {
    it("calls onClose when close button clicked", async () => {
      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      const closeButton = screen.getByRole("button", { name: /close/i });
      await userEvent.click(closeButton);

      expect(mockOnClose).toHaveBeenCalled();
    });

    it("resets form when dialog is reopened", async () => {
      const { rerender } = renderWithProvider(
        <PromptTester open={true} onClose={mockOnClose} />,
      );

      // Select prompt
      const promptSelect = screen.getByLabelText(/select prompt/i);
      await userEvent.selectOptions(promptSelect, "summarize");

      // Verify prompt is selected
      expect(screen.getByText("Summarize the given text")).toBeInTheDocument();

      // Close and reopen
      rerender(
        <Provider store={createTestStore()}>
          <PromptTester open={false} onClose={mockOnClose} />
        </Provider>,
      );

      rerender(
        <Provider store={createTestStore()}>
          <PromptTester open={true} onClose={mockOnClose} />
        </Provider>,
      );

      // Form should be reset
      expect(
        screen.queryByText("Summarize the given text"),
      ).not.toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("shows empty state when no prompts available", () => {
      mockUseListMcpPromptsQuery.mockReturnValue({
        data: { prompts: [] },
        isLoading: false,
        error: null,
      });

      renderWithProvider(<PromptTester open={true} onClose={mockOnClose} />);

      expect(screen.getByText(/no prompts/i)).toBeInTheDocument();
    });
  });
});
