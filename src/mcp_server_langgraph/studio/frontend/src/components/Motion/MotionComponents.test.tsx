/**
 * MotionComponents Tests
 *
 * Tests for the Motion wrapper component library.
 * TDD: Tests written first to define expected behavior.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import {
  MotionFadeIn,
  MotionSlideIn,
  MotionList,
  MotionListItem,
  MotionPanel,
  MotionSkeleton,
  MotionBadge,
} from "./MotionComponents";

// Note: motion/react is globally mocked in src/test/setup.ts with proper prop filtering

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("MotionComponents", () => {
  describe("MotionFadeIn", () => {
    it("should render children", () => {
      render(<MotionFadeIn>Test content</MotionFadeIn>);
      expect(screen.getByText("Test content")).toBeInTheDocument();
    });

    it("should accept custom className", () => {
      render(
        <MotionFadeIn className="custom-class" data-testid="fade-in">
          Content
        </MotionFadeIn>,
      );
      expect(screen.getByTestId("fade-in")).toHaveClass("custom-class");
    });

    it("should have data-testid when provided", () => {
      render(<MotionFadeIn data-testid="fade-in">Content</MotionFadeIn>);
      expect(screen.getByTestId("fade-in")).toBeInTheDocument();
    });
  });

  describe("MotionSlideIn", () => {
    it("should render children", () => {
      render(<MotionSlideIn>Slide content</MotionSlideIn>);
      expect(screen.getByText("Slide content")).toBeInTheDocument();
    });

    it("should accept direction prop", () => {
      render(<MotionSlideIn direction="right">Content</MotionSlideIn>);
      expect(screen.getByText("Content")).toBeInTheDocument();
    });

    it("should accept distance prop", () => {
      render(<MotionSlideIn distance={30}>Content</MotionSlideIn>);
      expect(screen.getByText("Content")).toBeInTheDocument();
    });
  });

  describe("MotionList", () => {
    it("should render children with stagger container", () => {
      render(
        <MotionList>
          <li>Item 1</li>
          <li>Item 2</li>
        </MotionList>,
      );
      expect(screen.getByText("Item 1")).toBeInTheDocument();
      expect(screen.getByText("Item 2")).toBeInTheDocument();
    });

    it("should have list role by default", () => {
      render(
        <MotionList data-testid="motion-list">
          <li>Item</li>
        </MotionList>,
      );
      expect(screen.getByTestId("motion-list")).toHaveAttribute("role", "list");
    });
  });

  describe("MotionListItem", () => {
    it("should render children", () => {
      render(<MotionListItem>List item content</MotionListItem>);
      expect(screen.getByText("List item content")).toBeInTheDocument();
    });
  });

  describe("MotionPanel", () => {
    it("should render children when open", () => {
      render(<MotionPanel isOpen>Panel content</MotionPanel>);
      expect(screen.getByText("Panel content")).toBeInTheDocument();
    });

    it("should not render children when closed", () => {
      render(<MotionPanel isOpen={false}>Panel content</MotionPanel>);
      expect(screen.queryByText("Panel content")).not.toBeInTheDocument();
    });

    it("should accept direction prop", () => {
      render(
        <MotionPanel isOpen direction="left">
          Content
        </MotionPanel>,
      );
      expect(screen.getByText("Content")).toBeInTheDocument();
    });
  });

  describe("MotionSkeleton", () => {
    it("should render with pulse animation class", () => {
      render(<MotionSkeleton data-testid="skeleton" />);
      expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    });

    it("should accept width and height props", () => {
      render(
        <MotionSkeleton width="100px" height="20px" data-testid="skeleton" />,
      );
      const skeleton = screen.getByTestId("skeleton");
      expect(skeleton).toHaveStyle({ width: "100px", height: "20px" });
    });

    it("should accept variant prop", () => {
      render(<MotionSkeleton variant="circular" data-testid="skeleton" />);
      expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    });
  });

  describe("MotionBadge", () => {
    it("should render children", () => {
      render(<MotionBadge>5</MotionBadge>);
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("should pulse when pulse prop is true", () => {
      render(
        <MotionBadge pulse data-testid="badge">
          3
        </MotionBadge>,
      );
      expect(screen.getByTestId("badge")).toBeInTheDocument();
    });

    it("should accept variant prop", () => {
      render(<MotionBadge variant="error">!</MotionBadge>);
      expect(screen.getByText("!")).toBeInTheDocument();
    });
  });
});
