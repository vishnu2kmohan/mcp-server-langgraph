/**
 * Badge Component Stories
 *
 * Storybook stories for the Badge component.
 * Showcases all variants, sizes, and states.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Check, AlertTriangle, X, Info } from "lucide-react";
import { Badge } from "./Badge";

const meta: Meta<typeof Badge> = {
  title: "Design System/Badge",
  component: Badge,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A consistent, accessible badge component with multiple variants. Uses CVA for type-safe variant management.",
      },
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "primary", "success", "warning", "error", "outline"],
      description: "Visual variant of the badge",
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
      description: "Size of the badge",
    },
    pill: {
      control: "boolean",
      description: "Render as pill (fully rounded)",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Badge>;

// =============================================================================
// Basic Stories
// =============================================================================

export const Default: Story = {
  args: {
    children: "Badge",
  },
};

export const Primary: Story = {
  args: {
    variant: "primary",
    children: "Primary",
  },
};

export const Success: Story = {
  args: {
    variant: "success",
    children: "Success",
  },
};

export const Warning: Story = {
  args: {
    variant: "warning",
    children: "Warning",
  },
};

export const Error: Story = {
  args: {
    variant: "error",
    children: "Error",
  },
};

export const Outline: Story = {
  args: {
    variant: "outline",
    children: "Outline",
  },
};

// =============================================================================
// Sizes
// =============================================================================

export const Small: Story = {
  args: {
    size: "sm",
    children: "Small",
  },
};

export const Medium: Story = {
  args: {
    size: "md",
    children: "Medium",
  },
};

export const Large: Story = {
  args: {
    size: "lg",
    children: "Large",
  },
};

// =============================================================================
// Pill Mode
// =============================================================================

export const Pill: Story = {
  args: {
    pill: true,
    children: "Pill Badge",
  },
};

// =============================================================================
// With Icons
// =============================================================================

export const WithSuccessIcon: Story = {
  args: {
    variant: "success",
    icon: <Check className="h-3 w-3" />,
    children: "Completed",
  },
};

export const WithWarningIcon: Story = {
  args: {
    variant: "warning",
    icon: <AlertTriangle className="h-3 w-3" />,
    children: "Warning",
  },
};

export const WithErrorIcon: Story = {
  args: {
    variant: "error",
    icon: <X className="h-3 w-3" />,
    children: "Failed",
  },
};

export const WithInfoIcon: Story = {
  args: {
    variant: "primary",
    icon: <Info className="h-3 w-3" />,
    children: "Info",
  },
};

// =============================================================================
// Showcase Stories
// =============================================================================

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge variant="default">Default</Badge>
      <Badge variant="primary">Primary</Badge>
      <Badge variant="success">Success</Badge>
      <Badge variant="warning">Warning</Badge>
      <Badge variant="error">Error</Badge>
      <Badge variant="outline">Outline</Badge>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All badge variants displayed together for comparison.",
      },
    },
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-2">
      <Badge size="sm">Small</Badge>
      <Badge size="md">Medium</Badge>
      <Badge size="lg">Large</Badge>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All badge sizes displayed together for comparison.",
      },
    },
  },
};

export const StatusBadges: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge variant="success" icon={<Check className="h-3 w-3" />}>
        Active
      </Badge>
      <Badge variant="warning" icon={<AlertTriangle className="h-3 w-3" />}>
        Pending
      </Badge>
      <Badge variant="error" icon={<X className="h-3 w-3" />}>
        Failed
      </Badge>
      <Badge variant="default">Draft</Badge>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Common status badge patterns with icons.",
      },
    },
  },
};

export const PillVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge pill variant="default">
        12
      </Badge>
      <Badge pill variant="primary">
        New
      </Badge>
      <Badge pill variant="success">
        99+
      </Badge>
      <Badge pill variant="error">
        3
      </Badge>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Pill-shaped badges often used for counts and notifications.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <div className="flex flex-wrap gap-2">
        <Badge variant="default">Default</Badge>
        <Badge variant="primary">Primary</Badge>
        <Badge variant="success">Success</Badge>
        <Badge variant="warning">Warning</Badge>
        <Badge variant="error">Error</Badge>
        <Badge variant="outline">Outline</Badge>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Badge variants in dark mode context.",
      },
    },
  },
};
