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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ProjectContextBadge } from "./ProjectContextBadge";

import { TestProvider } from "@/test-utils";

expect.extend(toHaveNoViolations);

describe("ProjectContextBadge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render badge when context is active", () => {
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} />
        </TestProvider>,
      );

      expect(screen.getByTestId("project-context-badge")).toBeInTheDocument();
    });

    it("should not render when context is inactive", () => {
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={false} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("project-context-badge"),
      ).not.toBeInTheDocument();
    });

    it("should display context indicator icon", () => {
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} />
        </TestProvider>,
      );

      expect(screen.getByTestId("context-icon")).toBeInTheDocument();
    });

    it("should display context path when provided", () => {
      render(
        <TestProvider>
          <ProjectContextBadge
            hasContext={true}
            contextPath=".studio/context.md"
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} onClick={onClick} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("project-context-badge"));

      expect(onClick).toHaveBeenCalled();
    });

    it("should show tooltip on hover", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ProjectContextBadge
            hasContext={true}
            contextPath=".studio/context.md"
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} size="sm" />
        </TestProvider>,
      );

      expect(screen.getByTestId("project-context-badge")).toHaveAttribute(
        "data-size",
        "sm",
      );
    });

    it("should render medium size by default", () => {
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} isLoading={true} />
        </TestProvider>,
      );

      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible label", () => {
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} />
        </TestProvider>,
      );

      expect(screen.getByTestId("project-context-badge")).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Project context"),
      );
    });

    it("should be keyboard accessible", async () => {
      const onClick = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ProjectContextBadge hasContext={true} onClick={onClick} />
        </TestProvider>,
      );

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
        <TestProvider>
          <ProjectContextBadge hasContext={true} className="custom-class" />
        </TestProvider>,
      );

      expect(screen.getByTestId("project-context-badge")).toHaveClass(
        "custom-class",
      );
    });
  });
});
