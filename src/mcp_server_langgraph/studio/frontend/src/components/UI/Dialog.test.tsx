/**
 * Dialog Component Tests
 *
 * TDD tests for the base Dialog component.
 * Tests cover:
 * - Rendering
 * - Open/close behavior
 * - Accessibility
 * - Backdrop click
 * - Close button
 * - Keyboard handling
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Dialog } from "./Dialog";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Dialog", () => {
  describe("Rendering", () => {
    it("should not render when open is false", () => {
      render(
        <TestProvider>
          <Dialog open={false} onClose={vi.fn()} title="Test Dialog">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render when open is true", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test Dialog">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should render title in header", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="My Dialog Title">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.getByText("My Dialog Title")).toBeInTheDocument();
    });

    it("should render children content", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Dialog content here</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.getByText("Dialog content here")).toBeInTheDocument();
    });

    it("should render close button", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
    });
  });

  describe("Close Behavior", () => {
    it("should call onClose when close button is clicked", () => {
      const onClose = vi.fn();
      render(
        <TestProvider>
          <Dialog open={true} onClose={onClose} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: "Close" }));

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("should call onClose when backdrop is clicked", () => {
      const onClose = vi.fn();
      render(
        <TestProvider>
          <Dialog open={true} onClose={onClose} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const backdrop = screen.getByTestId("dialog-backdrop");
      fireEvent.click(backdrop);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("should not close when clicking inside the dialog content", () => {
      const onClose = vi.fn();
      render(
        <TestProvider>
          <Dialog open={true} onClose={onClose} title="Test">
            <div>Click me</div>
          </Dialog>
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Click me"));

      expect(onClose).not.toHaveBeenCalled();
    });

    it("should call onClose when Escape key is pressed", () => {
      const onClose = vi.fn();
      render(
        <TestProvider>
          <Dialog open={true} onClose={onClose} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      fireEvent.keyDown(document, { key: "Escape" });

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("Accessibility", () => {
    it('should have role="dialog"', () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it('should have aria-modal="true"', () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("should have aria-labelledby pointing to title", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Accessible Dialog">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby", "dialog-title");
      expect(screen.getByText("Accessible Dialog")).toHaveAttribute(
        "id",
        "dialog-title",
      );
    });
  });

  describe("Sizes", () => {
    it("should render with default size (md)", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const dialogPanel = screen.getByRole("dialog").querySelector(".max-w-md");
      expect(dialogPanel).toBeInTheDocument();
    });

    it("should render with sm size", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test" size="sm">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const dialogPanel = screen.getByRole("dialog").querySelector(".max-w-sm");
      expect(dialogPanel).toBeInTheDocument();
    });

    it("should render with lg size", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test" size="lg">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const dialogPanel = screen.getByRole("dialog").querySelector(".max-w-lg");
      expect(dialogPanel).toBeInTheDocument();
    });

    it("should render with xl size", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test" size="xl">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const dialogPanel = screen.getByRole("dialog").querySelector(".max-w-xl");
      expect(dialogPanel).toBeInTheDocument();
    });
  });

  describe("Footer", () => {
    it("should render footer when provided", () => {
      render(
        <TestProvider>
          <Dialog
            open={true}
            onClose={vi.fn()}
            title="Test"
            footer={<button>Save</button>}
          >
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    });

    it("should not render footer section when not provided", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      // Footer section should not exist
      expect(screen.queryByTestId("dialog-footer")).not.toBeInTheDocument();
    });
  });

  describe("Custom Styling", () => {
    it("should apply custom className to content", () => {
      render(
        <TestProvider>
          <Dialog
            open={true}
            onClose={vi.fn()}
            title="Test"
            contentClassName="custom-class"
          >
            <div data-testid="content">Content</div>
          </Dialog>
        </TestProvider>,
      );

      const content = screen.getByTestId("dialog-content");
      expect(content).toHaveClass("custom-class");
    });
  });

  describe("CVA integration", () => {
    it("exports dialogVariants function for external use", async () => {
      const { dialogVariants } = await import("./Dialog");
      expect(typeof dialogVariants).toBe("function");
    });
  });

  describe("Accessibility - Touch Targets (WCAG 2.5.8)", () => {
    it("close button meets minimum 24x24px touch target", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const closeButton = screen.getByRole("button", { name: "Close" });
      // Check for h-8 w-8 (32px) or min-h-8 min-w-8 which exceeds 24px minimum
      expect(closeButton.className).toMatch(/min-h-8|h-8/);
      expect(closeButton.className).toMatch(/min-w-8|w-8/);
    });

    it("close button has adequate padding for touch interaction", () => {
      render(
        <TestProvider>
          <Dialog open={true} onClose={vi.fn()} title="Test">
            <div>Content</div>
          </Dialog>
        </TestProvider>,
      );

      const closeButton = screen.getByRole("button", { name: "Close" });
      // Verify the button has padding and rounded styling for touch
      expect(closeButton.className).toContain("rounded");
      expect(closeButton.className).toMatch(/p-1/);
    });
  });
});
