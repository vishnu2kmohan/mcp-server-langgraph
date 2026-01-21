/**
 * SegmentedControl Storybook Stories
 *
 * Demonstrates the SegmentedControl component for mutually exclusive
 * option selection, commonly used for view mode toggles in toolbars.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { LayoutGrid, List, Columns, Table, AlignLeft, AlignCenter, AlignRight, AlignJustify } from "lucide-react";
import { SegmentedControl, SegmentedControlItem } from "./SegmentedControl";

const meta: Meta<typeof SegmentedControl> = {
  title: "UI/SegmentedControl",
  component: SegmentedControl,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A toolbar-friendly toggle group for mutually exclusive options. Uses proper ARIA radiogroup pattern with full keyboard navigation.",
      },
    },
  },
  argTypes: {
    value: {
      control: { type: "select" },
      options: ["grid", "list", "table"],
      description: "Currently selected value",
    },
    size: {
      control: { type: "select" },
      options: ["sm", "md", "lg"],
      description: "Size variant",
    },
    disabled: {
      control: { type: "boolean" },
      description: "Whether the entire control is disabled",
    },
    "aria-label": {
      control: { type: "text" },
      description: "Accessible label for the control",
    },
  },
};

export default meta;
type Story = StoryObj<typeof SegmentedControl>;

// =============================================================================
// Interactive wrapper for state management
// =============================================================================

function SegmentedControlDemo({
  initialValue = "grid",
  size = "md",
  disabled = false,
}: {
  initialValue?: string;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
}) {
  const [value, setValue] = useState(initialValue);

  return (
    <SegmentedControl
      value={value}
      onValueChange={setValue}
      size={size}
      disabled={disabled}
      aria-label="View mode"
    >
      <SegmentedControlItem value="grid" aria-label="Grid view">
        <LayoutGrid size={16} />
      </SegmentedControlItem>
      <SegmentedControlItem value="list" aria-label="List view">
        <List size={16} />
      </SegmentedControlItem>
      <SegmentedControlItem value="table" aria-label="Table view">
        <Table size={16} />
      </SegmentedControlItem>
    </SegmentedControl>
  );
}

// =============================================================================
// Stories
// =============================================================================

/**
 * Default segmented control with icon-only segments for view mode selection.
 */
export const Default: Story = {
  render: () => <SegmentedControlDemo />,
};

/**
 * Small size variant for compact toolbars.
 */
export const SizeSmall: Story = {
  render: () => <SegmentedControlDemo size="sm" />,
};

/**
 * Medium size variant (default).
 */
export const SizeMedium: Story = {
  render: () => <SegmentedControlDemo size="md" />,
};

/**
 * Large size variant for prominent controls.
 */
export const SizeLarge: Story = {
  render: () => <SegmentedControlDemo size="lg" />,
};

/**
 * All sizes displayed together for comparison.
 */
export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-col gap-4 items-start">
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-11 w-16">Small:</span>
        <SegmentedControlDemo size="sm" />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-11 w-16">Medium:</span>
        <SegmentedControlDemo size="md" />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-11 w-16">Large:</span>
        <SegmentedControlDemo size="lg" />
      </div>
    </div>
  ),
};

/**
 * Disabled state prevents all interaction.
 */
export const Disabled: Story = {
  render: () => <SegmentedControlDemo disabled />,
};

/**
 * Text labels instead of icons for clearer options.
 */
export const WithTextLabels: Story = {
  render: () => {
    const [value, setValue] = useState("daily");

    return (
      <SegmentedControl
        value={value}
        onValueChange={setValue}
        aria-label="Time range"
      >
        <SegmentedControlItem value="daily">Daily</SegmentedControlItem>
        <SegmentedControlItem value="weekly">Weekly</SegmentedControlItem>
        <SegmentedControlItem value="monthly">Monthly</SegmentedControlItem>
      </SegmentedControl>
    );
  },
};

/**
 * Icons with text labels for maximum clarity.
 */
export const WithIconsAndText: Story = {
  render: () => {
    const [value, setValue] = useState("grid");

    return (
      <SegmentedControl
        value={value}
        onValueChange={setValue}
        aria-label="View mode"
      >
        <SegmentedControlItem value="grid">
          <LayoutGrid size={16} />
          <span>Grid</span>
        </SegmentedControlItem>
        <SegmentedControlItem value="list">
          <List size={16} />
          <span>List</span>
        </SegmentedControlItem>
        <SegmentedControlItem value="columns">
          <Columns size={16} />
          <span>Columns</span>
        </SegmentedControlItem>
      </SegmentedControl>
    );
  },
};

/**
 * Text alignment control example.
 */
export const TextAlignment: Story = {
  render: () => {
    const [value, setValue] = useState("left");

    return (
      <SegmentedControl
        value={value}
        onValueChange={setValue}
        size="sm"
        aria-label="Text alignment"
      >
        <SegmentedControlItem value="left" aria-label="Align left">
          <AlignLeft size={14} />
        </SegmentedControlItem>
        <SegmentedControlItem value="center" aria-label="Align center">
          <AlignCenter size={14} />
        </SegmentedControlItem>
        <SegmentedControlItem value="right" aria-label="Align right">
          <AlignRight size={14} />
        </SegmentedControlItem>
        <SegmentedControlItem value="justify" aria-label="Justify">
          <AlignJustify size={14} />
        </SegmentedControlItem>
      </SegmentedControl>
    );
  },
};

/**
 * Two-option toggle for simple binary choices.
 */
export const TwoOptions: Story = {
  render: () => {
    const [value, setValue] = useState("on");

    return (
      <SegmentedControl
        value={value}
        onValueChange={setValue}
        aria-label="Toggle"
      >
        <SegmentedControlItem value="on">On</SegmentedControlItem>
        <SegmentedControlItem value="off">Off</SegmentedControlItem>
      </SegmentedControl>
    );
  },
};

/**
 * Individual item can be disabled while control is enabled.
 */
export const WithDisabledItem: Story = {
  render: () => {
    const [value, setValue] = useState("grid");

    return (
      <SegmentedControl
        value={value}
        onValueChange={setValue}
        aria-label="View mode"
      >
        <SegmentedControlItem value="grid" aria-label="Grid view">
          <LayoutGrid size={16} />
        </SegmentedControlItem>
        <SegmentedControlItem value="list" aria-label="List view">
          <List size={16} />
        </SegmentedControlItem>
        <SegmentedControlItem value="table" aria-label="Table view (premium)" disabled>
          <Table size={16} />
        </SegmentedControlItem>
      </SegmentedControl>
    );
  },
};

/**
 * Keyboard navigation demonstration - use Arrow keys, Home, End.
 */
export const KeyboardNavigation: Story = {
  render: () => (
    <div className="flex flex-col gap-4 items-center">
      <SegmentedControlDemo />
      <p className="text-sm text-neutral-11 text-center max-w-xs">
        Focus the control and use Arrow keys to navigate, Home/End to jump to first/last,
        Enter/Space to select.
      </p>
    </div>
  ),
};
