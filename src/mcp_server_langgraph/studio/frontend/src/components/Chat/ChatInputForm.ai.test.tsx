/**
 * ChatInputForm AI Feature Tests
 *
 * Split from ChatInputForm.test.tsx to stay under 1000 lines.
 * Contains tests for:
 * - Inline AI Suggestions (Sprint 6)
 * - RichText Mode (Sprint 5.2)
 * - KnowledgeBaseFocus Integration
 *
 * @see docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe } from "jest-axe";
import { ChatInputForm, UploadFile } from "./ChatInputForm";

describe("ChatInputForm AI Features", () => {
  const defaultProps = {
    input: "",
    onInputChange: vi.fn(),
    onSubmit: vi.fn(),
    isProcessing: false,
    isListening: false,
    isVoiceSupported: true,
    voiceError: null as string | null,
    onStartListening: vi.fn(),
    onStopListening: vi.fn(),
    uploadFiles: [] as UploadFile[],
    isUploading: false,
    isDragging: false,
    fileError: null as string | null,
    onSelectFiles: vi.fn(),
    onRemoveFile: vi.fn(),
    dragHandlers: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // Inline AI Suggestions (Sprint 6)
  // ===========================================================================
  describe("Inline AI Suggestions (Sprint 6)", () => {
    it("should not show inline suggestion when feature is disabled", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello"
          enableInlineSuggestions={false}
          inlineSuggestion="world"
        />,
      );

      expect(screen.queryByTestId("inline-suggestion")).not.toBeInTheDocument();
    });

    it("should show inline suggestion ghost text when enabled", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world, how are you?"
        />,
      );

      const suggestion = screen.getByTestId("inline-suggestion");
      expect(suggestion).toBeInTheDocument();
      expect(suggestion).toHaveTextContent("world, how are you?");
    });

    it("should not show inline suggestion when input is empty", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input=""
          enableInlineSuggestions={true}
          inlineSuggestion="some suggestion"
        />,
      );

      expect(screen.queryByTestId("inline-suggestion")).not.toBeInTheDocument();
    });

    it("should not show inline suggestion when suggestion is empty", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello"
          enableInlineSuggestions={true}
          inlineSuggestion=""
        />,
      );

      expect(screen.queryByTestId("inline-suggestion")).not.toBeInTheDocument();
    });

    it("should call onAcceptSuggestion when Tab is pressed", () => {
      const onAcceptSuggestion = vi.fn();
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
          onAcceptSuggestion={onAcceptSuggestion}
        />,
      );

      const textarea = screen.getByPlaceholderText(/type your message/i);
      fireEvent.keyDown(textarea, { key: "Tab" });

      expect(onAcceptSuggestion).toHaveBeenCalledWith("world");
    });

    it("should not call onAcceptSuggestion when Tab pressed without suggestion", () => {
      const onAcceptSuggestion = vi.fn();
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello"
          enableInlineSuggestions={true}
          inlineSuggestion=""
          onAcceptSuggestion={onAcceptSuggestion}
        />,
      );

      const textarea = screen.getByPlaceholderText(/type your message/i);
      fireEvent.keyDown(textarea, { key: "Tab" });

      expect(onAcceptSuggestion).not.toHaveBeenCalled();
    });

    it("should call onDismissSuggestion when Escape is pressed", () => {
      const onDismissSuggestion = vi.fn();
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
          onDismissSuggestion={onDismissSuggestion}
        />,
      );

      const textarea = screen.getByPlaceholderText(/type your message/i);
      fireEvent.keyDown(textarea, { key: "Escape" });

      expect(onDismissSuggestion).toHaveBeenCalled();
    });

    it("should show suggestion loading indicator when fetching", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello"
          enableInlineSuggestions={true}
          isSuggestionLoading={true}
        />,
      );

      expect(screen.getByTestId("suggestion-loading")).toBeInTheDocument();
    });

    it("should not show suggestion when processing message", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello"
          isProcessing={true}
          enableInlineSuggestions={true}
          inlineSuggestion="world"
        />,
      );

      expect(screen.queryByTestId("inline-suggestion")).not.toBeInTheDocument();
    });

    it("should render ghost text with correct styling", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
        />,
      );

      const suggestion = screen.getByTestId("inline-suggestion");
      expect(suggestion).toHaveClass("text-gray-400");
    });

    it("should show hint text about Tab to accept", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
        />,
      );

      expect(screen.getByTestId("suggestion-hint")).toHaveTextContent(
        /tab.*accept/i,
      );
    });

    it("should position suggestion after input text", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          input="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
        />,
      );

      // The suggestion overlay should contain both input text and suggestion
      const overlay = screen.getByTestId("inline-suggestion-overlay");
      expect(overlay).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // RichText Mode Tests (Sprint 5.2 - Pill + RichTextInput as Default)
  // ===========================================================================
  describe("RichText Mode", () => {
    describe("No Regressions - Default Behavior", () => {
      it("should render textarea when enableRichTextMode=false (backwards compat)", () => {
        render(<ChatInputForm {...defaultProps} enableRichTextMode={false} />);

        // Textarea should be present
        expect(
          screen.getByPlaceholderText(/type your message/i),
        ).toBeInTheDocument();
        // RichTextInput should NOT be present
        expect(screen.queryByTestId("rich-text-input")).not.toBeInTheDocument();
      });

      it("should preserve submitOnEnter behavior from prop (not hardcoded)", () => {
        const onSubmit = vi.fn();

        // Test submitOnEnter=true (ChatGPT style: Enter to submit)
        const { unmount } = render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            submitOnEnter={true}
            input="Hello"
            onSubmit={onSubmit}
          />,
        );

        const textarea = screen.getByRole("textbox", {
          name: /message input/i,
        });
        fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
        expect(onSubmit).toHaveBeenCalledTimes(1);

        unmount();
        onSubmit.mockClear();

        // Test submitOnEnter=false (Legacy style: Ctrl+Enter to submit)
        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            submitOnEnter={false}
            input="Hello"
            onSubmit={onSubmit}
          />,
        );

        const textareaLegacy = screen.getByRole("textbox", {
          name: /message input/i,
        });
        // Enter alone should NOT submit
        fireEvent.keyDown(textareaLegacy, { key: "Enter", shiftKey: false });
        expect(onSubmit).not.toHaveBeenCalled();

        // Ctrl+Enter SHOULD submit
        fireEvent.keyDown(textareaLegacy, { key: "Enter", ctrlKey: true });
        expect(onSubmit).toHaveBeenCalledTimes(1);
      });

      it("should render slash command menu in RichText mode", () => {
        const slashCommands = [
          { id: "help", name: "help", description: "Show help" },
          { id: "clear", name: "clear", description: "Clear chat" },
        ];

        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            input="/"
            slashCommands={slashCommands}
          />,
        );

        // Slash command menu should appear
        expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
      });

      it("should render voice button in RichText mode", () => {
        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            isVoiceSupported={true}
          />,
        );

        // Voice button should be accessible
        expect(
          screen.getByRole("button", { name: /voice input/i }),
        ).toBeInTheDocument();
      });

      it("should render file upload button in RichText mode", () => {
        render(<ChatInputForm {...defaultProps} enableRichTextMode={true} />);

        // File upload button should be accessible
        expect(
          screen.getByRole("button", { name: /attach file/i }),
        ).toBeInTheDocument();
      });
    });

    describe("New RichText Behavior", () => {
      it("should render RichTextInput when enableRichTextMode=true", () => {
        render(<ChatInputForm {...defaultProps} enableRichTextMode={true} />);

        // RichTextInput should be present (has data-testid="rich-text-input")
        expect(screen.getByTestId("rich-text-input")).toBeInTheDocument();
      });

      it("should apply pill container styling in RichText mode", () => {
        render(<ChatInputForm {...defaultProps} enableRichTextMode={true} />);

        // Pill container with rounded-2xl class should be present
        const pillContainer = screen.getByTestId("pill-container");
        expect(pillContainer).toHaveClass("rounded-2xl");
        expect(pillContainer).toHaveClass("shadow-lg");
      });

      it("should accept inline suggestion with Tab in RichText mode", () => {
        const onAcceptSuggestion = vi.fn();

        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            input="Hello "
            enableInlineSuggestions={true}
            inlineSuggestion="world"
            onAcceptSuggestion={onAcceptSuggestion}
          />,
        );

        const textarea = screen.getByRole("textbox", {
          name: /message input/i,
        });
        fireEvent.keyDown(textarea, { key: "Tab" });

        expect(onAcceptSuggestion).toHaveBeenCalledWith("world");
      });

      it("should hide thinking toggle in RichText mode (product approved)", () => {
        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            modelSupportsThinking={true}
            enableThinking={true}
          />,
        );

        // Thinking toggle should NOT be visible in RichText mode
        expect(
          screen.queryByRole("switch", { name: /extended thinking/i }),
        ).not.toBeInTheDocument();
      });

      it("should show ReasoningEffortSelector when model supports thinking in RichText mode", () => {
        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            modelSupportsThinking={true}
            enableThinking={true}
            reasoningEffort="medium"
            onReasoningEffortChange={vi.fn()}
          />,
        );

        // ReasoningEffortSelector should be visible (uses data-testid in compact mode)
        expect(
          screen.getByTestId("reasoning-effort-selector"),
        ).toBeInTheDocument();
      });

      it("should not show ReasoningEffortSelector when model does not support thinking", () => {
        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            modelSupportsThinking={false}
          />,
        );

        // ReasoningEffortSelector should NOT be visible
        expect(
          screen.queryByRole("button", { name: /reasoning effort/i }),
        ).not.toBeInTheDocument();
      });
    });

    describe("Accessibility in RichText Mode", () => {
      it("should have no accessibility violations in RichText mode", async () => {
        const { container } = render(
          <ChatInputForm {...defaultProps} enableRichTextMode={true} />,
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
      });

      it("should support keyboard navigation in RichText mode", () => {
        render(
          <ChatInputForm
            {...defaultProps}
            enableRichTextMode={true}
            isVoiceSupported={true}
          />,
        );

        // Tab through focusable elements
        const textarea = screen.getByRole("textbox", {
          name: /message input/i,
        });
        const voiceButton = screen.getByRole("button", {
          name: /voice input/i,
        });
        const sendButton = screen.getByRole("button", { name: /send/i });

        // All elements should be focusable
        expect(textarea).not.toBeDisabled();
        expect(voiceButton).not.toBeDisabled();
        expect(sendButton).toBeDisabled(); // Disabled when input is empty
      });
    });
  });

  // ===========================================================================
  // KnowledgeBaseFocus Integration (TDD - RED Phase)
  // ===========================================================================
  describe("KnowledgeBaseFocus Integration", () => {
    it("should render KnowledgeBaseFocus when showKBFocus is true", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="all"
          onKBFocusChange={vi.fn()}
        />,
      );

      expect(screen.getByTestId("kb-focus-button")).toBeInTheDocument();
    });

    it("should not render KnowledgeBaseFocus when showKBFocus is false", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={false}
        />,
      );

      expect(screen.queryByTestId("kb-focus-button")).not.toBeInTheDocument();
    });

    it("should not render KnowledgeBaseFocus by default", () => {
      render(<ChatInputForm {...defaultProps} enableRichTextMode={true} />);

      expect(screen.queryByTestId("kb-focus-button")).not.toBeInTheDocument();
    });

    it("should display current KB focus mode", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="kb_only"
          onKBFocusChange={vi.fn()}
        />,
      );

      expect(screen.getByText("Knowledge Base")).toBeInTheDocument();
    });

    it("should call onKBFocusChange when focus mode changes", async () => {
      const handleChange = vi.fn();
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="all"
          onKBFocusChange={handleChange}
        />,
      );

      // Click the dropdown button
      fireEvent.click(screen.getByTestId("kb-focus-button"));

      // Click an option (find by description to avoid duplicate text issues)
      const options = screen.getAllByRole("option");
      const webOption = options.find((opt) =>
        opt.textContent?.includes("Search external web only"),
      );
      expect(webOption).toBeDefined();
      fireEvent.click(webOption!);

      expect(handleChange).toHaveBeenCalledWith("web_only");
    });

    it("should disable KnowledgeBaseFocus when isProcessing is true", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="all"
          onKBFocusChange={vi.fn()}
          isProcessing={true}
        />,
      );

      expect(screen.getByTestId("kb-focus-button")).toBeDisabled();
    });

    it("should show KB status indicator when kbStatus is provided", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="kb_only"
          onKBFocusChange={vi.fn()}
          kbStatus="ready"
        />,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-green-500");
    });

    it("should show misconfigured status with yellow indicator", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="kb_only"
          onKBFocusChange={vi.fn()}
          kbStatus="misconfigured"
          kbStatusMessage="Missing QDRANT_URL"
        />,
      );

      const indicator = screen.getByTestId("kb-status-indicator");
      expect(indicator).toHaveClass("bg-yellow-500");
    });

    it("should render KnowledgeBaseFocus in compact mode", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="all"
          onKBFocusChange={vi.fn()}
          kbFocusCompact={true}
        />,
      );

      const button = screen.getByTestId("kb-focus-button");
      expect(button).toHaveClass("p-2");
    });

    it("should position KnowledgeBaseFocus in controls row", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          enableRichTextMode={true}
          showKBFocus={true}
          kbFocusValue="all"
          onKBFocusChange={vi.fn()}
        />,
      );

      // KB Focus should be in the controls row (flex container with gap-2)
      const button = screen.getByTestId("kb-focus-button");
      const controlsRow = button.closest(".flex.items-center.gap-2");
      expect(controlsRow).toBeInTheDocument();
    });
  });
});
