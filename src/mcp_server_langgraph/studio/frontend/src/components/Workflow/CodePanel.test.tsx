/**
 * CodePanel Tests
 *
 * Tests for the code preview panel component.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { CodePanel } from "./CodePanel";

import { TestProvider } from "@/test-utils";

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

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the code panel when open", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Generated Code")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} isOpen={false} />
        </TestProvider>,
      );

      expect(screen.queryByText("Generated Code")).not.toBeInTheDocument();
    });

    it("should display the code content", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/def my_workflow/)).toBeInTheDocument();
    });

    it("should render close button", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /close/i }),
      ).toBeInTheDocument();
    });

    it("should render copy button", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onClose when close button is clicked", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /close/i }));
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it("should call onCopy when copy button is clicked", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /copy/i }));
      expect(defaultProps.onCopy).toHaveBeenCalled();
    });
  });

  describe("Empty State", () => {
    it("should show placeholder when code is empty", () => {
      render(
        <TestProvider>
          <CodePanel {...defaultProps} code="" />
        </TestProvider>,
      );

      expect(screen.getByText(/no code generated/i)).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("should apply dark mode styles", () => {
      const { container } = render(
        <TestProvider>
          <CodePanel {...defaultProps} isDarkMode={true} />
        </TestProvider>,
      );

      const panel = container.querySelector('[data-testid="code-panel"]');
      expect(panel).toHaveClass("bg-neutral-3");
    });

    it("should apply light mode styles", () => {
      const { container } = render(
        <TestProvider>
          <CodePanel {...defaultProps} isDarkMode={false} />
        </TestProvider>,
      );

      const panel = container.querySelector('[data-testid="code-panel"]');
      expect(panel).toHaveClass("bg-neutral-1");
    });
  });
});
