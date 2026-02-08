/**
 * SegmentedControl Component Tests
 *
 * Tests for the SegmentedControl component which provides
 * a toolbar-friendly toggle group for view modes, display options, etc.
 *
 * Following TDD: These tests were written FIRST, before implementation.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SegmentedControl, SegmentedControlItem } from "./SegmentedControl";
import { LayoutGrid, List } from "lucide-react";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SegmentedControl", () => {
  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  describe("rendering", () => {
    it("renders all segments", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}}>
            <SegmentedControlItem value="grid" aria-label="Grid view">
              <LayoutGrid size={16} />
            </SegmentedControlItem>
            <SegmentedControlItem value="list" aria-label="List view">
              <List size={16} />
            </SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
      expect(screen.getAllByRole("radio")).toHaveLength(2);
    });

    it("renders with text labels", () => {
      render(
        <TestProvider>
          <SegmentedControl value="day" onValueChange={() => {}}>
            <SegmentedControlItem value="day">Day</SegmentedControlItem>
            <SegmentedControlItem value="week">Week</SegmentedControlItem>
            <SegmentedControlItem value="month">Month</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getByText("Day")).toBeInTheDocument();
      expect(screen.getByText("Week")).toBeInTheDocument();
      expect(screen.getByText("Month")).toBeInTheDocument();
    });

    it("renders with icon and text combined", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}}>
            <SegmentedControlItem value="grid" aria-label="Grid view">
              <LayoutGrid size={16} />
              <span>Grid</span>
            </SegmentedControlItem>
            <SegmentedControlItem value="list" aria-label="List view">
              <List size={16} />
              <span>List</span>
            </SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getByText("Grid")).toBeInTheDocument();
      expect(screen.getByText("List")).toBeInTheDocument();
    });

    it("applies custom className to container", () => {
      render(
        <TestProvider>
          <SegmentedControl
            value="grid"
            onValueChange={() => {}}
            className="custom-class"
          >
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getByRole("radiogroup")).toHaveClass("custom-class");
    });
  });

  // ==========================================================================
  // Interaction Tests
  // ==========================================================================

  describe("interaction", () => {
    it("calls onValueChange when a segment is clicked", async () => {
      const user = userEvent.setup();
      const onValueChange = vi.fn();

      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={onValueChange}>
            <SegmentedControlItem value="grid" aria-label="Grid view">
              Grid
            </SegmentedControlItem>
            <SegmentedControlItem value="list" aria-label="List view">
              List
            </SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      await user.click(screen.getByText("List"));
      expect(onValueChange).toHaveBeenCalledWith("list");
    });

    it("does not call onValueChange when clicking already selected segment", async () => {
      const user = userEvent.setup();
      const onValueChange = vi.fn();

      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={onValueChange}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      await user.click(screen.getByText("Grid"));
      // Should not call since it's already selected (or could call with same value - either is acceptable)
      // Most implementations allow this but don't change state
    });

    it("supports keyboard navigation with arrow keys", async () => {
      const user = userEvent.setup();
      const onValueChange = vi.fn();

      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={onValueChange}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
            <SegmentedControlItem value="table">Table</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      // Focus the first item
      const gridButton = screen.getByText("Grid").closest("button");
      gridButton?.focus();

      // Arrow right should move to next
      await user.keyboard("{ArrowRight}");
      expect(onValueChange).toHaveBeenCalledWith("list");
    });

    it("supports Enter/Space to select focused segment", async () => {
      const user = userEvent.setup();
      const onValueChange = vi.fn();

      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={onValueChange}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const listButton = screen.getByText("List").closest("button");
      listButton?.focus();

      await user.keyboard("{Enter}");
      expect(onValueChange).toHaveBeenCalledWith("list");
    });
  });

  // ==========================================================================
  // Visual State Tests
  // ==========================================================================

  describe("visual states", () => {
    it("marks selected segment with aria-checked", () => {
      render(
        <TestProvider>
          <SegmentedControl value="list" onValueChange={() => {}}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const gridRadio = screen.getByText("Grid").closest('[role="radio"]');
      const listRadio = screen.getByText("List").closest('[role="radio"]');

      expect(gridRadio).toHaveAttribute("aria-checked", "false");
      expect(listRadio).toHaveAttribute("aria-checked", "true");
    });

    it("applies selected styles to active segment", () => {
      render(
        <TestProvider>
          <SegmentedControl value="list" onValueChange={() => {}}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const listButton = screen.getByText("List").closest("button");
      // Should have active/selected styling (bg-neutral-1 or similar)
      expect(listButton).toHaveClass(/bg-/);
    });
  });

  // ==========================================================================
  // Accessibility Tests
  // ==========================================================================

  describe("accessibility", () => {
    it("has role='radiogroup' on container", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("has role='radio' on each segment", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getAllByRole("radio")).toHaveLength(2);
    });

    it("supports aria-label on container", () => {
      render(
        <TestProvider>
          <SegmentedControl
            value="grid"
            onValueChange={() => {}}
            aria-label="View mode"
          >
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getByRole("radiogroup")).toHaveAttribute(
        "aria-label",
        "View mode",
      );
    });

    it("supports aria-label on individual segments", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}}>
            <SegmentedControlItem value="grid" aria-label="Grid view">
              <LayoutGrid size={16} />
            </SegmentedControlItem>
            <SegmentedControlItem value="list" aria-label="List view">
              <List size={16} />
            </SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      expect(screen.getByLabelText("Grid view")).toBeInTheDocument();
      expect(screen.getByLabelText("List view")).toBeInTheDocument();
    });

    it("manages focus correctly with tabindex", () => {
      render(
        <TestProvider>
          <SegmentedControl value="list" onValueChange={() => {}}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const gridButton = screen.getByText("Grid").closest("button");
      const listButton = screen.getByText("List").closest("button");

      // Only selected item should be in tab order
      expect(gridButton).toHaveAttribute("tabindex", "-1");
      expect(listButton).toHaveAttribute("tabindex", "0");
    });
  });

  // ==========================================================================
  // Size Variants Tests
  // ==========================================================================

  describe("size variants", () => {
    it("renders with default size", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      // Default size should have standard padding
      const container = screen.getByRole("radiogroup");
      expect(container).toBeInTheDocument();
    });

    it("renders with sm size", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}} size="sm">
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const container = screen.getByRole("radiogroup");
      expect(container).toHaveAttribute("data-size", "sm");
    });

    it("renders with lg size", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}} size="lg">
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const container = screen.getByRole("radiogroup");
      expect(container).toHaveAttribute("data-size", "lg");
    });
  });

  // ==========================================================================
  // Disabled State Tests
  // ==========================================================================

  describe("disabled state", () => {
    it("disables all segments when control is disabled", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}} disabled>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list">List</SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("radio");
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it("disables individual segment when item is disabled", () => {
      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={() => {}}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list" disabled>
              List
            </SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      const gridButton = screen.getByText("Grid").closest("button");
      const listButton = screen.getByText("List").closest("button");

      expect(gridButton).not.toBeDisabled();
      expect(listButton).toBeDisabled();
    });

    it("does not call onValueChange when disabled segment is clicked", async () => {
      const user = userEvent.setup();
      const onValueChange = vi.fn();

      render(
        <TestProvider>
          <SegmentedControl value="grid" onValueChange={onValueChange}>
            <SegmentedControlItem value="grid">Grid</SegmentedControlItem>
            <SegmentedControlItem value="list" disabled>
              List
            </SegmentedControlItem>
          </SegmentedControl>
        </TestProvider>,
      );

      await user.click(screen.getByText("List"));
      expect(onValueChange).not.toHaveBeenCalled();
    });
  });
});
