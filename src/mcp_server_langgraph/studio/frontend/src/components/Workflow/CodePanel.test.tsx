/**
 * CodePanel Tests
 *
 * Tests for the code preview panel component.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CodePanel } from "./CodePanel";

describe("CodePanel", () => {
  const defaultProps = {
    code: "def my_workflow():\n    pass",
    isOpen: true,
    onClose: vi.fn(),
    onCopy: vi.fn(),
    isDarkMode: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the code panel when open", () => {
      render(<CodePanel {...defaultProps} />);

      expect(screen.getByText("Generated Code")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(<CodePanel {...defaultProps} isOpen={false} />);

      expect(screen.queryByText("Generated Code")).not.toBeInTheDocument();
    });

    it("should display the code content", () => {
      render(<CodePanel {...defaultProps} />);

      expect(screen.getByText(/def my_workflow/)).toBeInTheDocument();
    });

    it("should render close button", () => {
      render(<CodePanel {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /close/i }),
      ).toBeInTheDocument();
    });

    it("should render copy button", () => {
      render(<CodePanel {...defaultProps} />);

      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onClose when close button is clicked", () => {
      render(<CodePanel {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /close/i }));
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it("should call onCopy when copy button is clicked", () => {
      render(<CodePanel {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /copy/i }));
      expect(defaultProps.onCopy).toHaveBeenCalled();
    });
  });

  describe("Empty State", () => {
    it("should show placeholder when code is empty", () => {
      render(<CodePanel {...defaultProps} code="" />);

      expect(screen.getByText(/no code generated/i)).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("should apply dark mode styles", () => {
      const { container } = render(
        <CodePanel {...defaultProps} isDarkMode={true} />,
      );

      const panel = container.querySelector('[data-testid="code-panel"]');
      expect(panel).toHaveClass("bg-gray-800");
    });

    it("should apply light mode styles", () => {
      const { container } = render(
        <CodePanel {...defaultProps} isDarkMode={false} />,
      );

      const panel = container.querySelector('[data-testid="code-panel"]');
      expect(panel).toHaveClass("bg-white");
    });
  });
});
