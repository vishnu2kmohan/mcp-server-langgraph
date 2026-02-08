/**
 * ChatInputForm Model Selection Integration Tests
 *
 * Tests for model selector functionality including:
 * - Loading state display
 * - Model selection dropdown
 * - Model change callbacks
 * - Thinking model support
 *
 * Sprint 1 - Chat Input Gap Fix
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ChatInputForm, type ModelOption } from "./ChatInputForm";

import { TestProvider } from "@/test-utils";

// Mock drag handlers for file upload
const mockDragHandlers = {
  onDragEnter: vi.fn(),
  onDragLeave: vi.fn(),
  onDragOver: vi.fn(),
  onDrop: vi.fn(),
};

const defaultProps = {
  input: "",
  onInputChange: vi.fn(),
  onSubmit: vi.fn(),
  isProcessing: false,
  isListening: false,
  isVoiceSupported: true,
  voiceError: null,
  onStartListening: vi.fn(),
  onStopListening: vi.fn(),
  uploadFiles: [],
  isUploading: false,
  isDragging: false,
  fileError: null,
  onSelectFiles: vi.fn(),
  onRemoveFile: vi.fn(),
  dragHandlers: mockDragHandlers,
};

const mockModels: ModelOption[] = [
  { id: "claude-3-5-sonnet", name: "Claude 3.5 Sonnet", provider: "anthropic" },
  { id: "gpt-4o", name: "GPT-4o", provider: "openai" },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "google" },
];

describe("ChatInputForm Model Selection Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Model Selector Visibility", () => {
    it("should not show model selector when showModelSelector is false", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} showModelSelector={false} />
        </TestProvider>,
      );
      expect(screen.queryByTestId("model-selector")).not.toBeInTheDocument();
    });

    it("should show model selector when showModelSelector is true", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("model-selector")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when isModelsLoading is true", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            isModelsLoading={true}
            availableModels={[]}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("model-selector-loading")).toBeInTheDocument();
      expect(screen.getByText("Loading models...")).toBeInTheDocument();
    });

    it("should disable model selector button when loading", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            isModelsLoading={true}
            availableModels={[]}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      expect(button).toBeDisabled();
    });

    it("should show aria-busy when loading", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            isModelsLoading={true}
            availableModels={[]}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      expect(button).toHaveAttribute("aria-busy", "true");
    });

    it("should show models when not loading", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            isModelsLoading={false}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("model-selector-loading"),
      ).not.toBeInTheDocument();
      expect(screen.getByText("claude-3-5-sonnet")).toBeInTheDocument();
    });
  });

  describe("Model Selection Dropdown", () => {
    it("should display the selected model name", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="gpt-4o"
          />
        </TestProvider>,
      );

      expect(screen.getByText("gpt-4o")).toBeInTheDocument();
    });

    it("should display provider badge for selected model", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      expect(screen.getByText("anthropic")).toBeInTheDocument();
    });

    it("should open dropdown when button is clicked", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      expect(
        screen.getByTestId("model-option-claude-3-5-sonnet"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("model-option-gpt-4o")).toBeInTheDocument();
      expect(
        screen.getByTestId("model-option-gemini-2.5-flash"),
      ).toBeInTheDocument();
    });

    it("should show all available models in dropdown", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Each model should be listed
      expect(screen.getByText("Claude 3.5 Sonnet")).toBeInTheDocument();
      expect(screen.getByText("GPT-4o")).toBeInTheDocument();
      expect(screen.getByText("Gemini 2.5 Flash")).toBeInTheDocument();
    });

    it("should show checkmark next to selected model", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      const selectedOption = screen.getByTestId(
        "model-option-claude-3-5-sonnet",
      );
      expect(selectedOption).toHaveAttribute("aria-selected", "true");
    });
  });

  describe("Model Change Callback", () => {
    it("should call onModelChange when a different model is selected", () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Select a different model
      const gptOption = screen.getByTestId("model-option-gpt-4o");
      fireEvent.click(gptOption);

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });

    it("should close dropdown after selection", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
            onModelChange={vi.fn()}
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Dropdown should be open
      expect(screen.getByTestId("model-option-gpt-4o")).toBeInTheDocument();

      // Select a model
      fireEvent.click(screen.getByTestId("model-option-gpt-4o"));

      // Dropdown should be closed
      expect(
        screen.queryByTestId("model-option-gpt-4o"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Processing State", () => {
    it("should disable model selector when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
            isProcessing={true}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      expect(button).toBeDisabled();
    });

    it("should not open dropdown when disabled", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
            isProcessing={true}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      expect(
        screen.queryByTestId("model-option-gpt-4o"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA attributes on model selector", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      expect(button).toHaveAttribute("aria-label", "Select AI model");
      expect(button).toHaveAttribute("aria-haspopup", "listbox");
    });

    it("should have aria-expanded when dropdown is open", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");

      // Initially closed
      expect(button).toHaveAttribute("aria-expanded", "false");

      // Open dropdown
      fireEvent.click(button);
      expect(button).toHaveAttribute("aria-expanded", "true");
    });

    it("should have role=listbox on dropdown menu", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      const listbox = screen.getByRole("listbox");
      expect(listbox).toBeInTheDocument();
    });

    it("should have role=option on each model option", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      const options = screen.getAllByRole("option");
      expect(options).toHaveLength(3);
    });
  });

  describe("No Models Available", () => {
    it("should show Select model placeholder when no model is selected", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel={undefined}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Select model")).toBeInTheDocument();
    });

    it("should handle empty available models gracefully", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={[]}
            selectedModel={undefined}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Should show empty dropdown (no options)
      expect(
        screen.queryByTestId("model-option-claude-3-5-sonnet"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Thinking Model Support", () => {
    it("should show reasoning effort selector when model supports thinking", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
            modelSupportsThinking={true}
            enableThinking={true}
            onReasoningEffortChange={vi.fn()}
          />
        </TestProvider>,
      );

      // The reasoning effort selector should be visible
      // (in rich text mode, it's in the controls row)
      expect(
        screen.queryByTestId("enable-thinking-toggle") ||
          screen.queryByLabelText(/reasoning effort/i),
      ).toBeTruthy();
    });

    it("should not show thinking toggle when model does not support thinking", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="gpt-4o"
            modelSupportsThinking={false}
            enableThinking={false}
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("enable-thinking-toggle"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("should close dropdown on Escape key", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);
      expect(screen.getByTestId("model-option-gpt-4o")).toBeInTheDocument();

      // Press Escape
      fireEvent.keyDown(button, { key: "Escape" });
      expect(
        screen.queryByTestId("model-option-gpt-4o"),
      ).not.toBeInTheDocument();
    });

    it("should navigate down with ArrowDown key", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Press ArrowDown to move focus
      fireEvent.keyDown(button, { key: "ArrowDown" });

      // First option should be focused (claude-3-5-sonnet)
      const firstOption = screen.getByTestId("model-option-claude-3-5-sonnet");
      expect(firstOption).toHaveClass("ring-2");
    });

    it("should navigate up with ArrowUp key", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="gemini-2.5-flash"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Press ArrowUp to navigate to last option
      fireEvent.keyDown(button, { key: "ArrowUp" });

      // Models are sorted alphabetically: Claude, Gemini, GPT-4o
      // So GPT-4o is the last option after sorting
      const lastOption = screen.getByTestId("model-option-gpt-4o");
      expect(lastOption).toHaveClass("ring-2");
    });

    it("should select focused option with Enter key", () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Models are sorted alphabetically: Claude, Gemini, GPT-4o
      // Initial focus is -1
      // ArrowDown -> 0 (claude-3-5-sonnet)
      // ArrowDown -> 1 (gemini-2.5-flash)
      fireEvent.keyDown(button, { key: "ArrowDown" }); // -1 -> 0
      fireEvent.keyDown(button, { key: "ArrowDown" }); // 0 -> 1

      // Press Enter to select gemini-2.5-flash
      fireEvent.keyDown(button, { key: "Enter" });

      expect(onModelChange).toHaveBeenCalledWith("gemini-2.5-flash");
    });

    it("should open dropdown with Enter key when closed", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");

      // Dropdown should be closed initially
      expect(
        screen.queryByTestId("model-option-gpt-4o"),
      ).not.toBeInTheDocument();

      // Press Enter to open
      fireEvent.keyDown(button, { key: "Enter" });
      expect(screen.getByTestId("model-option-gpt-4o")).toBeInTheDocument();
    });

    it("should jump to first option with Home key", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="gemini-2.5-flash"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Press Home to jump to first
      fireEvent.keyDown(button, { key: "Home" });

      const firstOption = screen.getByTestId("model-option-claude-3-5-sonnet");
      expect(firstOption).toHaveClass("ring-2");
    });

    it("should jump to last option with End key", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Press End to jump to last
      fireEvent.keyDown(button, { key: "End" });

      // Models are sorted alphabetically: Claude, Gemini, GPT-4o
      // So GPT-4o is the last option after sorting
      const lastOption = screen.getByTestId("model-option-gpt-4o");
      expect(lastOption).toHaveClass("ring-2");
    });

    it("should wrap around when navigating past last option", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Initial focus is -1 (none)
      // Navigate to wrap around:
      // ArrowDown -> 0, ArrowDown -> 1, ArrowDown -> 2, ArrowDown -> 0 (wrap)
      fireEvent.keyDown(button, { key: "ArrowDown" }); // -1 -> 0
      fireEvent.keyDown(button, { key: "ArrowDown" }); // 0 -> 1
      fireEvent.keyDown(button, { key: "ArrowDown" }); // 1 -> 2
      fireEvent.keyDown(button, { key: "ArrowDown" }); // 2 -> 0 (wrap)

      const firstOption = screen.getByTestId("model-option-claude-3-5-sonnet");
      expect(firstOption).toHaveClass("ring-2");
    });

    it("should navigate filtered models with keyboard when search is enabled", () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            enableModelSearch={true}
            availableModels={mockModels}
            selectedModel="claude-3-5-sonnet"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Filter to "gpt" - should narrow list to GPT-4o only
      const search = screen.getByTestId("model-search-input");
      fireEvent.change(search, { target: { value: "gpt" } });

      // Navigate down to first (and only) filtered result
      fireEvent.keyDown(button, { key: "ArrowDown" });

      // Select with Enter
      fireEvent.keyDown(button, { key: "Enter" });

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });
  });
}); // Close main describe block
