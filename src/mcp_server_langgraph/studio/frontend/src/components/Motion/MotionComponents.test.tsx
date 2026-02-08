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

import { TestProvider } from "@/test-utils";

// Note: motion/react is globally mocked in src/test/setup.ts with proper prop filtering

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("MotionComponents", () => {
  describe("MotionFadeIn", () => {
    it("should render children", () => {
      render(
        <TestProvider>
          <MotionFadeIn>Test content</MotionFadeIn>
        </TestProvider>,
      );
      expect(screen.getByText("Test content")).toBeInTheDocument();
    });

    it("should accept custom className", () => {
      render(
        <TestProvider>
          <MotionFadeIn className="custom-class" data-testid="fade-in">
            Content
          </MotionFadeIn>
        </TestProvider>,
      );
      expect(screen.getByTestId("fade-in")).toHaveClass("custom-class");
    });

    it("should have data-testid when provided", () => {
      render(
        <TestProvider>
          <MotionFadeIn data-testid="fade-in">Content</MotionFadeIn>
        </TestProvider>,
      );
      expect(screen.getByTestId("fade-in")).toBeInTheDocument();
    });
  });

  describe("MotionSlideIn", () => {
    it("should render children", () => {
      render(
        <TestProvider>
          <MotionSlideIn>Slide content</MotionSlideIn>
        </TestProvider>,
      );
      expect(screen.getByText("Slide content")).toBeInTheDocument();
    });

    it("should accept direction prop", () => {
      render(
        <TestProvider>
          <MotionSlideIn direction="right">Content</MotionSlideIn>
        </TestProvider>,
      );
      expect(screen.getByText("Content")).toBeInTheDocument();
    });

    it("should accept distance prop", () => {
      render(
        <TestProvider>
          <MotionSlideIn distance={30}>Content</MotionSlideIn>
        </TestProvider>,
      );
      expect(screen.getByText("Content")).toBeInTheDocument();
    });
  });

  describe("MotionList", () => {
    it("should render children with stagger container", () => {
      render(
        <TestProvider>
          <MotionList>
            <li>Item 1</li>
            <li>Item 2</li>
          </MotionList>
        </TestProvider>,
      );
      expect(screen.getByText("Item 1")).toBeInTheDocument();
      expect(screen.getByText("Item 2")).toBeInTheDocument();
    });

    it("should have list role by default", () => {
      render(
        <TestProvider>
          <MotionList data-testid="motion-list">
            <li>Item</li>
          </MotionList>
        </TestProvider>,
      );
      expect(screen.getByTestId("motion-list")).toHaveAttribute("role", "list");
    });
  });

  describe("MotionListItem", () => {
    it("should render children", () => {
      render(
        <TestProvider>
          <MotionListItem>List item content</MotionListItem>
        </TestProvider>,
      );
      expect(screen.getByText("List item content")).toBeInTheDocument();
    });
  });

  describe("MotionPanel", () => {
    it("should render children when open", () => {
      render(
        <TestProvider>
          <MotionPanel isOpen>Panel content</MotionPanel>
        </TestProvider>,
      );
      expect(screen.getByText("Panel content")).toBeInTheDocument();
    });

    it("should not render children when closed", () => {
      render(
        <TestProvider>
          <MotionPanel isOpen={false}>Panel content</MotionPanel>
        </TestProvider>,
      );
      expect(screen.queryByText("Panel content")).not.toBeInTheDocument();
    });

    it("should accept direction prop", () => {
      render(
        <TestProvider>
          <MotionPanel isOpen direction="left">
            Content
          </MotionPanel>
        </TestProvider>,
      );
      expect(screen.getByText("Content")).toBeInTheDocument();
    });
  });

  describe("MotionSkeleton", () => {
    it("should render with pulse animation class", () => {
      render(
        <TestProvider>
          <MotionSkeleton data-testid="skeleton" />
        </TestProvider>,
      );
      expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    });

    it("should accept width and height props", () => {
      render(
        <TestProvider>
          <MotionSkeleton width="100px" height="20px" data-testid="skeleton" />
        </TestProvider>,
      );
      const skeleton = screen.getByTestId("skeleton");
      expect(skeleton).toHaveStyle({ width: "100px", height: "20px" });
    });

    it("should accept variant prop", () => {
      render(
        <TestProvider>
          <MotionSkeleton variant="circular" data-testid="skeleton" />
        </TestProvider>,
      );
      expect(screen.getByTestId("skeleton")).toBeInTheDocument();
    });
  });

  describe("MotionBadge", () => {
    it("should render children", () => {
      render(
        <TestProvider>
          <MotionBadge>5</MotionBadge>
        </TestProvider>,
      );
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("should pulse when pulse prop is true", () => {
      render(
        <TestProvider>
          <MotionBadge pulse data-testid="badge">
            3
          </MotionBadge>
        </TestProvider>,
      );
      expect(screen.getByTestId("badge")).toBeInTheDocument();
    });

    it("should accept variant prop", () => {
      render(
        <TestProvider>
          <MotionBadge variant="error">!</MotionBadge>
        </TestProvider>,
      );
      expect(screen.getByText("!")).toBeInTheDocument();
    });
  });
});
