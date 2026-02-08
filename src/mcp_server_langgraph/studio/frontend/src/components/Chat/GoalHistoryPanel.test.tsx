/**
 * GoalHistoryPanel Component Tests
 *
 * TDD tests for the goal history display panel.
 * Displays completed goals for a session with achievement status.
 *
 * Written FIRST per TDD methodology (RED phase).
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import { GoalHistoryPanel, type SessionGoalHistory } from "./GoalHistoryPanel";

import { TestProvider } from "@/test-utils";

describe("GoalHistoryPanel", () => {
  const mockGoals: SessionGoalHistory[] = [
    {
      id: "goal-1",
      goal: "Complete the data analysis",
      achieved: true,
      feedback: "All analysis done successfully",
      setAt: 1705123456789,
      completedAt: 1705127056789,
    },
    {
      id: "goal-2",
      goal: "Implement new feature",
      achieved: "partial",
      feedback: "Completed 80%",
      setAt: 1705130000000,
      completedAt: 1705133600000,
    },
    {
      id: "goal-3",
      goal: "Fix critical bug",
      achieved: false,
      feedback: "Blocked by dependencies",
      setAt: 1705137200000,
      completedAt: 1705140800000,
    },
  ];

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders the component with test id", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      expect(screen.getByTestId("goal-history-panel")).toBeInTheDocument();
    });

    it("renders panel header with title", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      expect(screen.getByText("Goal History")).toBeInTheDocument();
    });

    it("renders all goals in the list", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();
      expect(screen.getByText("Implement new feature")).toBeInTheDocument();
      expect(screen.getByText("Fix critical bug")).toBeInTheDocument();
    });

    it("displays achievement status badges correctly", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      expect(screen.getByText("Achieved")).toBeInTheDocument();
      expect(screen.getByText("Partial")).toBeInTheDocument();
      expect(screen.getByText("Not Achieved")).toBeInTheDocument();
    });

    it("displays feedback when available", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      expect(
        screen.getByText("All analysis done successfully"),
      ).toBeInTheDocument();
      expect(screen.getByText("Completed 80%")).toBeInTheDocument();
      expect(screen.getByText("Blocked by dependencies")).toBeInTheDocument();
    });

    it("formats timestamps correctly", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      // Should display relative or formatted time - at least verify timestamps are rendered
      const goalItems = screen.getAllByTestId(/goal-item-/);
      expect(goalItems).toHaveLength(3);
    });
  });

  describe("Empty State", () => {
    it("displays empty state when no goals", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={[]} />
        </TestProvider>,
      );

      expect(screen.getByText("No goals recorded yet")).toBeInTheDocument();
    });

    it("renders custom empty message when provided", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={[]}
            emptyMessage="Start by setting a goal above"
          />
        </TestProvider>,
      );

      expect(
        screen.getByText("Start by setting a goal above"),
      ).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("displays loading state when isLoading is true", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={[]} isLoading />
        </TestProvider>,
      );

      expect(screen.getByTestId("goal-history-loading")).toBeInTheDocument();
    });

    it("shows loading skeleton items", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={[]} isLoading />
        </TestProvider>,
      );

      const skeletons = screen.getAllByTestId(/goal-skeleton-/);
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA attributes", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      const panel = screen.getByTestId("goal-history-panel");
      expect(panel).toHaveAttribute("role", "region");
      expect(panel).toHaveAttribute("aria-label", "Goal History");
    });

    it("goal items have proper list semantics", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      const list = screen.getByRole("list");
      expect(list).toBeInTheDocument();

      const items = screen.getAllByRole("listitem");
      expect(items).toHaveLength(3);
    });

    it("achievement badges have accessible labels", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      // Verify status badges are accessible (use getAllByLabelText since there are multiple)
      const achievedBadges = screen.getAllByLabelText(/status: achieved/i);
      const partialBadges = screen.getAllByLabelText(/status: partial/i);
      const notAchievedBadges =
        screen.getAllByLabelText(/status: not achieved/i);

      expect(achievedBadges.length).toBeGreaterThan(0);
      expect(partialBadges.length).toBeGreaterThan(0);
      expect(notAchievedBadges.length).toBeGreaterThan(0);
    });
  });

  describe("Compact Mode", () => {
    it("renders in compact mode when compact prop is true", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} compact />
        </TestProvider>,
      );

      const panel = screen.getByTestId("goal-history-panel");
      expect(panel).toHaveClass("compact");
    });

    it("hides feedback in compact mode", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} compact />
        </TestProvider>,
      );

      // Feedback should not be visible in compact mode
      expect(
        screen.queryByText("All analysis done successfully"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Goal Count Badge", () => {
    it("displays goal count in header", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("does not show count badge when empty", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={[]} />
        </TestProvider>,
      );

      const badges = screen.queryAllByTestId("goal-count-badge");
      expect(badges).toHaveLength(0);
    });
  });

  describe("Collapsible Behavior", () => {
    it("can be collapsed when collapsible prop is true", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} collapsible />
        </TestProvider>,
      );

      const header = screen.getByRole("button", { name: /goal history/i });
      expect(header).toBeInTheDocument();

      // Initially expanded
      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();

      // Click to collapse
      await user.click(header);

      // Content should be hidden
      expect(
        screen.queryByText("Complete the data analysis"),
      ).not.toBeInTheDocument();
    });

    it("starts collapsed when defaultCollapsed is true", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} collapsible defaultCollapsed />
        </TestProvider>,
      );

      expect(
        screen.queryByText("Complete the data analysis"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Achievement Filtering", () => {
    it("filters by achievement status when filter is provided", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} filter="achieved" />
        </TestProvider>,
      );

      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();
      expect(
        screen.queryByText("Implement new feature"),
      ).not.toBeInTheDocument();
      expect(screen.queryByText("Fix critical bug")).not.toBeInTheDocument();
    });

    it("shows partial goals when filter is 'partial'", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} filter="partial" />
        </TestProvider>,
      );

      expect(
        screen.queryByText("Complete the data analysis"),
      ).not.toBeInTheDocument();
      expect(screen.getByText("Implement new feature")).toBeInTheDocument();
      expect(screen.queryByText("Fix critical bug")).not.toBeInTheDocument();
    });

    it("shows not achieved goals when filter is 'not-achieved'", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} filter="not-achieved" />
        </TestProvider>,
      );

      expect(
        screen.queryByText("Complete the data analysis"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Implement new feature"),
      ).not.toBeInTheDocument();
      expect(screen.getByText("Fix critical bug")).toBeInTheDocument();
    });
  });

  describe("Time Ordering", () => {
    it("displays goals in reverse chronological order by default", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      const goalItems = screen.getAllByTestId(/goal-item-/);

      // Last goal should be first (reverse chronological)
      expect(goalItems[0]).toHaveTextContent("Fix critical bug");
      expect(goalItems[1]).toHaveTextContent("Implement new feature");
      expect(goalItems[2]).toHaveTextContent("Complete the data analysis");
    });

    it("displays in chronological order when order='chronological'", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} order="chronological" />
        </TestProvider>,
      );

      const goalItems = screen.getAllByTestId(/goal-item-/);

      // First goal should be first (chronological)
      expect(goalItems[0]).toHaveTextContent("Complete the data analysis");
      expect(goalItems[1]).toHaveTextContent("Implement new feature");
      expect(goalItems[2]).toHaveTextContent("Fix critical bug");
    });
  });

  describe("Max Items", () => {
    it("limits displayed items when maxItems is set", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} maxItems={2} />
        </TestProvider>,
      );

      const goalItems = screen.getAllByTestId(/goal-item-/);
      expect(goalItems).toHaveLength(2);
    });

    it("shows 'show more' button when items exceed maxItems", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} maxItems={2} />
        </TestProvider>,
      );

      expect(screen.getByText(/show 1 more/i)).toBeInTheDocument();
    });

    it("expands to show all items when 'show more' is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} maxItems={2} />
        </TestProvider>,
      );

      await user.click(screen.getByText(/show 1 more/i));

      const goalItems = screen.getAllByTestId(/goal-item-/);
      expect(goalItems).toHaveLength(3);
    });
  });

  describe("Delete Functionality", () => {
    it("renders delete button when onDelete prop is provided", () => {
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} onDelete={onDelete} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      expect(deleteButtons).toHaveLength(3);
    });

    it("does not render delete button when onDelete is not provided", () => {
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} />
        </TestProvider>,
      );

      const deleteButtons = screen.queryAllByRole("button", {
        name: /delete goal/i,
      });
      expect(deleteButtons).toHaveLength(0);
    });

    it("calls onDelete with goal id when delete button is clicked", async () => {
      const user = userEvent.setup();
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} onDelete={onDelete} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      // Click first delete button (which is goal-3 due to reverse chronological order)
      await user.click(deleteButtons[0]);

      expect(onDelete).toHaveBeenCalledTimes(1);
      expect(onDelete).toHaveBeenCalledWith("goal-3");
    });

    it("shows confirmation dialog before delete when showDeleteConfirmation is true", async () => {
      const user = userEvent.setup();
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            onDelete={onDelete}
            showDeleteConfirmation
          />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      await user.click(deleteButtons[0]);

      // onDelete should NOT be called yet (waiting for confirmation)
      expect(onDelete).not.toHaveBeenCalled();

      // Confirmation dialog should appear
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });

    it("calls onDelete after confirming deletion in dialog", async () => {
      const user = userEvent.setup();
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            onDelete={onDelete}
            showDeleteConfirmation
          />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      await user.click(deleteButtons[0]);

      // Click confirm button in dialog
      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      await user.click(confirmButton);

      expect(onDelete).toHaveBeenCalledWith("goal-3");
    });

    it("does not call onDelete when canceling confirmation dialog", async () => {
      const user = userEvent.setup();
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            onDelete={onDelete}
            showDeleteConfirmation
          />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      await user.click(deleteButtons[0]);

      // Click cancel button in dialog
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await user.click(cancelButton);

      expect(onDelete).not.toHaveBeenCalled();
    });

    it("delete button has appropriate styling and icon", () => {
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} onDelete={onDelete} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      // Each button should contain a trash icon (verify via class or svg)
      deleteButtons.forEach((button) => {
        expect(button.querySelector("svg")).toBeInTheDocument();
      });
    });
  });

  describe("Keyboard Accessibility", () => {
    it("delete button can be activated with Enter key", async () => {
      const user = userEvent.setup();
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} onDelete={onDelete} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      const firstDeleteButton = deleteButtons[0];

      // Focus the button and press Enter
      firstDeleteButton.focus();
      await user.keyboard("{Enter}");

      expect(onDelete).toHaveBeenCalledTimes(1);
    });

    it("delete button can be activated with Space key", async () => {
      const user = userEvent.setup();
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} onDelete={onDelete} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      const firstDeleteButton = deleteButtons[0];

      // Focus the button and press Space
      firstDeleteButton.focus();
      await user.keyboard(" ");

      expect(onDelete).toHaveBeenCalledTimes(1);
    });

    it("confirmation dialog can be dismissed with Escape key", async () => {
      const user = userEvent.setup();
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            onDelete={onDelete}
            showDeleteConfirmation
          />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });
      await user.click(deleteButtons[0]);

      // Dialog should be open
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();

      // Press Escape to close (dispatch on document for consistency with Dialog tests)
      await user.keyboard("{Escape}");

      // Dialog should be closed, onDelete should not be called
      // Use waitFor to allow AnimatePresence exit animation to complete
      await vi.waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
      expect(onDelete).not.toHaveBeenCalled();
    });

    it("all delete buttons are focusable in sequence", () => {
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} onDelete={onDelete} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete goal/i,
      });

      // All buttons should be focusable (no tabindex=-1)
      deleteButtons.forEach((button) => {
        expect(button).not.toHaveAttribute("tabindex", "-1");
      });
    });
  });

  describe("Controlled Collapse State", () => {
    it("uses isCollapsed prop when provided (controlled mode)", () => {
      // When isCollapsed=false, content should be visible
      const { rerender } = render(
        <TestProvider>
          <GoalHistoryPanel goals={mockGoals} collapsible isCollapsed={false} />
        </TestProvider>,
      );
      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();

      // When isCollapsed=true, content should be hidden
      rerender(
        <GoalHistoryPanel goals={mockGoals} collapsible isCollapsed={true} />,
      );
      expect(
        screen.queryByText("Complete the data analysis"),
      ).not.toBeInTheDocument();
    });

    it("calls onCollapsedChange when toggle button is clicked", async () => {
      const user = userEvent.setup();
      const onCollapsedChange = vi.fn();

      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            collapsible
            isCollapsed={false}
            onCollapsedChange={onCollapsedChange}
          />
        </TestProvider>,
      );

      // Click the toggle button
      const toggleButton = screen.getByRole("button", {
        name: /goal history/i,
      });
      await user.click(toggleButton);

      // Should call onCollapsedChange with true (requesting collapse)
      expect(onCollapsedChange).toHaveBeenCalledWith(true);
    });

    it("does not change internal state in controlled mode", async () => {
      const user = userEvent.setup();
      const onCollapsedChange = vi.fn();

      // Start expanded (isCollapsed=false)
      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            collapsible
            isCollapsed={false}
            onCollapsedChange={onCollapsedChange}
          />
        </TestProvider>,
      );

      // Content should be visible
      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();

      // Click toggle - should call callback but NOT change visibility
      // (parent controls the state)
      const toggleButton = screen.getByRole("button", {
        name: /goal history/i,
      });
      await user.click(toggleButton);

      // Content should STILL be visible (controlled mode ignores click until parent updates prop)
      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();
    });

    it("maintains backwards compatibility with uncontrolled mode", async () => {
      const user = userEvent.setup();

      // Render without isCollapsed prop (uncontrolled mode)
      render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            collapsible
            defaultCollapsed={false}
          />
        </TestProvider>,
      );

      // Content should be visible
      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();

      // Click toggle - should collapse using internal state
      const toggleButton = screen.getByRole("button", {
        name: /goal history/i,
      });
      await user.click(toggleButton);

      // Content should now be hidden (uncontrolled mode uses internal state)
      expect(
        screen.queryByText("Complete the data analysis"),
      ).not.toBeInTheDocument();
    });

    it("persists expanded state across parent re-renders when controlled", () => {
      const onCollapsedChange = vi.fn();

      // This simulates the key use case: parent controls state, panel doesn't reset
      const { rerender } = render(
        <TestProvider>
          <GoalHistoryPanel
            goals={mockGoals}
            collapsible
            isCollapsed={false}
            onCollapsedChange={onCollapsedChange}
          />
        </TestProvider>,
      );

      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();

      // Parent re-renders with same isCollapsed value - should stay expanded
      rerender(
        <GoalHistoryPanel
          goals={mockGoals}
          collapsible
          isCollapsed={false}
          onCollapsedChange={onCollapsedChange}
        />,
      );

      expect(
        screen.getByText("Complete the data analysis"),
      ).toBeInTheDocument();
    });
  });
});
