/**
 * Pagination Component Tests
 *
 * TDD tests for cursor-based and page-based pagination.
 * Features:
 * - Cursor-based navigation (prev/next)
 * - Page-based navigation (page numbers)
 * - Items per page selection
 * - Disabled states
 * - Accessibility
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { CursorPagination, PagePagination } from "./Pagination";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CursorPagination", () => {
  describe("Rendering", () => {
    it("should render prev and next buttons", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={false}
            onNext={vi.fn()}
            onPrev={vi.fn()}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /previous/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
    });

    it("should disable prev button when hasPrev is false", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={false}
            onNext={vi.fn()}
            onPrev={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    });

    it("should disable next button when hasNext is false", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={false}
            hasPrev={true}
            onNext={vi.fn()}
            onPrev={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    });

    it("should show loading state", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={true}
            onNext={vi.fn()}
            onPrev={vi.fn()}
            isLoading={true}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    });

    it("should display item count when provided", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={false}
            onNext={vi.fn()}
            onPrev={vi.fn()}
            itemCount={25}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/25 items/i)).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onNext when next button is clicked", () => {
      const onNext = vi.fn();
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={false}
            onNext={onNext}
            onPrev={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(onNext).toHaveBeenCalledTimes(1);
    });

    it("should call onPrev when prev button is clicked", () => {
      const onPrev = vi.fn();
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={true}
            onNext={vi.fn()}
            onPrev={onPrev}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /previous/i }));
      expect(onPrev).toHaveBeenCalledTimes(1);
    });

    it("should not call onNext when button is disabled", () => {
      const onNext = vi.fn();
      render(
        <TestProvider>
          <CursorPagination
            hasNext={false}
            hasPrev={false}
            onNext={onNext}
            onPrev={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(onNext).not.toHaveBeenCalled();
    });
  });

  describe("Limit Selector", () => {
    it("should render limit selector when showLimitSelector is true", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={false}
            onNext={vi.fn()}
            onPrev={vi.fn()}
            showLimitSelector={true}
            limit={20}
            onLimitChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("should call onLimitChange when limit is changed", () => {
      const onLimitChange = vi.fn();
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={false}
            onNext={vi.fn()}
            onPrev={vi.fn()}
            showLimitSelector={true}
            limit={20}
            onLimitChange={onLimitChange}
          />
        </TestProvider>,
      );

      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: "50" },
      });
      expect(onLimitChange).toHaveBeenCalledWith(50);
    });

    it("should display current limit value", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={false}
            onNext={vi.fn()}
            onPrev={vi.fn()}
            showLimitSelector={true}
            limit={50}
            onLimitChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("combobox")).toHaveValue("50");
    });
  });

  describe("Accessibility", () => {
    it("should have proper aria-labels", () => {
      render(
        <TestProvider>
          <CursorPagination
            hasNext={true}
            hasPrev={true}
            onNext={vi.fn()}
            onPrev={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("navigation")).toHaveAttribute(
        "aria-label",
        "Pagination",
      );
    });
  });
});

describe("PagePagination", () => {
  describe("Rendering", () => {
    it("should render page numbers", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={1}
            totalPages={5}
            onPageChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("should highlight current page", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={2}
            totalPages={5}
            onPageChange={vi.fn()}
          />
        </TestProvider>,
      );

      const currentPageButton = screen.getByRole("button", { name: /page 2/i });
      expect(currentPageButton).toHaveAttribute("aria-current", "page");
    });

    it("should show ellipsis for many pages", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={5}
            totalPages={10}
            onPageChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getAllByText("...").length).toBeGreaterThan(0);
    });

    it("should show total items when provided", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={1}
            totalPages={5}
            totalItems={100}
            perPage={20}
            onPageChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/100 items/i)).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onPageChange when page is clicked", () => {
      const onPageChange = vi.fn();
      render(
        <TestProvider>
          <PagePagination
            currentPage={1}
            totalPages={5}
            onPageChange={onPageChange}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /page 3/i }));
      expect(onPageChange).toHaveBeenCalledWith(3);
    });

    it("should call onPageChange with previous page when prev clicked", () => {
      const onPageChange = vi.fn();
      render(
        <TestProvider>
          <PagePagination
            currentPage={3}
            totalPages={5}
            onPageChange={onPageChange}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /previous/i }));
      expect(onPageChange).toHaveBeenCalledWith(2);
    });

    it("should call onPageChange with next page when next clicked", () => {
      const onPageChange = vi.fn();
      render(
        <TestProvider>
          <PagePagination
            currentPage={3}
            totalPages={5}
            onPageChange={onPageChange}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(onPageChange).toHaveBeenCalledWith(4);
    });

    it("should disable prev on first page", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={1}
            totalPages={5}
            onPageChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    });

    it("should disable next on last page", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={5}
            totalPages={5}
            onPageChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    });
  });

  describe("Per Page Selector", () => {
    it("should render per page selector when provided", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={1}
            totalPages={5}
            onPageChange={vi.fn()}
            perPage={20}
            onPerPageChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("should call onPerPageChange when selection changes", () => {
      const onPerPageChange = vi.fn();
      render(
        <TestProvider>
          <PagePagination
            currentPage={1}
            totalPages={5}
            onPageChange={vi.fn()}
            perPage={20}
            onPerPageChange={onPerPageChange}
          />
        </TestProvider>,
      );

      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: "50" },
      });
      expect(onPerPageChange).toHaveBeenCalledWith(50);
    });
  });

  describe("Loading State", () => {
    it("should disable all buttons when loading", () => {
      render(
        <TestProvider>
          <PagePagination
            currentPage={2}
            totalPages={5}
            onPageChange={vi.fn()}
            isLoading={true}
          />
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });
});
