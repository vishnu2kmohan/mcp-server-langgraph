/**
 * GoalHistoryPanel Stories
 *
 * Storybook stories showcasing the GoalHistoryPanel component
 * in various states and configurations.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";

import { GoalHistoryPanel, type SessionGoalHistory } from "./GoalHistoryPanel";

// Handler for delete actions - logs to console in development
const handleDelete = (goalId: string) => {
  // In Storybook, we can observe the action via the component's behavior
  void goalId;
};

const meta: Meta<typeof GoalHistoryPanel> = {
  title: "Chat/GoalHistoryPanel",
  component: GoalHistoryPanel,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Displays completed goals for a session with achievement status badges, filtering, and collapsible behavior.",
      },
    },
  },
  argTypes: {
    goals: {
      description: "Array of completed goals to display",
    },
    isLoading: {
      control: "boolean",
      description: "Show loading skeleton state",
    },
    compact: {
      control: "boolean",
      description: "Compact mode - hides feedback",
    },
    collapsible: {
      control: "boolean",
      description: "Allow collapsing/expanding the panel",
    },
    defaultCollapsed: {
      control: "boolean",
      description: "Start in collapsed state",
    },
    filter: {
      control: "select",
      options: ["all", "achieved", "partial", "not-achieved"],
      description: "Filter goals by achievement status",
    },
    order: {
      control: "select",
      options: ["chronological", "reverse-chronological"],
      description: "Order of goals",
    },
    maxItems: {
      control: "number",
      description: "Maximum items to show before 'show more'",
    },
    emptyMessage: {
      control: "text",
      description: "Custom message when no goals",
    },
  },
};

export default meta;
type Story = StoryObj<typeof GoalHistoryPanel>;

// Sample goal data
const sampleGoals: SessionGoalHistory[] = [
  {
    id: "goal-1",
    goal: "Complete the data analysis for Q4 report",
    achieved: true,
    feedback: "All analysis completed successfully. Charts and insights ready for review.",
    setAt: Date.now() - 3600000 * 24, // 24 hours ago
    completedAt: Date.now() - 3600000 * 20, // 20 hours ago
  },
  {
    id: "goal-2",
    goal: "Implement user authentication feature",
    achieved: "partial",
    feedback: "Completed OAuth integration. JWT tokens pending.",
    setAt: Date.now() - 3600000 * 48, // 48 hours ago
    completedAt: Date.now() - 3600000 * 44, // 44 hours ago
  },
  {
    id: "goal-3",
    goal: "Fix critical production bug in payment processing",
    achieved: false,
    feedback: "Blocked by third-party API issue. Escalated to vendor.",
    setAt: Date.now() - 3600000 * 72, // 72 hours ago
    completedAt: Date.now() - 3600000 * 70, // 70 hours ago
  },
  {
    id: "goal-4",
    goal: "Review and merge PR #1234",
    achieved: true,
    feedback: null,
    setAt: Date.now() - 3600000 * 96, // 96 hours ago
    completedAt: Date.now() - 3600000 * 94, // 94 hours ago
  },
  {
    id: "goal-5",
    goal: "Set up monitoring dashboards",
    achieved: true,
    feedback: "Grafana dashboards configured with all key metrics.",
    setAt: Date.now() - 3600000 * 120, // 120 hours ago
    completedAt: Date.now() - 3600000 * 118, // 118 hours ago
  },
];

/**
 * Default state with multiple goals showing different achievement statuses.
 */
export const Default: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
  },
};

/**
 * All goals achieved - shows success state.
 */
export const AllAchieved: Story = {
  args: {
    goals: sampleGoals.filter((g) => g.achieved === true),
  },
};

/**
 * Mixed achievement statuses with filtering enabled.
 */
export const FilteredByAchieved: Story = {
  args: {
    goals: sampleGoals,
    filter: "achieved",
  },
};

/**
 * Only partially achieved goals.
 */
export const FilteredByPartial: Story = {
  args: {
    goals: sampleGoals,
    filter: "partial",
  },
};

/**
 * Only not achieved goals.
 */
export const FilteredByNotAchieved: Story = {
  args: {
    goals: sampleGoals,
    filter: "not-achieved",
  },
};

/**
 * Empty state when no goals have been recorded.
 */
export const Empty: Story = {
  args: {
    goals: [],
  },
};

/**
 * Empty state with custom message.
 */
export const EmptyCustomMessage: Story = {
  args: {
    goals: [],
    emptyMessage: "Start by setting a goal above to track your progress.",
  },
};

/**
 * Loading state with skeleton placeholders.
 */
export const Loading: Story = {
  args: {
    goals: [],
    isLoading: true,
  },
};

/**
 * Compact mode - hides feedback to save space.
 */
export const Compact: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
    compact: true,
  },
};

/**
 * Collapsible panel - can be expanded/collapsed.
 */
export const Collapsible: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
    collapsible: true,
  },
};

/**
 * Starts collapsed by default.
 */
export const CollapsedByDefault: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
    collapsible: true,
    defaultCollapsed: true,
  },
};

/**
 * With pagination - shows 'show more' button.
 */
export const WithPagination: Story = {
  args: {
    goals: sampleGoals,
    maxItems: 2,
  },
};

/**
 * Chronological order - oldest first.
 */
export const ChronologicalOrder: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
    order: "chronological",
  },
};

/**
 * Single goal - minimal display.
 */
export const SingleGoal: Story = {
  args: {
    goals: [sampleGoals[0]],
  },
};

/**
 * Dark mode preview - uses Storybook's theme decorator.
 */
export const DarkMode: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
  },
  parameters: {
    backgrounds: { default: "dark" },
  },
  decorators: [
    (Story) => (
      <div className="dark bg-neutral-2 p-4 rounded-lg">
        <Story />
      </div>
    ),
  ],
};

/**
 * With delete buttons - shows trash icon for each goal.
 * Uses Storybook actions for demonstration.
 */
export const WithDelete: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
    onDelete: handleDelete,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Each goal displays a delete button. Check the Actions panel to see delete events.",
      },
    },
  },
};

/**
 * With delete confirmation dialog - requires user confirmation before deletion.
 * Click the trash icon, then confirm or cancel in the dialog.
 */
export const WithDeleteConfirmation: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
    onDelete: handleDelete,
    showDeleteConfirmation: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Shows a confirmation dialog before deleting. Try clicking a delete button to see the dialog.",
      },
    },
  },
};

/**
 * Compact mode with delete - combines compact display with delete functionality.
 */
export const CompactWithDelete: Story = {
  args: {
    goals: sampleGoals.slice(0, 3),
    compact: true,
    onDelete: handleDelete,
  },
};

/**
 * Collapsible with delete and confirmation - full-featured panel.
 * Demonstrates all features working together.
 */
export const FullFeatured: Story = {
  args: {
    goals: sampleGoals,
    collapsible: true,
    maxItems: 3,
    onDelete: handleDelete,
    showDeleteConfirmation: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Combines collapsible panel, pagination, and delete with confirmation. This represents the typical production configuration.",
      },
    },
  },
};
