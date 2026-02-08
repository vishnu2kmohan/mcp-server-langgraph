/**
 * MessageActions Component Tests
 *
 * Tests for the message actions dropdown menu that provides
 * Copy, Edit, Regenerate, and Delete functionality.
 *
 * TDD RED Phase: Write failing tests first.
 */

import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MessageActions, type MessageActionsProps } from "./MessageActions";

import { TestProvider } from "@/test-utils";

// Mock clipboard API
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.assign(navigator, { clipboard: mockClipboard });

describe("MessageActions", () => {
  const defaultProps: MessageActionsProps = {
    messageId: "msg-001",
    content: "This is a test message",
    role: "assistant",
    onEdit: vi.fn(),
    onRegenerate: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render the actions trigger button", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByTestId("message-actions-trigger")).toBeInTheDocument();
    });

    it("should not show menu initially", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("message-actions-menu"),
      ).not.toBeInTheDocument();
    });

    it("should show menu when trigger is clicked", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("message-actions-menu")).toBeInTheDocument();
    });

    it("should close menu when clicking outside", async () => {
      render(
        <TestProvider>
          <div>
            <MessageActions {...defaultProps} />
            <div data-testid="outside">Outside</div>
          </div>
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("message-actions-menu")).toBeInTheDocument();

      // Component listens for mousedown, not click
      fireEvent.mouseDown(screen.getByTestId("outside"));
      await waitFor(() => {
        expect(
          screen.queryByTestId("message-actions-menu"),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("copy action", () => {
    it("should show copy button for all message roles", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-copy")).toBeInTheDocument();
    });

    it("should copy content to clipboard when copy is clicked", async () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-copy"));

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith(
          "This is a test message",
        );
      });
    });

    it("should show copied confirmation after copying", async () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-copy"));

      await waitFor(() => {
        expect(screen.getByTestId("copy-success")).toBeInTheDocument();
      });
    });
  });

  describe("edit action", () => {
    it("should show edit button for user messages", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="user" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-edit")).toBeInTheDocument();
    });

    it("should not show edit button for assistant messages", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="assistant" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.queryByTestId("action-edit")).not.toBeInTheDocument();
    });

    it("should call onEdit with messageId when edit is clicked", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="user" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-edit"));

      expect(defaultProps.onEdit).toHaveBeenCalledWith("msg-001");
    });

    it("should close menu after edit action", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="user" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-edit"));

      expect(
        screen.queryByTestId("message-actions-menu"),
      ).not.toBeInTheDocument();
    });
  });

  describe("regenerate action", () => {
    it("should show regenerate button for assistant messages", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="assistant" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-regenerate")).toBeInTheDocument();
    });

    it("should not show regenerate button for user messages", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="user" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.queryByTestId("action-regenerate")).not.toBeInTheDocument();
    });

    it("should call onRegenerate with messageId when regenerate is clicked", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="assistant" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-regenerate"));

      expect(defaultProps.onRegenerate).toHaveBeenCalledWith("msg-001");
    });

    it("should close menu after regenerate action", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="assistant" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-regenerate"));

      expect(
        screen.queryByTestId("message-actions-menu"),
      ).not.toBeInTheDocument();
    });

    it("should disable regenerate when isRegenerating is true", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} role="assistant" isRegenerating />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));

      const regenerateButton = screen.getByTestId("action-regenerate");
      expect(regenerateButton).toBeDisabled();
    });
  });

  describe("delete action", () => {
    it("should show delete button for all message roles", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-delete")).toBeInTheDocument();
    });

    it("should show confirmation dialog when delete is clicked", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-delete"));

      expect(screen.getByTestId("delete-confirmation")).toBeInTheDocument();
    });

    it("should call onDelete with messageId when confirmed", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-delete"));
      fireEvent.click(screen.getByTestId("confirm-delete"));

      expect(defaultProps.onDelete).toHaveBeenCalledWith("msg-001");
    });

    it("should close confirmation dialog when cancelled", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-delete"));
      fireEvent.click(screen.getByTestId("cancel-delete"));

      expect(
        screen.queryByTestId("delete-confirmation"),
      ).not.toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have aria-label on trigger button", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      const trigger = screen.getByTestId("message-actions-trigger");
      expect(trigger).toHaveAttribute("aria-label", "Message actions");
    });

    it("should have aria-expanded attribute", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      const trigger = screen.getByTestId("message-actions-trigger");

      expect(trigger).toHaveAttribute("aria-expanded", "false");
      fireEvent.click(trigger);
      expect(trigger).toHaveAttribute("aria-expanded", "true");
    });

    it("should close menu on Escape key", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("message-actions-menu")).toBeInTheDocument();

      fireEvent.keyDown(document, { key: "Escape" });
      expect(
        screen.queryByTestId("message-actions-menu"),
      ).not.toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("should apply custom className", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} className="custom-class" />
        </TestProvider>,
      );
      const container = screen.getByTestId("message-actions-container");
      expect(container).toHaveClass("custom-class");
    });
  });

  // ===========================================================================
  // Enhanced Actions (Sprint 2.5)
  // ===========================================================================

  describe("copy code blocks", () => {
    const contentWithCode = `Here is some code:
\`\`\`javascript
function hello() {
  console.log("Hello World");
}
\`\`\`
And some more text.`;

    it("should show copy code button when message has code blocks", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} content={contentWithCode} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-copy-code")).toBeInTheDocument();
    });

    it("should not show copy code button when no code blocks", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} content="No code here" />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.queryByTestId("action-copy-code")).not.toBeInTheDocument();
    });

    it("should copy only code blocks when copy code is clicked", async () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} content={contentWithCode} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-copy-code"));

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith(
          expect.stringContaining("function hello()"),
        );
      });
    });
  });

  describe("feedback actions", () => {
    it("should show thumbs up button", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onFeedback={() => {}} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-thumbs-up")).toBeInTheDocument();
    });

    it("should show thumbs down button", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onFeedback={() => {}} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-thumbs-down")).toBeInTheDocument();
    });

    it("should call onFeedback with positive when thumbs up clicked", () => {
      const onFeedback = vi.fn();
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onFeedback={onFeedback} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-thumbs-up"));

      expect(onFeedback).toHaveBeenCalledWith("msg-001", "positive");
    });

    it("should call onFeedback with negative when thumbs down clicked", () => {
      const onFeedback = vi.fn();
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onFeedback={onFeedback} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-thumbs-down"));

      expect(onFeedback).toHaveBeenCalledWith("msg-001", "negative");
    });

    it("should highlight active feedback state", () => {
      render(
        <TestProvider>
          <MessageActions
            {...defaultProps}
            onFeedback={() => {}}
            feedbackState="positive"
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));

      const thumbsUp = screen.getByTestId("action-thumbs-up");
      expect(thumbsUp).toHaveAttribute("data-active", "true");
    });
  });

  describe("bookmark action", () => {
    it("should show bookmark button when onBookmark is provided", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onBookmark={() => {}} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-bookmark")).toBeInTheDocument();
    });

    it("should call onBookmark when bookmark is clicked", () => {
      const onBookmark = vi.fn();
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onBookmark={onBookmark} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-bookmark"));

      expect(onBookmark).toHaveBeenCalledWith("msg-001");
    });

    it("should show filled bookmark icon when bookmarked", () => {
      render(
        <TestProvider>
          <MessageActions
            {...defaultProps}
            onBookmark={() => {}}
            isBookmarked
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));

      const bookmark = screen.getByTestId("action-bookmark");
      expect(bookmark).toHaveAttribute("data-bookmarked", "true");
    });
  });

  describe("share action", () => {
    it("should show share button when onShare is provided", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onShare={() => {}} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-share")).toBeInTheDocument();
    });

    it("should call onShare when share is clicked", () => {
      const onShare = vi.fn();
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onShare={onShare} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-share"));

      expect(onShare).toHaveBeenCalledWith("msg-001");
    });
  });

  describe("branch action", () => {
    it("should show branch button when onBranch is provided", () => {
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onBranch={() => {}} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-branch")).toBeInTheDocument();
    });

    it("should call onBranch when branch is clicked", () => {
      const onBranch = vi.fn();
      render(
        <TestProvider>
          <MessageActions {...defaultProps} onBranch={onBranch} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-branch"));

      expect(onBranch).toHaveBeenCalledWith("msg-001");
    });
  });
});
