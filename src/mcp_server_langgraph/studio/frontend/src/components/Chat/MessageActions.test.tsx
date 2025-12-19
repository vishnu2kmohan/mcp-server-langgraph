/**
 * MessageActions Component Tests
 *
 * Tests for the message actions dropdown menu that provides
 * Copy, Edit, Regenerate, and Delete functionality.
 *
 * TDD RED Phase: Write failing tests first.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MessageActions, type MessageActionsProps } from "./MessageActions";

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

  describe("rendering", () => {
    it("should render the actions trigger button", () => {
      render(<MessageActions {...defaultProps} />);
      expect(screen.getByTestId("message-actions-trigger")).toBeInTheDocument();
    });

    it("should not show menu initially", () => {
      render(<MessageActions {...defaultProps} />);
      expect(
        screen.queryByTestId("message-actions-menu"),
      ).not.toBeInTheDocument();
    });

    it("should show menu when trigger is clicked", () => {
      render(<MessageActions {...defaultProps} />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("message-actions-menu")).toBeInTheDocument();
    });

    it("should close menu when clicking outside", async () => {
      render(
        <div>
          <MessageActions {...defaultProps} />
          <div data-testid="outside">Outside</div>
        </div>,
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
      render(<MessageActions {...defaultProps} />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-copy")).toBeInTheDocument();
    });

    it("should copy content to clipboard when copy is clicked", async () => {
      render(<MessageActions {...defaultProps} />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-copy"));

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith(
          "This is a test message",
        );
      });
    });

    it("should show copied confirmation after copying", async () => {
      render(<MessageActions {...defaultProps} />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-copy"));

      await waitFor(() => {
        expect(screen.getByTestId("copy-success")).toBeInTheDocument();
      });
    });
  });

  describe("edit action", () => {
    it("should show edit button for user messages", () => {
      render(<MessageActions {...defaultProps} role="user" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-edit")).toBeInTheDocument();
    });

    it("should not show edit button for assistant messages", () => {
      render(<MessageActions {...defaultProps} role="assistant" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.queryByTestId("action-edit")).not.toBeInTheDocument();
    });

    it("should call onEdit with messageId when edit is clicked", () => {
      render(<MessageActions {...defaultProps} role="user" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-edit"));

      expect(defaultProps.onEdit).toHaveBeenCalledWith("msg-001");
    });

    it("should close menu after edit action", () => {
      render(<MessageActions {...defaultProps} role="user" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-edit"));

      expect(
        screen.queryByTestId("message-actions-menu"),
      ).not.toBeInTheDocument();
    });
  });

  describe("regenerate action", () => {
    it("should show regenerate button for assistant messages", () => {
      render(<MessageActions {...defaultProps} role="assistant" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-regenerate")).toBeInTheDocument();
    });

    it("should not show regenerate button for user messages", () => {
      render(<MessageActions {...defaultProps} role="user" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.queryByTestId("action-regenerate")).not.toBeInTheDocument();
    });

    it("should call onRegenerate with messageId when regenerate is clicked", () => {
      render(<MessageActions {...defaultProps} role="assistant" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-regenerate"));

      expect(defaultProps.onRegenerate).toHaveBeenCalledWith("msg-001");
    });

    it("should close menu after regenerate action", () => {
      render(<MessageActions {...defaultProps} role="assistant" />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-regenerate"));

      expect(
        screen.queryByTestId("message-actions-menu"),
      ).not.toBeInTheDocument();
    });

    it("should disable regenerate when isRegenerating is true", () => {
      render(
        <MessageActions {...defaultProps} role="assistant" isRegenerating />,
      );
      fireEvent.click(screen.getByTestId("message-actions-trigger"));

      const regenerateButton = screen.getByTestId("action-regenerate");
      expect(regenerateButton).toBeDisabled();
    });
  });

  describe("delete action", () => {
    it("should show delete button for all message roles", () => {
      render(<MessageActions {...defaultProps} />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      expect(screen.getByTestId("action-delete")).toBeInTheDocument();
    });

    it("should show confirmation dialog when delete is clicked", () => {
      render(<MessageActions {...defaultProps} />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-delete"));

      expect(screen.getByTestId("delete-confirmation")).toBeInTheDocument();
    });

    it("should call onDelete with messageId when confirmed", () => {
      render(<MessageActions {...defaultProps} />);
      fireEvent.click(screen.getByTestId("message-actions-trigger"));
      fireEvent.click(screen.getByTestId("action-delete"));
      fireEvent.click(screen.getByTestId("confirm-delete"));

      expect(defaultProps.onDelete).toHaveBeenCalledWith("msg-001");
    });

    it("should close confirmation dialog when cancelled", () => {
      render(<MessageActions {...defaultProps} />);
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
      render(<MessageActions {...defaultProps} />);
      const trigger = screen.getByTestId("message-actions-trigger");
      expect(trigger).toHaveAttribute("aria-label", "Message actions");
    });

    it("should have aria-expanded attribute", () => {
      render(<MessageActions {...defaultProps} />);
      const trigger = screen.getByTestId("message-actions-trigger");

      expect(trigger).toHaveAttribute("aria-expanded", "false");
      fireEvent.click(trigger);
      expect(trigger).toHaveAttribute("aria-expanded", "true");
    });

    it("should close menu on Escape key", () => {
      render(<MessageActions {...defaultProps} />);
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
      render(<MessageActions {...defaultProps} className="custom-class" />);
      const container = screen.getByTestId("message-actions-container");
      expect(container).toHaveClass("custom-class");
    });
  });
});
