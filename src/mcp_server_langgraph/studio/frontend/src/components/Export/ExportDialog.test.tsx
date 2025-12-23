/**
 * ExportDialog Tests
 *
 * TDD tests for the Export Dialog component.
 * Tests cover:
 * - Format selection
 * - Export options
 * - Copy and download actions
 * - WCAG 2.1 AA accessibility compliance
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ExportDialog, ExportDialogProps } from "./ExportDialog";

expect.extend(toHaveNoViolations);

const mockMessages = [
  {
    id: "1",
    role: "user" as const,
    content: "Hello",
    timestamp: "2024-01-01T10:00:00Z",
  },
  {
    id: "2",
    role: "assistant" as const,
    content: "Hi there!",
    timestamp: "2024-01-01T10:00:10Z",
  },
];

const defaultProps: ExportDialogProps = {
  isOpen: true,
  onClose: vi.fn(),
  messages: mockMessages,
};

describe("ExportDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render when open", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(screen.getByTestId("export-dialog")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(<ExportDialog {...defaultProps} isOpen={false} />);

      expect(screen.queryByTestId("export-dialog")).not.toBeInTheDocument();
    });

    it("should render format options", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(screen.getByText(/markdown/i)).toBeInTheDocument();
      expect(screen.getByText(/json/i)).toBeInTheDocument();
    });

    it("should render export options", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(screen.getByText(/include timestamps/i)).toBeInTheDocument();
      expect(screen.getByText(/include token counts/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Format Selection Tests
  // ===========================================================================

  describe("format selection", () => {
    it("should default to markdown format", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(screen.getByTestId("format-markdown")).toHaveAttribute(
        "aria-checked",
        "true",
      );
    });

    it("should allow selecting JSON format", async () => {
      const user = userEvent.setup();
      render(<ExportDialog {...defaultProps} />);

      await user.click(screen.getByTestId("format-json"));

      expect(screen.getByTestId("format-json")).toHaveAttribute(
        "aria-checked",
        "true",
      );
    });
  });

  // ===========================================================================
  // Export Options Tests
  // ===========================================================================

  describe("export options", () => {
    it("should toggle timestamp option", async () => {
      const user = userEvent.setup();
      render(<ExportDialog {...defaultProps} />);

      const toggle = screen.getByTestId("option-timestamps");
      await user.click(toggle);

      expect(toggle).toHaveAttribute("aria-checked", "true");
    });

    it("should toggle token count option", async () => {
      const user = userEvent.setup();
      render(<ExportDialog {...defaultProps} />);

      const toggle = screen.getByTestId("option-tokens");
      await user.click(toggle);

      expect(toggle).toHaveAttribute("aria-checked", "true");
    });
  });

  // ===========================================================================
  // Action Tests
  // ===========================================================================

  describe("actions", () => {
    it("should render copy button", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });

    it("should render download button", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /download/i }),
      ).toBeInTheDocument();
    });

    it("should close dialog on cancel", async () => {
      const user = userEvent.setup();
      render(<ExportDialog {...defaultProps} />);

      await user.click(screen.getByRole("button", { name: /cancel/i }));

      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Preview Tests
  // ===========================================================================

  describe("preview", () => {
    it("should show export preview", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(screen.getByTestId("export-preview")).toBeInTheDocument();
    });

    it("should update preview when format changes", async () => {
      const user = userEvent.setup();
      render(<ExportDialog {...defaultProps} />);

      // Default is markdown
      expect(screen.getByTestId("export-preview")).toHaveTextContent("Hello");

      // Switch to JSON
      await user.click(screen.getByTestId("format-json"));

      expect(screen.getByTestId("export-preview")).toHaveTextContent("{");
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<ExportDialog {...defaultProps} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper dialog role", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have proper heading", () => {
      render(<ExportDialog {...defaultProps} />);

      expect(
        screen.getByRole("heading", { name: /export/i }),
      ).toBeInTheDocument();
    });

    it("should be keyboard navigable", async () => {
      const user = userEvent.setup();
      render(<ExportDialog {...defaultProps} />);

      await user.tab();

      // First focusable element should have focus
      expect(document.activeElement).not.toBe(document.body);
    });

    it("should close on Escape key", async () => {
      const user = userEvent.setup();
      render(<ExportDialog {...defaultProps} />);

      await user.keyboard("{Escape}");

      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(<ExportDialog {...defaultProps} className="custom-class" />);

      expect(screen.getByTestId("export-dialog")).toHaveClass("custom-class");
    });
  });
});
