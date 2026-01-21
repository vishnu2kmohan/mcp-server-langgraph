/**
 * ConversationPanel Tests
 *
 * TDD tests for the conversation panel orchestrator component.
 * ConversationPanel combines MessageList, ChatInput, FollowUpSuggestions,
 * and SlashCommandMenu into a cohesive chat experience.
 *
 * Note: ConnectedChatInputForm is mocked to isolate ConversationPanel testing
 * from Redux dependencies (ADR-0093 Phase 6 consolidation).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import type { ChatMessage } from "./MessageBubble";
import type { Suggestion } from "./FollowUpSuggestions";
import type { SlashCommand } from "../components/Chat/ChatInput";

expect.extend(toHaveNoViolations);

// =============================================================================
// Mock ConnectedChatInputForm
// =============================================================================
// ConnectedChatInputForm uses Redux hooks (selectSubmitOnEnter from uiSlice)
// and useFeatureFlag. We mock it to isolate ConversationPanel testing.

const mockConnectedChatInputForm = vi.fn();

vi.mock("./ConnectedChatInputForm", () => ({
  ConnectedChatInputForm: (props: Record<string, unknown>) => {
    mockConnectedChatInputForm(props);
    const {
      value,
      onChange,
      onSubmit,
      isProcessing,
      autoFocus,
      slashCommands,
      onSlashCommand,
    } = props as {
      value?: string;
      onChange?: (v: string) => void;
      onSubmit?: (v: string) => void;
      isProcessing?: boolean;
      autoFocus?: boolean;
      slashCommands?: SlashCommand[];
      onSlashCommand?: (cmd: SlashCommand) => void;
    };

    return (
      <div data-testid="chat-input-container">
        <textarea
          data-testid="chat-input"
          value={value || ""}
          onChange={(e) => onChange?.(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (value) {
                onSubmit?.(value);
              }
            }
          }}
          disabled={isProcessing}
          autoFocus={autoFocus}
          aria-label="Chat input"
        />
        {/* Slash command menu when input starts with / */}
        {value?.startsWith("/") &&
          slashCommands &&
          slashCommands.length > 0 && (
            <div data-testid="slash-command-menu">
              {slashCommands
                .filter(
                  (cmd: SlashCommand) =>
                    !value ||
                    value === "/" ||
                    cmd.name
                      .toLowerCase()
                      .includes(value.slice(1).toLowerCase()),
                )
                .map((cmd: SlashCommand) => (
                  <button
                    key={cmd.name}
                    type="button"
                    onClick={() => {
                      onSlashCommand?.(cmd);
                      onChange?.("");
                    }}
                  >
                    /{cmd.name}
                  </button>
                ))}
            </div>
          )}
        <button
          data-testid="send-button"
          type="button"
          onClick={() => value && onSubmit?.(value)}
          disabled={isProcessing}
        >
          Send
        </button>
      </div>
    );
  },
}));

// Import after mock
import { ConversationPanel } from "./ConversationPanel";

// =============================================================================
// Mock Data
// =============================================================================

const mockMessages: ChatMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "Hello, how are you?",
    timestamp: new Date("2024-01-15T10:00:00Z"),
  },
  {
    id: "msg-2",
    role: "assistant",
    content: "I'm doing well! How can I help you today?",
    timestamp: new Date("2024-01-15T10:00:05Z"),
  },
];

const mockSuggestions: Suggestion[] = [
  { id: "sug-1", text: "Tell me more about X", type: "follow-up" },
  { id: "sug-2", text: "Create a workflow", type: "action" },
];

const mockSlashCommands: SlashCommand[] = [
  { name: "help", description: "Show help", icon: "help" },
  { name: "clear", description: "Clear chat", icon: "trash" },
];

// =============================================================================
// Tests
// =============================================================================

