/**
 * BulkActionBar Component Tests
 *
 * TDD tests for the bulk action toolbar component.
 * Features:
 * - Display selected count
 * - Clear selection button
 * - Action buttons (Delete, etc.)
 * - Loading state during operations
 * - Confirmation dialog for destructive actions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { BulkActionBar } from "./BulkActionBar";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("BulkActionBar", () => {
  const defaultProps = {
    selectedCount: 3,
    onClearSelection: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render when items are selected", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("3 selected")).toBeInTheDocument();
    });

    it("should not render when no items are selected", () => {
      const { container } = render(
        <TestProvider>
          <BulkActionBar {...defaultProps} selectedCount={0} />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });

    it("should display singular text for 1 item", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} selectedCount={1} />
        </TestProvider>,
      );

      expect(screen.getByText("1 selected")).toBeInTheDocument();
    });

    it("should have clear selection button", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Clear selection")).toBeInTheDocument();
    });

    it("should have delete button", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /delete/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Clear Selection", () => {
    it("should call onClearSelection when clear button is clicked", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByLabelText("Clear selection"));

      expect(defaultProps.onClearSelection).toHaveBeenCalled();
    });
  });

  describe("Delete Action", () => {
    it("should show confirmation dialog when delete is clicked", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      expect(screen.getByText(/3 items/i)).toBeInTheDocument();
    });

    it("should call onDelete when confirmed", async () => {
      const onDelete = vi.fn().mockResolvedValue(undefined);
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} onDelete={onDelete} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(onDelete).toHaveBeenCalled();
      });
    });

    it("should close dialog when cancelled", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
    });

    it("should not call onDelete when cancelled", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(defaultProps.onDelete).not.toHaveBeenCalled();
    });
  });

  describe("Loading State", () => {
    it("should show loading state during delete operation", async () => {
      const onDelete = vi
        .fn()
        .mockImplementation(
          () => new Promise((resolve) => setTimeout(resolve, 100)),
        );
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} onDelete={onDelete} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      expect(screen.getByText(/deleting/i)).toBeInTheDocument();
    });

    it("should disable buttons during loading", async () => {
      const onDelete = vi
        .fn()
        .mockImplementation(
          () => new Promise((resolve) => setTimeout(resolve, 100)),
        );
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} onDelete={onDelete} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      const confirmButton = screen.getByRole("button", { name: /deleting/i });
      expect(confirmButton).toBeDisabled();
    });
  });

  describe("Custom Actions", () => {
    it("should render custom actions when provided", () => {
      const customActions = [
        {
          label: "Archive",
          onClick: vi.fn(),
          icon: <span data-testid="archive-icon">📦</span>,
        },
      ];

      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} customActions={customActions} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /archive/i }),
      ).toBeInTheDocument();
      expect(screen.getByTestId("archive-icon")).toBeInTheDocument();
    });

    it("should call custom action onClick", () => {
      const customAction = {
        label: "Export",
        onClick: vi.fn(),
      };

      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} customActions={[customAction]} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /export/i }));

      expect(customAction.onClick).toHaveBeenCalled();
    });

    it("should support destructive custom actions with confirmation", async () => {
      const customAction = {
        label: "Permanently Delete",
        onClick: vi.fn().mockResolvedValue(undefined),
        destructive: true,
        confirmMessage: "This cannot be undone!",
      };

      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} customActions={[customAction]} />
        </TestProvider>,
      );

      fireEvent.click(
        screen.getByRole("button", { name: /permanently delete/i }),
      );

      expect(screen.getByText(/this cannot be undone/i)).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(customAction.onClick).toHaveBeenCalled();
      });
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA attributes", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      const bar = screen.getByRole("toolbar");
      expect(bar).toHaveAttribute("aria-label", "Bulk actions");
    });

    it("should announce selection count to screen readers", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("status")).toHaveTextContent("3 selected");
    });
  });

  describe("Styling", () => {
    it("should have fixed position at bottom", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} />
        </TestProvider>,
      );

      const bar = screen.getByRole("toolbar");
      expect(bar).toHaveClass("fixed");
      expect(bar).toHaveClass("bottom-0");
    });

    it("should apply custom className", () => {
      render(
        <TestProvider>
          <BulkActionBar {...defaultProps} className="custom-class" />
        </TestProvider>,
      );

      const bar = screen.getByRole("toolbar");
      expect(bar).toHaveClass("custom-class");
    });
  });
});
