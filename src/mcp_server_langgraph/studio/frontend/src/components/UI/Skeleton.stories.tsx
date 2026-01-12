/**
 * Skeleton Loading Component Stories
 *
 * Interactive documentation for skeleton loading components.
 * Showcases base Skeleton and compound components (Card, Text, List).
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Skeleton, SkeletonCard, SkeletonText, SkeletonList } from "./Skeleton";

const meta: Meta<typeof Skeleton> = {
  title: "Design System/Skeleton",
  component: Skeleton,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Animated placeholder components for loading states. Includes base Skeleton and compound components for common patterns.",
      },
    },
  },
  argTypes: {
    rounded: {
      control: "boolean",
      description:
        "Whether to use circular (rounded-full) or rectangular shape",
    },
    className: {
      control: "text",
      description: "Additional CSS classes for dimensions and styling",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Skeleton>;

/**
 * Base skeleton with default rectangular shape
 */
export const Default: Story = {
  args: {
    className: "h-4 w-48",
  },
};

/**
 * Circular skeleton for avatars
 */
export const Rounded: Story = {
  args: {
    rounded: true,
    className: "h-12 w-12",
  },
  parameters: {
    docs: {
      description: {
        story: "Use rounded variant for avatar or icon placeholders.",
      },
    },
  },
};

/**
 * Various sizes demonstration
 */
export const Sizes: Story = {
  render: () => (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-500 w-24">Extra Small:</span>
        <Skeleton className="h-2 w-24" />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-500 w-24">Small:</span>
        <Skeleton className="h-3 w-32" />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-500 w-24">Medium:</span>
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-500 w-24">Large:</span>
        <Skeleton className="h-6 w-64" />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-500 w-24">Extra Large:</span>
        <Skeleton className="h-8 w-80" />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Skeleton dimensions are controlled via className prop.",
      },
    },
  },
};

/**
 * Avatar sizes with rounded variant
 */
export const AvatarSizes: Story = {
  render: () => (
    <div className="flex items-end gap-4">
      <div className="text-center">
        <Skeleton rounded className="h-8 w-8" />
        <span className="text-xs text-neutral-500 mt-1 block">SM</span>
      </div>
      <div className="text-center">
        <Skeleton rounded className="h-10 w-10" />
        <span className="text-xs text-neutral-500 mt-1 block">MD</span>
      </div>
      <div className="text-center">
        <Skeleton rounded className="h-12 w-12" />
        <span className="text-xs text-neutral-500 mt-1 block">LG</span>
      </div>
      <div className="text-center">
        <Skeleton rounded className="h-16 w-16" />
        <span className="text-xs text-neutral-500 mt-1 block">XL</span>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Rounded skeletons for avatar placeholders of various sizes.",
      },
    },
  },
};

/**
 * SkeletonCard compound component
 */
export const CardSkeleton: Story = {
  render: () => (
    <div className="max-w-sm">
      <SkeletonCard />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Pre-composed card skeleton with header and content areas. Perfect for card loading states.",
      },
    },
  },
};

/**
 * SkeletonText compound component
 */
export const TextSkeleton: Story = {
  render: () => (
    <div className="max-w-md space-y-6">
      <div>
        <h3 className="text-sm font-medium text-neutral-500 mb-2">
          3 lines (default)
        </h3>
        <SkeletonText />
      </div>
      <div>
        <h3 className="text-sm font-medium text-neutral-500 mb-2">5 lines</h3>
        <SkeletonText lines={5} />
      </div>
      <div>
        <h3 className="text-sm font-medium text-neutral-500 mb-2">1 line</h3>
        <SkeletonText lines={1} />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Pre-composed text skeleton with varying line widths. Use lines prop to control count.",
      },
    },
  },
};

/**
 * SkeletonList compound component
 */
export const ListSkeleton: Story = {
  render: () => (
    <div className="max-w-md space-y-6">
      <div>
        <h3 className="text-sm font-medium text-neutral-500 mb-2">
          3 items (default)
        </h3>
        <SkeletonList />
      </div>
      <div>
        <h3 className="text-sm font-medium text-neutral-500 mb-2">5 items</h3>
        <SkeletonList items={5} />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Pre-composed list skeleton with avatar and text. Perfect for list/table loading states.",
      },
    },
  },
};

/**
 * Real-world usage: Profile card loading state
 */
export const ProfileCardLoading: Story = {
  render: () => (
    <div className="max-w-sm p-4 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg">
      <div className="flex items-center gap-4 mb-4">
        <Skeleton rounded className="h-16 w-16" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <SkeletonText lines={2} />
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-24" />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Example of composing skeletons for a profile card loading state.",
      },
    },
  },
};

/**
 * Real-world usage: Table loading state
 */
export const TableLoading: Story = {
  render: () => (
    <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex gap-4 p-3 bg-neutral-50 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-20" />
      </div>
      {/* Rows */}
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex gap-4 p-3 border-b border-neutral-100 dark:border-neutral-700 last:border-b-0"
        >
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Example of composing skeletons for a table loading state.",
      },
    },
  },
};

/**
 * Dark mode demonstration
 */
export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-900 p-6 rounded-lg">
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton rounded className="h-12 w-12" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
        <SkeletonCard />
        <SkeletonList items={2} />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Skeletons automatically adapt to dark mode with appropriate colors.",
      },
    },
  },
};