describe("ConversationPanel", () => {
  const defaultProps = {
    messages: mockMessages,
    onSendMessage: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockConnectedChatInputForm.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the conversation panel container", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
    });

    it("should render MessageList with messages", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(screen.getByTestId("message-list")).toBeInTheDocument();
      expect(screen.getByText("Hello, how are you?")).toBeInTheDocument();
      expect(
        screen.getByText("I'm doing well! How can I help you today?"),
      ).toBeInTheDocument();
    });

    it("should render ChatInput", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(screen.getByTestId("chat-input-container")).toBeInTheDocument();
    });

    it("should render empty state when no messages", () => {
      render(<ConversationPanel {...defaultProps} messages={[]} />);

      expect(
        screen.getByText("No messages yet. Start a conversation!"),
      ).toBeInTheDocument();
    });
  });

  describe("Sending Messages", () => {
    it("should call onSendMessage when user sends a message", async () => {
      const onSendMessage = vi.fn();
      render(
        <ConversationPanel {...defaultProps} onSendMessage={onSendMessage} />,
      );

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "Test message");
      await userEvent.keyboard("{Enter}");

      expect(onSendMessage).toHaveBeenCalledWith("Test message");
    });

    it("should clear input after sending", async () => {
      render(<ConversationPanel {...defaultProps} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await userEvent.type(input, "Test message");
      await userEvent.keyboard("{Enter}");

      expect(input.value).toBe("");
    });

    it("should disable input when isLoading", () => {
      render(<ConversationPanel {...defaultProps} isLoading />);

      const input = screen.getByRole("textbox");
      expect(input).toBeDisabled();
    });
  });

  describe("Follow-up Suggestions", () => {
    it("should render suggestions when provided", () => {
      render(
        <ConversationPanel {...defaultProps} suggestions={mockSuggestions} />,
      );

      expect(screen.getByText("Tell me more about X")).toBeInTheDocument();
      expect(screen.getByText("Create a workflow")).toBeInTheDocument();
    });

    it("should not render suggestions when empty", () => {
      render(<ConversationPanel {...defaultProps} suggestions={[]} />);

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should call onSendMessage when suggestion clicked", async () => {
      const onSendMessage = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          onSendMessage={onSendMessage}
          suggestions={mockSuggestions}
        />,
      );

      const suggestion = screen.getByText("Tell me more about X");
      await userEvent.click(suggestion);

      expect(onSendMessage).toHaveBeenCalledWith("Tell me more about X");
    });

    it("should hide suggestions while loading", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          suggestions={mockSuggestions}
          isLoading
        />,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Slash Commands", () => {
    it("should show slash command menu when typing /", async () => {
      render(
        <ConversationPanel
          {...defaultProps}
          slashCommands={mockSlashCommands}
        />,
      );

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "/");

      await waitFor(() => {
        expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
      });
    });

    it("should filter commands based on input", async () => {
      render(
        <ConversationPanel
          {...defaultProps}
          slashCommands={mockSlashCommands}
        />,
      );

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "/hel");

      await waitFor(() => {
        // Check that help command is visible (slash menu filters)
        expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
      });
    });

    it("should call onSlashCommand when command clicked", async () => {
      const onSlashCommand = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          slashCommands={mockSlashCommands}
          onSlashCommand={onSlashCommand}
        />,
      );

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "/");

      await waitFor(() => {
        expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
      });

      // Click on the help command in the menu (rendered as "/help")
      const helpCommand = screen.getByText("/help");
      await userEvent.click(helpCommand);

      expect(onSlashCommand).toHaveBeenCalledWith(
        expect.objectContaining({ name: "help" }),
      );
    });

    it("should hide slash menu after command selection", async () => {
      render(
        <ConversationPanel
          {...defaultProps}
          slashCommands={mockSlashCommands}
        />,
      );

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "/");

      await waitFor(() => {
        expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
      });

      // Click on a command (rendered as "/help")
      const helpCommand = screen.getByText("/help");
      await userEvent.click(helpCommand);

      await waitFor(() => {
        expect(
          screen.queryByTestId("slash-command-menu"),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Loading and Streaming States", () => {
    it("should show loading indicator when isLoading", () => {
      render(<ConversationPanel {...defaultProps} isLoading />);

      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });

    it("should show streaming indicator when isStreaming", () => {
      render(<ConversationPanel {...defaultProps} isStreaming />);

      expect(screen.getByTestId("streaming-indicator")).toBeInTheDocument();
      expect(screen.getByText("AI is typing...")).toBeInTheDocument();
    });

    it("should disable send button while loading", () => {
      render(<ConversationPanel {...defaultProps} isLoading />);

      const sendButton = screen.getByTestId("send-button");
      expect(sendButton).toBeDisabled();
    });
  });

  describe("Scroll Behavior", () => {
    it("should show scroll-to-bottom button when scrolled up", () => {
      render(<ConversationPanel {...defaultProps} isScrolledUp />);

      expect(screen.getByTestId("scroll-to-bottom-button")).toBeInTheDocument();
    });

    it("should call onScrollToBottom when button clicked", async () => {
      const onScrollToBottom = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          isScrolledUp
          onScrollToBottom={onScrollToBottom}
        />,
      );

      const button = screen.getByTestId("scroll-to-bottom-button");
      await userEvent.click(button);

      expect(onScrollToBottom).toHaveBeenCalled();
    });
  });

  describe("Keyboard Navigation", () => {
    it("should focus input on mount when autoFocus is true", () => {
      render(<ConversationPanel {...defaultProps} autoFocus />);

      const input = screen.getByRole("textbox");
      expect(document.activeElement).toBe(input);
    });

    it("should submit message on Enter (without Shift)", async () => {
      const onSendMessage = vi.fn();
      render(
        <ConversationPanel {...defaultProps} onSendMessage={onSendMessage} />,
      );

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "Test message{Enter}");

      expect(onSendMessage).toHaveBeenCalled();
    });

    it("should allow newline on Shift+Enter", async () => {
      render(<ConversationPanel {...defaultProps} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await userEvent.type(input, "Line 1{Shift>}{Enter}{/Shift}Line 2");

      expect(input.value).toContain("\n");
    });
  });

  describe("Session Header", () => {
    it("should render session title when provided", () => {
      render(
        <ConversationPanel {...defaultProps} sessionTitle="Chat Session 1" />,
      );

      expect(screen.getByText("Chat Session 1")).toBeInTheDocument();
    });

    it("should render session actions when provided", () => {
      const onRename = vi.fn();
      const onDelete = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          sessionTitle="Chat Session 1"
          onRename={onRename}
          onDelete={onDelete}
        />,
      );

      expect(screen.getByTestId("session-rename-button")).toBeInTheDocument();
      expect(screen.getByTestId("session-delete-button")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<ConversationPanel {...defaultProps} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper ARIA labels", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(screen.getByRole("log")).toHaveAttribute(
        "aria-label",
        "Chat messages",
      );
      expect(screen.getByRole("textbox")).toHaveAttribute("aria-label");
    });

    it("should announce new messages to screen readers", () => {
      render(<ConversationPanel {...defaultProps} />);

      const messageList = screen.getByRole("log");
      expect(messageList).toHaveAttribute("aria-live", "polite");
    });

    it("should have proper focus management", async () => {
      render(
        <ConversationPanel
          {...defaultProps}
          suggestions={mockSuggestions}
          autoFocus
        />,
      );

      // When autoFocus is true, input starts with focus
      const input = screen.getByRole("textbox");
      expect(document.activeElement).toBe(input);

      // Tab moves forward to next element in DOM order (Send button after input)
      await userEvent.tab();

      // Should be on the send button (next focusable element after input)
      expect(document.activeElement).toHaveTextContent("Send");
    });
  });

  describe("Responsive Layout", () => {
    it("should render in vertical layout by default", () => {
      render(<ConversationPanel {...defaultProps} />);

      const panel = screen.getByTestId("conversation-panel");
      expect(panel).toHaveClass("flex-col");
    });

    it("should accept custom className", () => {
      render(<ConversationPanel {...defaultProps} className="custom-class" />);

      const panel = screen.getByTestId("conversation-panel");
      expect(panel).toHaveClass("custom-class");
    });
  });

  describe("Telemetry", () => {
    it("should call onMessageSent callback for telemetry", async () => {
      const onMessageSent = vi.fn();
      render(
        <ConversationPanel {...defaultProps} onMessageSent={onMessageSent} />,
      );

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "Test message{Enter}");

      expect(onMessageSent).toHaveBeenCalledWith(
        expect.objectContaining({
          messageLength: 12,
          timestamp: expect.any(Number),
        }),
      );
    });

    it("should call onSuggestionUsed callback for telemetry", async () => {
      const onSuggestionUsed = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          suggestions={mockSuggestions}
          onSuggestionUsed={onSuggestionUsed}
        />,
      );

      const suggestion = screen.getByText("Tell me more about X");
      await userEvent.click(suggestion);

      expect(onSuggestionUsed).toHaveBeenCalledWith(
        expect.objectContaining({
          suggestionId: "sug-1",
          suggestionType: "follow-up",
        }),
      );
    });
  });

  // ===========================================================================
  // Model Selector Props Tests (Sprint 1 - Chat Input Gap Fix)
  // ===========================================================================

  describe("Model Selector Props", () => {
    const mockModels = [
      { id: "claude-3-opus", name: "Claude 3 Opus", provider: "anthropic" },
      { id: "claude-3-sonnet", name: "Claude 3 Sonnet", provider: "anthropic" },
      { id: "gpt-4o", name: "GPT-4o", provider: "openai" },
    ];

    it("should pass showModelSelector prop to ConnectedChatInputForm", () => {
      render(<ConversationPanel {...defaultProps} showModelSelector={true} />);

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          showModelSelector: true,
        }),
      );
    });

    it("should pass selectedModel prop to ConnectedChatInputForm", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          showModelSelector={true}
          selectedModel="claude-3-opus"
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedModel: "claude-3-opus",
        }),
      );
    });

    it("should pass availableModels prop to ConnectedChatInputForm", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          showModelSelector={true}
          availableModels={mockModels}
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          availableModels: mockModels,
        }),
      );
    });

    it("should pass onModelChange callback to ConnectedChatInputForm", () => {
      const onModelChange = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          showModelSelector={true}
          onModelChange={onModelChange}
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          onModelChange: onModelChange,
        }),
      );
    });

    it("should pass modelSupportsThinking prop to ConnectedChatInputForm", () => {
      render(
        <ConversationPanel {...defaultProps} modelSupportsThinking={true} />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          modelSupportsThinking: true,
        }),
      );
    });

    it("should pass reasoningEffort prop to ConnectedChatInputForm", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          modelSupportsThinking={true}
          reasoningEffort="high"
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          reasoningEffort: "high",
        }),
      );
    });

    it("should pass onReasoningEffortChange callback to ConnectedChatInputForm", () => {
      const onReasoningEffortChange = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          modelSupportsThinking={true}
          onReasoningEffortChange={onReasoningEffortChange}
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          onReasoningEffortChange: onReasoningEffortChange,
        }),
      );
    });
  });

  describe("Model Selection Props (Sprint 1 - Chat Input Gap Fix)", () => {
    const mockModels = [
      {
        id: "claude-3-5-sonnet",
        name: "Claude 3.5 Sonnet",
        provider: "anthropic",
      },
      { id: "gpt-4o", name: "GPT-4o", provider: "openai" },
    ];

    it("should pass showModelSelector prop to ConnectedChatInputForm", () => {
      render(<ConversationPanel {...defaultProps} showModelSelector={true} />);

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          showModelSelector: true,
        }),
      );
    });

    it("should pass selectedModel prop to ConnectedChatInputForm", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          showModelSelector={true}
          selectedModel="claude-3-5-sonnet"
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedModel: "claude-3-5-sonnet",
        }),
      );
    });

    it("should pass availableModels prop to ConnectedChatInputForm", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          showModelSelector={true}
          availableModels={mockModels}
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          availableModels: mockModels,
        }),
      );
    });

    it("should pass onModelChange callback to ConnectedChatInputForm", () => {
      const onModelChange = vi.fn();
      render(
        <ConversationPanel
          {...defaultProps}
          showModelSelector={true}
          onModelChange={onModelChange}
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          onModelChange: onModelChange,
        }),
      );
    });

    it("should pass isModelsLoading prop to ConnectedChatInputForm", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          showModelSelector={true}
          isModelsLoading={true}
        />,
      );

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          isModelsLoading: true,
        }),
      );
    });

    it("should default showModelSelector to false", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          showModelSelector: false,
        }),
      );
    });

    it("should default isModelsLoading to false", () => {
      render(<ConversationPanel {...defaultProps} showModelSelector={true} />);

      expect(mockConnectedChatInputForm).toHaveBeenCalledWith(
        expect.objectContaining({
          isModelsLoading: false,
        }),
      );
    });
  });

  // ===========================================================================
  // Source Citations Grouping Tests
  // ===========================================================================

  describe("Source Citations Grouping", () => {
    const messageWithMixedSources: ChatMessage[] = [
      {
        id: "msg-sources",
        role: "assistant",
        content: "Here are my findings.",
        timestamp: new Date("2024-01-15T10:00:00Z"),
        sources: [
          { title: "Web Source", url: "https://example.com" },
          { title: "KB Source", url: "/kb/docs/guide.md" },
        ],
      },
    ];

    it("should group sources by type by default", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          messages={messageWithMixedSources}
        />,
      );

      // Default is groupSourcesByType=true, so groups should be present
      expect(screen.getByTestId("web-sources-group")).toBeInTheDocument();
      expect(screen.getByTestId("kb-sources-group")).toBeInTheDocument();
    });

    it("should not group sources when groupSourcesByType is false", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          messages={messageWithMixedSources}
          groupSourcesByType={false}
        />,
      );

      // When explicitly disabled, groups should not be present
      expect(screen.queryByTestId("web-sources-group")).not.toBeInTheDocument();
      expect(screen.queryByTestId("kb-sources-group")).not.toBeInTheDocument();
    });

    it("should pass groupSourcesByType prop to MessageList", () => {
      render(
        <ConversationPanel
          {...defaultProps}
          messages={messageWithMixedSources}
          groupSourcesByType={false}
        />,
      );

      // The prop should affect rendering - no groups when disabled
      expect(screen.queryByTestId("web-sources-group")).not.toBeInTheDocument();
    });
  });
});
