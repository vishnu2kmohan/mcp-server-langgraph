/**
 * CursorPagination Tests
 *
 * TDD tests for cursor-based pagination component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CursorPagination } from "./CursorPagination";

describe("CursorPagination", () => {
  describe("Component Structure", () => {
    it("should render pagination container", () => {
      render(
        <CursorPagination
          hasNextPage={false}
          hasPreviousPage={false}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
        />,
      );
      expect(screen.getByTestId("cursor-pagination")).toBeInTheDocument();
    });

    it("should render previous button", () => {
      render(
        <CursorPagination
          hasNextPage={false}
          hasPreviousPage={false}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("button", { name: /previous/i }),
      ).toBeInTheDocument();
    });

    it("should render next button", () => {
      render(
        <CursorPagination
          hasNextPage={false}
          hasPreviousPage={false}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
        />,
      );
      expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
    });
  });

  describe("Button States", () => {
    it("should disable previous button when no previous page", () => {
      render(
        <CursorPagination
          hasNextPage={true}
          hasPreviousPage={false}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
        />,
      );
      expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    });

    it("should enable previous button when has previous page", () => {
      render(
        <CursorPagination
          hasNextPage={false}
          hasPreviousPage={true}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
        />,
      );
      expect(screen.getByRole("button", { name: /previous/i })).toBeEnabled();
    });

    it("should disable next button when no next page", () => {
      render(
        <CursorPagination
          hasNextPage={false}
          hasPreviousPage={true}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
        />,
      );
      expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    });

    it("should enable next button when has next page", () => {
      render(
        <CursorPagination
          hasNextPage={true}
          hasPreviousPage={false}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
        />,
      );
      expect(screen.getByRole("button", { name: /next/i })).toBeEnabled();
    });

    it("should disable both buttons when loading", () => {
      render(
        <CursorPagination
          hasNextPage={true}
          hasPreviousPage={true}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
          isLoading={true}
        />,
      );
      expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    });
  });

  describe("Button Clicks", () => {
    it("should call onPreviousPage when previous button clicked", () => {
      const onPreviousPage = vi.fn();
      render(
        <CursorPagination
          hasNextPage={false}
          hasPreviousPage={true}
          onNextPage={vi.fn()}
          onPreviousPage={onPreviousPage}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /previous/i }));
      expect(onPreviousPage).toHaveBeenCalledTimes(1);
    });

    it("should call onNextPage when next button clicked", () => {
      const onNextPage = vi.fn();
      render(
        <CursorPagination
          hasNextPage={true}
          hasPreviousPage={false}
          onNextPage={onNextPage}
          onPreviousPage={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(onNextPage).toHaveBeenCalledTimes(1);
    });

    it("should not call onPreviousPage when button is disabled", () => {
      const onPreviousPage = vi.fn();
      render(
        <CursorPagination
          hasNextPage={true}
          hasPreviousPage={false}
          onNextPage={vi.fn()}
          onPreviousPage={onPreviousPage}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: /previous/i }));
      expect(onPreviousPage).not.toHaveBeenCalled();
    });
  });

  describe("Optional Props", () => {
    it("should show loading indicator when loading", () => {
      render(
        <CursorPagination
          hasNextPage={true}
          hasPreviousPage={true}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
          isLoading={true}
        />,
      );
      expect(screen.getByTestId("pagination-loading")).toBeInTheDocument();
    });

    it("should show item count when provided", () => {
      render(
        <CursorPagination
          hasNextPage={true}
          hasPreviousPage={false}
          onNextPage={vi.fn()}
          onPreviousPage={vi.fn()}
          itemCount={25}
          totalCount={100}
        />,
      );
      expect(screen.getByText(/25 of 100/)).toBeInTheDocument();
    });
  });
});
