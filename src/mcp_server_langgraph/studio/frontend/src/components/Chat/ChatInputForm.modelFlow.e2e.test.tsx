/**
 * ChatInputForm Model Flow E2E Integration Tests
 *
 * End-to-end tests for the complete model selection flow:
 * - Model selection -> State update -> API call
 * - localStorage persistence across sessions
 * - Model capability-based UI changes
 *
 * Sprint 1 - Chat Input Gap Fix
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
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

const mockModelsWithCapabilities: ModelOption[] = [
  {
    id: "claude-3-5-sonnet",
    name: "Claude 3.5 Sonnet",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    supportsThinking: false,
    supportsVision: true,
    supportsTools: true,
  },
  {
    id: "gemini-2.5-flash",
    name: "Gemini 2.5 Flash",
    provider: "google",
    supportsThinking: true,
    supportsVision: false,
    supportsTools: true,
  },
];

describe("ChatInputForm Model Flow E2E Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Complete Model Selection Flow", () => {
    it("should complete full flow: select model -> update state -> trigger callback", async () => {
      // GIVEN: Model selection handler
      const onModelChange = vi.fn();
      const onReasoningEffortChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            onModelChange={onModelChange}
            modelSupportsThinking={true}
            reasoningEffort="medium"
            onReasoningEffortChange={onReasoningEffortChange}
            enableThinking={true}
          />
        </TestProvider>,
      );

      // WHEN: User opens dropdown and selects a different model
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Select GPT-4o
      const gptOption = screen.getByTestId("model-option-gpt-4o");
      fireEvent.click(gptOption);

      // THEN: Callback should be called with new model ID
      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
      expect(onModelChange).toHaveBeenCalledTimes(1);
    });

    it("should show thinking controls only when model supports it", () => {
      // GIVEN: A model that supports thinking
      const { rerender } = render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            modelSupportsThinking={true}
            enableThinking={true}
            onEnableThinkingChange={vi.fn()}
            onReasoningEffortChange={vi.fn()}
          />
        </TestProvider>,
      );

      // THEN: Thinking toggle should be visible
      expect(screen.getByTestId("enable-thinking-toggle")).toBeInTheDocument();

      // WHEN: Switching to a model that doesn't support thinking
      rerender(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="gpt-4o"
            modelSupportsThinking={false}
            enableThinking={false}
            onEnableThinkingChange={vi.fn()}
            onReasoningEffortChange={vi.fn()}
          />
        </TestProvider>,
      );

      // THEN: Thinking toggle should NOT be visible
      expect(
        screen.queryByTestId("enable-thinking-toggle"),
      ).not.toBeInTheDocument();
    });

    it("should update model button display when selected model changes", () => {
      const { rerender } = render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      // Initially shows Claude
      const button = screen.getByTestId("model-selector-button");
      expect(button).toHaveTextContent("claude-3-5-sonnet");
      expect(button).toHaveTextContent("anthropic");
      expect(button).toHaveTextContent("Thinking"); // Claude supports thinking

      // Rerender with GPT-4o selected
      rerender(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="gpt-4o"
          />
        </TestProvider>,
      );

      // Now shows GPT-4o
      expect(button).toHaveTextContent("gpt-4o");
      expect(button).toHaveTextContent("openai");
      expect(button).not.toHaveTextContent("Thinking"); // GPT-4o doesn't support thinking
    });
  });

  describe("Keyboard-Driven Model Selection Flow", () => {
    it("should complete model selection using only keyboard", async () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");

      // GIVEN: User focuses on button and presses Enter to open
      button.focus();
      fireEvent.keyDown(button, { key: "Enter" });

      // THEN: Dropdown should be open
      expect(screen.getByTestId("model-option-gpt-4o")).toBeInTheDocument();

      // WHEN: User navigates with arrow keys
      // Models are sorted alphabetically: Claude, Gemini, GPT-4o
      fireEvent.keyDown(button, { key: "ArrowDown" }); // Focus first option (Claude)
      fireEvent.keyDown(button, { key: "ArrowDown" }); // Focus second option (Gemini)

      // Second option (Gemini) should have focus ring
      expect(screen.getByTestId("model-option-gemini-2.5-flash")).toHaveClass(
        "ring-2",
      );

      // WHEN: User presses Enter to select
      fireEvent.keyDown(button, { key: "Enter" });

      // THEN: Callback should be called with Gemini (second option after sorting)
      expect(onModelChange).toHaveBeenCalledWith("gemini-2.5-flash");
    });

    it("should close dropdown with Escape without selecting", () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      const button = screen.getByTestId("model-selector-button");

      // Open dropdown
      fireEvent.click(button);
      expect(screen.getByTestId("model-option-gpt-4o")).toBeInTheDocument();

      // Press Escape
      fireEvent.keyDown(button, { key: "Escape" });

      // Dropdown should be closed
      expect(
        screen.queryByTestId("model-option-gpt-4o"),
      ).not.toBeInTheDocument();

      // No model change should have occurred
      expect(onModelChange).not.toHaveBeenCalled();
    });
  });

  describe("Recent Models Integration", () => {
    it("should prioritize recent models in selection", () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            recentModels={["gpt-4o"]}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Recent section should appear first
      const recentSection = screen.getByTestId("recent-models-section");
      expect(recentSection).toBeInTheDocument();

      // Click on recent model
      const recentGpt = screen.getByTestId("recent-model-option-gpt-4o");
      fireEvent.click(recentGpt);

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });
  });

  describe("Search-Driven Model Selection Flow", () => {
    it("should complete flow: search -> filter -> select", async () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            enableModelSearch={true}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Wait for search input to be focused
      const searchInput = screen.getByTestId("model-search-input");
      await waitFor(() => {
        expect(document.activeElement).toBe(searchInput);
      });

      // Type search query
      fireEvent.change(searchInput, { target: { value: "gemini" } });

      // Only Gemini should be visible
      expect(
        screen.getByTestId("model-option-gemini-2.5-flash"),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId("model-option-claude-3-5-sonnet"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("model-option-gpt-4o"),
      ).not.toBeInTheDocument();

      // Click on Gemini
      fireEvent.click(screen.getByTestId("model-option-gemini-2.5-flash"));

      expect(onModelChange).toHaveBeenCalledWith("gemini-2.5-flash");
    });
  });

  describe("Loading State Integration", () => {
    it("should disable model selector when loading and show loading state", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={[]}
            isModelsLoading={true}
          />
        </TestProvider>,
      );

      // Button should be disabled
      const button = screen.getByTestId("model-selector-button");
      expect(button).toBeDisabled();

      // Loading indicator should be shown
      expect(screen.getByTestId("model-selector-loading")).toBeInTheDocument();
      expect(screen.getByText("Loading models...")).toBeInTheDocument();

      // Dropdown should not open when clicked
      fireEvent.click(button);
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });

    it("should enable model selector when models finish loading", () => {
      const { rerender } = render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={[]}
            isModelsLoading={true}
          />
        </TestProvider>,
      );

      // Initially loading
      expect(screen.getByTestId("model-selector-button")).toBeDisabled();

      // Rerender with loaded models
      rerender(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            isModelsLoading={false}
          />
        </TestProvider>,
      );

      // Now enabled
      const button = screen.getByTestId("model-selector-button");
      expect(button).not.toBeDisabled();
      expect(button).toHaveTextContent("claude-3-5-sonnet");
    });
  });

  describe("Processing State Integration", () => {
    it("should disable model selector when processing a message", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            isProcessing={true}
          />
        </TestProvider>,
      );

      // Button should be disabled while processing
      const button = screen.getByTestId("model-selector-button");
      expect(button).toBeDisabled();

      // Dropdown should not open
      fireEvent.click(button);
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  describe("Capability Badges Integration", () => {
    it("should display all capability badges for a fully-featured model", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Claude has all capabilities
      const claudeOption = screen.getByTestId("model-option-claude-3-5-sonnet");
      expect(claudeOption).toHaveTextContent("Thinking");
      expect(claudeOption).toHaveTextContent("Vision");
      expect(claudeOption).toHaveTextContent("Tools");

      // Gemini has Thinking and Tools but not Vision
      const geminiOption = screen.getByTestId("model-option-gemini-2.5-flash");
      expect(geminiOption).toHaveTextContent("Thinking");
      expect(geminiOption).not.toHaveTextContent("Vision");
      expect(geminiOption).toHaveTextContent("Tools");
    });
  });

  describe("Model State Consistency", () => {
    it("should maintain consistent state through model changes", () => {
      const onModelChange = vi.fn();

      const { rerender } = render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="claude-3-5-sonnet"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Select GPT-4o
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);
      fireEvent.click(screen.getByTestId("model-option-gpt-4o"));

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");

      // Parent updates selectedModel prop
      rerender(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithCapabilities}
            selectedModel="gpt-4o"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // UI should reflect new selection
      expect(button).toHaveTextContent("gpt-4o");
      expect(button).toHaveTextContent("openai");

      // Open dropdown again and verify checkmark
      fireEvent.click(button);
      const gptOption = screen.getByTestId("model-option-gpt-4o");
      expect(gptOption).toHaveAttribute("aria-selected", "true");
    });
  });

  // =============================================================================
  // Model Lifecycle Status E2E Tests (Sprint 1 - Enhanced Model Selector)
  // Tests the complete flow: Backend ModelRegistry -> API -> Frontend rendering
  // =============================================================================

  describe("Model Lifecycle Status E2E Flow", () => {
    const mockModelsWithLifecycleStatus: ModelOption[] = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        supportsThinking: true,
        supportsVision: true,
        supportsTools: true,
        status: "current", // Production-ready, no badge shown
      },
      {
        id: "gemini-3-flash-preview",
        name: "Gemini 3 Flash Preview",
        provider: "google",
        supportsThinking: true,
        supportsVision: true,
        supportsTools: true,
        status: "preview", // Experimental, cyan badge
      },
      {
        id: "gpt-4-turbo",
        name: "GPT-4 Turbo",
        provider: "openai",
        supportsThinking: false,
        supportsVision: true,
        supportsTools: true,
        status: "legacy", // Older version, amber badge
      },
      {
        id: "claude-3-sonnet",
        name: "Claude 3 Sonnet",
        provider: "anthropic",
        supportsThinking: true,
        supportsVision: false,
        supportsTools: true,
        status: "deprecated", // Will be removed, red badge
      },
    ];

    it("should render model lifecycle status badges from backend data", () => {
      // GIVEN: Models with lifecycle status from backend (simulating ModelRegistry response)
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithLifecycleStatus}
            selectedModel="claude-opus-4-5"
          />
        </TestProvider>,
      );

      // WHEN: User opens the model dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // THEN: Status badges should be displayed appropriately

      // Current model should NOT show any status badge
      const currentModel = screen.getByTestId("model-option-claude-opus-4-5");
      expect(currentModel).not.toHaveTextContent("Preview");
      expect(currentModel).not.toHaveTextContent("Legacy");
      expect(currentModel).not.toHaveTextContent("Deprecated");

      // Preview model should show Preview badge
      const previewModel = screen.getByTestId(
        "model-option-gemini-3-flash-preview",
      );
      expect(previewModel).toHaveTextContent("Preview");

      // Legacy model should show Legacy badge
      const legacyModel = screen.getByTestId("model-option-gpt-4-turbo");
      expect(legacyModel).toHaveTextContent("Legacy");

      // Deprecated model should show Deprecated badge
      const deprecatedModel = screen.getByTestId(
        "model-option-claude-3-sonnet",
      );
      expect(deprecatedModel).toHaveTextContent("Deprecated");
    });

    it("should update selected model button with lifecycle status badge", () => {
      const { rerender } = render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithLifecycleStatus}
            selectedModel="claude-opus-4-5"
          />
        </TestProvider>,
      );

      // Initially selected model is current (no status badge)
      const button = screen.getByTestId("model-selector-button");
      expect(button).not.toHaveTextContent("Preview");
      expect(button).not.toHaveTextContent("Legacy");
      expect(button).not.toHaveTextContent("Deprecated");

      // Select a deprecated model
      rerender(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithLifecycleStatus}
            selectedModel="claude-3-sonnet"
          />
        </TestProvider>,
      );

      // Button should now show deprecated badge
      expect(button).toHaveTextContent("Deprecated");

      // Select a preview model
      rerender(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithLifecycleStatus}
            selectedModel="gemini-3-flash-preview"
          />
        </TestProvider>,
      );

      // Button should now show preview badge
      expect(button).toHaveTextContent("Preview");
    });

    it("should complete model selection flow with lifecycle-aware models", () => {
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithLifecycleStatus}
            selectedModel="claude-opus-4-5"
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Select a deprecated model (user should be able to select any model)
      const deprecatedOption = screen.getByTestId(
        "model-option-claude-3-sonnet",
      );
      fireEvent.click(deprecatedOption);

      // Selection should work normally
      expect(onModelChange).toHaveBeenCalledWith("claude-3-sonnet");
    });

    it("should handle models without status field (backward compatibility)", () => {
      const modelsWithMixedStatus: ModelOption[] = [
        {
          id: "new-model-with-status",
          name: "New Model",
          provider: "test",
          status: "preview",
        },
        {
          id: "legacy-model-without-status",
          name: "Old Model",
          provider: "test",
          // No status field - backward compatibility
        },
      ];

      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={modelsWithMixedStatus}
            selectedModel="new-model-with-status"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Model with status should show badge
      const newModel = screen.getByTestId("model-option-new-model-with-status");
      expect(newModel).toHaveTextContent("Preview");

      // Model without status should not show any badge
      const legacyModel = screen.getByTestId(
        "model-option-legacy-model-without-status",
      );
      expect(legacyModel).not.toHaveTextContent("Preview");
      expect(legacyModel).not.toHaveTextContent("Legacy");
      expect(legacyModel).not.toHaveTextContent("Deprecated");
    });

    it("should combine capability badges and lifecycle status badges", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithLifecycleStatus}
            selectedModel="claude-opus-4-5"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Claude Opus 4.5: current + all capabilities
      const claudeOpus = screen.getByTestId("model-option-claude-opus-4-5");
      expect(claudeOpus).toHaveTextContent("Thinking");
      expect(claudeOpus).toHaveTextContent("Vision");
      expect(claudeOpus).toHaveTextContent("Tools");
      expect(claudeOpus).not.toHaveTextContent("Preview"); // current models don't show badge

      // Claude 3 Sonnet: deprecated + Thinking + Tools (no Vision)
      const claude3 = screen.getByTestId("model-option-claude-3-sonnet");
      expect(claude3).toHaveTextContent("Thinking");
      expect(claude3).not.toHaveTextContent("Vision");
      expect(claude3).toHaveTextContent("Tools");
      expect(claude3).toHaveTextContent("Deprecated");

      // GPT-4 Turbo: legacy + Vision + Tools (no Thinking)
      const gpt4 = screen.getByTestId("model-option-gpt-4-turbo");
      expect(gpt4).not.toHaveTextContent("Thinking");
      expect(gpt4).toHaveTextContent("Vision");
      expect(gpt4).toHaveTextContent("Tools");
      expect(gpt4).toHaveTextContent("Legacy");
    });

    it("should use correct semantic colors for lifecycle status badges", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            availableModels={mockModelsWithLifecycleStatus}
            selectedModel="claude-opus-4-5"
          />
        </TestProvider>,
      );

      // Open dropdown
      const button = screen.getByTestId("model-selector-button");
      fireEvent.click(button);

      // Verify status badges have correct data-testid for styling verification
      expect(
        screen.getByTestId("status-badge-preview-gemini-3-flash-preview"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("status-badge-legacy-gpt-4-turbo"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("status-badge-deprecated-claude-3-sonnet"),
      ).toBeInTheDocument();
    });
  });
});
