/**
 * ConversationPanel UnifiedMessageList Feature Flag Tests
 *
 * TDD tests for ADR-0104 message rendering consolidation.
 * Tests conditional rendering of UnifiedMessageList vs MessageList
 * based on the unified_message_list feature flag.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import type { ChatMessage } from "./MessageBubble";

// =============================================================================
// Mocks
// =============================================================================

// Mock the feature flag context
const mockIsEnabled = vi.fn();
vi.mock("../contexts/FeatureFlagContext", () => ({
  useFeatureFlags: () => ({
    isEnabled: mockIsEnabled,
    isLoading: false,
    isError: false,
    flags: {},
  }),
}));

// Track which message list component is rendered
const mockMessageList = vi.fn();
const mockUnifiedMessageList = vi.fn();

vi.mock("./MessageList", () => ({
  MessageList: (props: Record<string, unknown>) => {
    mockMessageList(props);
    return <div data-testid="message-list">MessageList</div>;
  },
}));

vi.mock("./UnifiedMessageList", () => ({
  UnifiedMessageList: (props: Record<string, unknown>) => {
    mockUnifiedMessageList(props);
    return <div data-testid="unified-message-list">UnifiedMessageList</div>;
  },
}));

// Mock ConnectedChatInputForm to avoid Redux dependencies
vi.mock("./ConnectedChatInputForm", () => ({
  ConnectedChatInputForm: () => (
    <div data-testid="chat-input-container">
      <textarea data-testid="chat-input" aria-label="Chat input" />
    </div>
  ),
}));

// Import after mocks
import { ConversationPanel } from "./ConversationPanel";

// =============================================================================
// Test Data
// =============================================================================

const createMockMessage = (
  overrides: Partial<ChatMessage> = {},
): ChatMessage => ({
  id: `msg-${Math.random().toString(36).slice(2, 11)}`,
  role: "user",
  content: "Hello, world!",
  timestamp: Date.now(),
  ...overrides,
});

const defaultProps = {
  messages: [createMockMessage()],
  onSendMessage: vi.fn(),
};

// =============================================================================
// Tests
// =============================================================================

describe("ConversationPanel - UnifiedMessageList Feature Flag", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsEnabled.mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Feature Flag: unified_message_list = false (default)", () => {
    beforeEach(() => {
      mockIsEnabled.mockImplementation((flag: string) => {
        if (flag === "unified_message_list") return false;
        return false;
      });
    });

    it("should render MessageList when unified_message_list flag is disabled", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(screen.getByTestId("message-list")).toBeInTheDocument();
      expect(
        screen.queryByTestId("unified-message-list"),
      ).not.toBeInTheDocument();
    });

    it("should pass messages to MessageList", () => {
      const messages = [
        createMockMessage({ content: "First" }),
        createMockMessage({ content: "Second" }),
      ];

      render(<ConversationPanel {...defaultProps} messages={messages} />);

      expect(mockMessageList).toHaveBeenCalled();
      expect(mockMessageList.mock.calls[0][0].messages).toEqual(messages);
    });

    it("should pass isLoading to MessageList", () => {
      render(<ConversationPanel {...defaultProps} isLoading={true} />);

      expect(mockMessageList).toHaveBeenCalled();
      expect(mockMessageList.mock.calls[0][0].isLoading).toBe(true);
    });

    it("should pass isStreaming to MessageList", () => {
      render(<ConversationPanel {...defaultProps} isStreaming={true} />);

      expect(mockMessageList).toHaveBeenCalled();
      expect(mockMessageList.mock.calls[0][0].isStreaming).toBe(true);
    });
  });

  describe("Feature Flag: unified_message_list = true", () => {
    beforeEach(() => {
      mockIsEnabled.mockImplementation((flag: string) => {
        if (flag === "unified_message_list") return true;
        return false;
      });
    });

    it("should render UnifiedMessageList when unified_message_list flag is enabled", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(screen.getByTestId("unified-message-list")).toBeInTheDocument();
      expect(screen.queryByTestId("message-list")).not.toBeInTheDocument();
    });

    it("should pass messages to UnifiedMessageList", () => {
      const messages = [
        createMockMessage({ content: "First" }),
        createMockMessage({ content: "Second" }),
      ];

      render(<ConversationPanel {...defaultProps} messages={messages} />);

      expect(mockUnifiedMessageList).toHaveBeenCalled();
      expect(mockUnifiedMessageList.mock.calls[0][0].messages).toEqual(
        messages,
      );
    });

    it("should pass isLoading to UnifiedMessageList", () => {
      render(<ConversationPanel {...defaultProps} isLoading={true} />);

      expect(mockUnifiedMessageList).toHaveBeenCalled();
      expect(mockUnifiedMessageList.mock.calls[0][0].isLoading).toBe(true);
    });

    it("should pass isStreaming to UnifiedMessageList", () => {
      render(<ConversationPanel {...defaultProps} isStreaming={true} />);

      expect(mockUnifiedMessageList).toHaveBeenCalled();
      expect(mockUnifiedMessageList.mock.calls[0][0].isStreaming).toBe(true);
    });

    it("should pass className to UnifiedMessageList", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(mockUnifiedMessageList).toHaveBeenCalled();
      expect(mockUnifiedMessageList.mock.calls[0][0].className).toBe("flex-1");
    });
  });

  describe("Feature Flag Check", () => {
    it("should call isEnabled with 'unified_message_list'", () => {
      render(<ConversationPanel {...defaultProps} />);

      expect(mockIsEnabled).toHaveBeenCalledWith("unified_message_list");
    });
  });
});
