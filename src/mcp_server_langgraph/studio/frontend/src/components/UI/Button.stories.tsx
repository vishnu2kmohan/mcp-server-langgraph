/**
 * Button Component Stories
 *
 * Storybook stories for the Button component.
 * Showcases all variants, sizes, and states.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Plus, ArrowRight, Download } from "lucide-react";
import { Button } from "./Button";

const meta: Meta<typeof Button> = {
  title: "Design System/Button",
  component: Button,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A consistent, accessible button component with multiple variants. Uses CVA for type-safe variant management.",
      },
    },
  },
  argTypes: {
    variant: {
      control: "select",
      options: [
        "primary",
        "secondary",
        "ghost",
        "danger",
        "success",
        "outline",
      ],
      description: "Visual variant of the button",
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
      description: "Size of the button",
    },
    loading: {
      control: "boolean",
      description: "Whether the button is in a loading state",
    },
    disabled: {
      control: "boolean",
      description: "Whether the button is disabled",
    },
    fullWidth: {
      control: "boolean",
      description: "Whether the button should take full width",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Button>;

// =============================================================================
// Basic Stories
// =============================================================================

export const Default: Story = {
  args: {
    children: "Button",
  },
};

export const Primary: Story = {
  args: {
    variant: "primary",
    children: "Primary Button",
  },
};

export const Secondary: Story = {
  args: {
    variant: "secondary",
    children: "Secondary Button",
  },
};

export const Ghost: Story = {
  args: {
    variant: "ghost",
    children: "Ghost Button",
  },
};

export const Danger: Story = {
  args: {
    variant: "danger",
    children: "Danger Button",
  },
};

export const Success: Story = {
  args: {
    variant: "success",
    children: "Success Button",
  },
};

export const Outline: Story = {
  args: {
    variant: "outline",
    children: "Outline Button",
  },
};

// =============================================================================
// Sizes
// =============================================================================

export const Small: Story = {
  args: {
    size: "sm",
    children: "Small Button",
  },
};

export const Medium: Story = {
  args: {
    size: "md",
    children: "Medium Button",
  },
};

export const Large: Story = {
  args: {
    size: "lg",
    children: "Large Button",
  },
};

// =============================================================================
// States
// =============================================================================

export const Loading: Story = {
  args: {
    loading: true,
    children: "Loading...",
  },
};

export const Disabled: Story = {
  args: {
    disabled: true,
    children: "Disabled Button",
  },
};

export const FullWidth: Story = {
  args: {
    fullWidth: true,
    children: "Full Width Button",
  },
  parameters: {
    layout: "padded",
  },
};

// =============================================================================
// With Icons
// =============================================================================

export const WithLeftIcon: Story = {
  args: {
    leftIcon: <Plus className="h-4 w-4" />,
    children: "Add Item",
  },
};

export const WithRightIcon: Story = {
  args: {
    rightIcon: <ArrowRight className="h-4 w-4" />,
    children: "Continue",
  },
};

export const WithBothIcons: Story = {
  args: {
    leftIcon: <Download className="h-4 w-4" />,
    rightIcon: <ArrowRight className="h-4 w-4" />,
    children: "Download & Continue",
  },
};

// =============================================================================
// Showcase Stories
// =============================================================================

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-4">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="danger">Danger</Button>
      <Button variant="success">Success</Button>
      <Button variant="outline">Outline</Button>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All button variants displayed together for comparison.",
      },
    },
  },
};

export const AllSizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <Button size="sm">Small</Button>
      <Button size="md">Medium</Button>
      <Button size="lg">Large</Button>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All button sizes displayed together for comparison.",
      },
    },
  },
};

export const AllVariantsDisabled: Story = {
  render: () => (
    <div className="flex flex-wrap gap-4">
      <Button variant="primary" disabled>
        Primary
      </Button>
      <Button variant="secondary" disabled>
        Secondary
      </Button>
      <Button variant="ghost" disabled>
        Ghost
      </Button>
      <Button variant="danger" disabled>
        Danger
      </Button>
      <Button variant="success" disabled>
        Success
      </Button>
      <Button variant="outline" disabled>
        Outline
      </Button>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All button variants in disabled state.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-900 p-6 rounded-lg">
      <div className="flex flex-wrap gap-4">
        <Button variant="primary">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="danger">Danger</Button>
        <Button variant="success">Success</Button>
        <Button variant="outline">Outline</Button>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Button variants in dark mode context.",
      },
    },
  },
};
