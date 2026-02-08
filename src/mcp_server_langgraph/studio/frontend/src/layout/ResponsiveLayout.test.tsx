/**
 * ResponsiveLayout Tests
 *
 * TDD tests for the ResponsiveLayout wrapper component.
 * Tests breakpoint detection and layout adaptation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import {
  ResponsiveLayout,
  useBreakpoint,
  type Breakpoint,
} from "./ResponsiveLayout";

import { TestProvider } from "@/test-utils";

// Mock matchMedia
function createMatchMedia(width: number) {
  return (query: string) => ({
    matches: (() => {
      if (query.includes("min-width: 1440px")) return width >= 1440;
      if (query.includes("min-width: 1024px")) return width >= 1024;
      if (query.includes("min-width: 768px")) return width >= 768;
      return true;
    })(),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
}

describe("ResponsiveLayout", () => {
  const originalMatchMedia = window.matchMedia;
  const originalInnerWidth = window.innerWidth;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    window.matchMedia = originalMatchMedia;
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: originalInnerWidth,
    });
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      expect(screen.getByTestId("responsive-layout")).toBeInTheDocument();
    });

    it("should render children", () => {
      window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
      render(
        <TestProvider>
          <ResponsiveLayout>
            <div data-testid="child">Child Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      expect(screen.getByTestId("child")).toBeInTheDocument();
    });
  });

  describe("breakpoint detection", () => {
    it("should detect xl breakpoint for width >= 1440px", () => {
      window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 1440,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      expect(screen.getByTestId("responsive-layout")).toHaveAttribute(
        "data-breakpoint",
        "xl",
      );
    });

    it("should detect lg breakpoint for width 1024-1439px", () => {
      window.matchMedia = createMatchMedia(1024) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 1024,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      expect(screen.getByTestId("responsive-layout")).toHaveAttribute(
        "data-breakpoint",
        "lg",
      );
    });

    it("should detect md breakpoint for width 768-1023px", () => {
      window.matchMedia = createMatchMedia(800) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 800,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      expect(screen.getByTestId("responsive-layout")).toHaveAttribute(
        "data-breakpoint",
        "md",
      );
    });

    it("should detect sm breakpoint for width < 768px", () => {
      window.matchMedia = createMatchMedia(600) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 600,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      expect(screen.getByTestId("responsive-layout")).toHaveAttribute(
        "data-breakpoint",
        "sm",
      );
    });
  });

  describe("layout classes", () => {
    it("should apply full layout classes for xl breakpoint", () => {
      window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 1440,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      const layout = screen.getByTestId("responsive-layout");
      expect(layout).toHaveClass("layout-full");
    });

    it("should apply collapsible layout classes for lg breakpoint", () => {
      window.matchMedia = createMatchMedia(1024) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 1024,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      const layout = screen.getByTestId("responsive-layout");
      expect(layout).toHaveClass("layout-collapsible");
    });

    it("should apply toggle layout classes for md breakpoint", () => {
      window.matchMedia = createMatchMedia(800) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 800,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      const layout = screen.getByTestId("responsive-layout");
      expect(layout).toHaveClass("layout-toggle");
    });

    it("should apply mobile layout classes for sm breakpoint", () => {
      window.matchMedia = createMatchMedia(600) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 600,
      });

      render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      const layout = screen.getByTestId("responsive-layout");
      expect(layout).toHaveClass("layout-mobile");
    });
  });

  describe("callbacks", () => {
    it("should call onBreakpointChange when breakpoint changes", () => {
      window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 1440,
      });

      const onBreakpointChange = vi.fn();
      render(
        <TestProvider>
          <ResponsiveLayout onBreakpointChange={onBreakpointChange}>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      // Initial call
      expect(onBreakpointChange).toHaveBeenCalledWith("xl");
    });
  });

  describe("styling", () => {
    it("should apply custom className", () => {
      window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
      render(
        <TestProvider>
          <ResponsiveLayout className="custom-class">
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );

      expect(screen.getByTestId("responsive-layout")).toHaveClass(
        "custom-class",
      );
    });
  });

  describe("axe accessibility", () => {
    it("should have no accessibility violations", async () => {
      window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
      const { container } = render(
        <TestProvider>
          <ResponsiveLayout>
            <div>Content</div>
          </ResponsiveLayout>
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});

describe("useBreakpoint hook", () => {
  const originalMatchMedia = window.matchMedia;

  afterEach(() => {
    cleanup();
    window.matchMedia = originalMatchMedia;
  });

  function TestComponent({
    onBreakpoint,
  }: {
    onBreakpoint: (bp: Breakpoint) => void;
  }) {
    const breakpoint = useBreakpoint();
    onBreakpoint(breakpoint);
    return <div data-testid="test">{breakpoint}</div>;
  }

  it("should return xl for large screens", () => {
    window.matchMedia = createMatchMedia(1440) as typeof window.matchMedia;
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 1440,
    });

    const onBreakpoint = vi.fn();
    render(
      <TestProvider>
        <TestComponent onBreakpoint={onBreakpoint} />
      </TestProvider>,
    );

    expect(onBreakpoint).toHaveBeenCalledWith("xl");
  });

  it("should return sm for mobile screens", () => {
    window.matchMedia = createMatchMedia(400) as typeof window.matchMedia;
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 400,
    });

    const onBreakpoint = vi.fn();
    render(
      <TestProvider>
        <TestComponent onBreakpoint={onBreakpoint} />
      </TestProvider>,
    );

    expect(onBreakpoint).toHaveBeenCalledWith("sm");
  });
});
