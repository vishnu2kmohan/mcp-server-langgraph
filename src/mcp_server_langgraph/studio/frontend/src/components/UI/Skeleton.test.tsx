/**
 * Skeleton Component Tests
 *
 * TDD tests for the Skeleton loading placeholder component.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Skeleton, SkeletonCard, SkeletonText, SkeletonList } from "./Skeleton";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Skeleton", () => {
  describe("Base Skeleton", () => {
    it("should render with default styles", () => {
      render(
        <TestProvider>
          <Skeleton data-testid="skeleton" />
        </TestProvider>,
      );
      const skeleton = screen.getByTestId("skeleton");
      expect(skeleton).toBeInTheDocument();
      expect(skeleton).toHaveClass("animate-pulse");
      expect(skeleton).toHaveClass("bg-neutral-3");
    });

    it("should apply custom className", () => {
      render(
        <TestProvider>
          <Skeleton className="w-full h-10" data-testid="skeleton" />
        </TestProvider>,
      );
      const skeleton = screen.getByTestId("skeleton");
      expect(skeleton).toHaveClass("w-full");
      expect(skeleton).toHaveClass("h-10");
    });

    it("should apply rounded styles", () => {
      render(
        <TestProvider>
          <Skeleton rounded data-testid="skeleton" />
        </TestProvider>,
      );
      const skeleton = screen.getByTestId("skeleton");
      expect(skeleton).toHaveClass("rounded-full");
    });
  });

  describe("SkeletonCard", () => {
    it("should render a card skeleton", () => {
      render(
        <TestProvider>
          <SkeletonCard data-testid="skeleton-card" />
        </TestProvider>,
      );
      const card = screen.getByTestId("skeleton-card");
      expect(card).toBeInTheDocument();
      expect(card).toHaveClass("rounded-lg");
    });

    it("should render with header and content sections", () => {
      render(
        <TestProvider>
          <SkeletonCard data-testid="skeleton-card" />
        </TestProvider>,
      );
      const card = screen.getByTestId("skeleton-card");
      // Should have multiple skeleton children
      expect(card.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
    });
  });

  describe("SkeletonText", () => {
    it("should render text skeleton with default lines", () => {
      render(
        <TestProvider>
          <SkeletonText data-testid="skeleton-text" />
        </TestProvider>,
      );
      const container = screen.getByTestId("skeleton-text");
      // Default 3 lines
      expect(container.querySelectorAll(".animate-pulse").length).toBe(3);
    });

    it("should render specified number of lines", () => {
      render(
        <TestProvider>
          <SkeletonText lines={5} data-testid="skeleton-text" />
        </TestProvider>,
      );
      const container = screen.getByTestId("skeleton-text");
      expect(container.querySelectorAll(".animate-pulse").length).toBe(5);
    });

    it("should have varying widths for natural appearance", () => {
      render(
        <TestProvider>
          <SkeletonText lines={3} data-testid="skeleton-text" />
        </TestProvider>,
      );
      const container = screen.getByTestId("skeleton-text");
      const skeletons = container.querySelectorAll(".animate-pulse");
      // Last line should be shorter
      expect(skeletons[2]).toHaveClass("w-3/4");
    });
  });

  describe("SkeletonList", () => {
    it("should render list skeleton with default items", () => {
      render(
        <TestProvider>
          <SkeletonList data-testid="skeleton-list" />
        </TestProvider>,
      );
      const container = screen.getByTestId("skeleton-list");
      // Default 3 items
      expect(container.children.length).toBe(3);
    });

    it("should render specified number of items", () => {
      render(
        <TestProvider>
          <SkeletonList items={5} data-testid="skeleton-list" />
        </TestProvider>,
      );
      const container = screen.getByTestId("skeleton-list");
      expect(container.children.length).toBe(5);
    });
  });

  describe("CVA integration", () => {
    it("exports skeletonVariants function for external use", async () => {
      const { skeletonVariants } = await import("./Skeleton");
      expect(typeof skeletonVariants).toBe("function");
    });
  });

  describe("Accessibility", () => {
    it("should have aria-hidden on base Skeleton for screen readers", () => {
      render(
        <TestProvider>
          <Skeleton data-testid="skeleton" />
        </TestProvider>,
      );
      const skeleton = screen.getByTestId("skeleton");
      expect(skeleton).toHaveAttribute("aria-hidden", "true");
    });

    it("should have aria-hidden on SkeletonCard for screen readers", () => {
      render(
        <TestProvider>
          <SkeletonCard data-testid="skeleton-card" />
        </TestProvider>,
      );
      const card = screen.getByTestId("skeleton-card");
      expect(card).toHaveAttribute("aria-hidden", "true");
    });

    it("should have aria-hidden on SkeletonText for screen readers", () => {
      render(
        <TestProvider>
          <SkeletonText data-testid="skeleton-text" />
        </TestProvider>,
      );
      const container = screen.getByTestId("skeleton-text");
      expect(container).toHaveAttribute("aria-hidden", "true");
    });

    it("should have aria-hidden on SkeletonList for screen readers", () => {
      render(
        <TestProvider>
          <SkeletonList data-testid="skeleton-list" />
        </TestProvider>,
      );
      const container = screen.getByTestId("skeleton-list");
      expect(container).toHaveAttribute("aria-hidden", "true");
    });

    it("should allow overriding aria-hidden when needed", () => {
      render(
        <TestProvider>
          <Skeleton data-testid="skeleton" aria-hidden={false} />
        </TestProvider>,
      );
      const skeleton = screen.getByTestId("skeleton");
      // User-provided value should override default
      expect(skeleton).toHaveAttribute("aria-hidden", "false");
    });
  });
});
