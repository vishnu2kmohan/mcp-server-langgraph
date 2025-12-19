/**
 * ProjectContextBadge Tests
 *
 * TDD tests for the Project Context Badge component.
 * Tests cover:
 * - Badge display when context is active
 * - Hidden when no context
 * - Click to open context panel
 * - Tooltip display
 * - WCAG 2.1 AA accessibility
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ProjectContextBadge } from "./ProjectContextBadge";

expect.extend(toHaveNoViolations);

describe("ProjectContextBadge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render badge when context is active", () => {
      render(<ProjectContextBadge hasContext={true} />);

      expect(screen.getByTestId("project-context-badge")).toBeInTheDocument();
    });

    it("should not render when context is inactive", () => {
      render(<ProjectContextBadge hasContext={false} />);

      expect(
        screen.queryByTestId("project-context-badge"),
      ).not.toBeInTheDocument();
    });

    it("should display context indicator icon", () => {
      render(<ProjectContextBadge hasContext={true} />);

      expect(screen.getByTestId("context-icon")).toBeInTheDocument();
    });

    it("should display context path when provided", () => {
      render(
        <ProjectContextBadge
          hasContext={true}
          contextPath=".studio/context.md"
        />,
      );

      expect(screen.getByText(".studio/context.md")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Interaction Tests
  // ===========================================================================

  describe("interactions", () => {
    it("should call onClick when badge is clicked", async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();
      render(<ProjectContextBadge hasContext={true} onClick={onClick} />);

      await user.click(screen.getByTestId("project-context-badge"));

      expect(onClick).toHaveBeenCalled();
    });

    it("should show tooltip on hover", async () => {
      const user = userEvent.setup();
      render(
        <ProjectContextBadge
          hasContext={true}
          contextPath=".studio/context.md"
        />,
      );

      await user.hover(screen.getByTestId("project-context-badge"));

      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Size Variants Tests
  // ===========================================================================

  describe("size variants", () => {
    it("should render small size", () => {
      render(<ProjectContextBadge hasContext={true} size="sm" />);

      expect(screen.getByTestId("project-context-badge")).toHaveAttribute(
        "data-size",
        "sm",
      );
    });

    it("should render medium size by default", () => {
      render(<ProjectContextBadge hasContext={true} />);

      expect(screen.getByTestId("project-context-badge")).toHaveAttribute(
        "data-size",
        "md",
      );
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should show loading indicator when loading", () => {
      render(<ProjectContextBadge hasContext={true} isLoading={true} />);

      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<ProjectContextBadge hasContext={true} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible label", () => {
      render(<ProjectContextBadge hasContext={true} />);

      expect(screen.getByTestId("project-context-badge")).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Project context"),
      );
    });

    it("should be keyboard accessible", async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();
      render(<ProjectContextBadge hasContext={true} onClick={onClick} />);

      const badge = screen.getByTestId("project-context-badge");
      badge.focus();
      await user.keyboard("{Enter}");

      expect(onClick).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <ProjectContextBadge hasContext={true} className="custom-class" />,
      );

      expect(screen.getByTestId("project-context-badge")).toHaveClass(
        "custom-class",
      );
    });
  });
});
