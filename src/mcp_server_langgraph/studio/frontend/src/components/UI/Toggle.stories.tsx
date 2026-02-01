/**
 * Toggle Component Stories
 *
 * Storybook documentation for the Toggle component.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Toggle } from "./Toggle";

const meta: Meta<typeof Toggle> = {
  title: "Design System/Toggle",
  component: Toggle,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component:
          "A switch/toggle component with accessible controls. Supports multiple sizes, labels, and descriptions.",
      },
    },
  },
  argTypes: {
    checked: {
      control: "boolean",
      description: "Whether the toggle is checked",
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
      description: "Toggle size",
    },
    label: {
      control: "text",
      description: "Optional label text",
    },
    description: {
      control: "text",
      description: "Optional description text",
    },
    disabled: {
      control: "boolean",
      description: "Whether the toggle is disabled",
    },
  },
};

export default meta;
type Story = StoryObj<typeof Toggle>;

/**
 * Default toggle in unchecked state
 */
export const Default: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return <Toggle checked={checked} onChange={setChecked} />;
  },
};

/**
 * Toggle in checked state
 */
export const Checked: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(true);
    return <Toggle checked={checked} onChange={setChecked} />;
  },
};

/**
 * Toggle with label
 */
export const WithLabel: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return (
      <Toggle
        checked={checked}
        onChange={setChecked}
        label="Enable notifications"
      />
    );
  },
};

/**
 * Toggle with label and description
 */
export const WithDescription: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return (
      <Toggle
        checked={checked}
        onChange={setChecked}
        label="Email notifications"
        description="Receive email updates about your account activity"
      />
    );
  },
};

/**
 * Disabled toggle
 */
export const Disabled: Story = {
  render: function Render() {
    const [checked1, setChecked1] = useState(false);
    const [checked2, setChecked2] = useState(true);
    return (
      <div className="space-y-4">
        <Toggle
          checked={checked1}
          onChange={setChecked1}
          disabled
          label="Disabled (off)"
        />
        <Toggle
          checked={checked2}
          onChange={setChecked2}
          disabled
          label="Disabled (on)"
        />
      </div>
    );
  },
};

/**
 * All sizes comparison
 */
export const Sizes: Story = {
  render: function Render() {
    const [sm, setSm] = useState(true);
    const [md, setMd] = useState(true);
    const [lg, setLg] = useState(true);
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Toggle checked={sm} onChange={setSm} size="sm" />
          <span className="text-sm text-neutral-11">Small</span>
        </div>
        <div className="flex items-center gap-4">
          <Toggle checked={md} onChange={setMd} size="md" />
          <span className="text-sm text-neutral-11">Medium (default)</span>
        </div>
        <div className="flex items-center gap-4">
          <Toggle checked={lg} onChange={setLg} size="lg" />
          <span className="text-sm text-neutral-11">Large</span>
        </div>
      </div>
    );
  },
};

/**
 * Settings panel example
 */
export const SettingsExample: Story = {
  render: () => {
    const [darkMode, setDarkMode] = useState(false);
    const [notifications, setNotifications] = useState(true);
    const [analytics, setAnalytics] = useState(false);

    return (
      <div className="max-w-md space-y-6 p-4 bg-neutral-1 rounded-lg border border-neutral-5">
        <h3 className="text-lg font-semibold text-neutral-12">Settings</h3>
        <div className="space-y-4">
          <Toggle
            checked={darkMode}
            onChange={setDarkMode}
            label="Dark mode"
            description="Use dark theme across the application"
          />
          <Toggle
            checked={notifications}
            onChange={setNotifications}
            label="Push notifications"
            description="Receive push notifications for important updates"
          />
          <Toggle
            checked={analytics}
            onChange={setAnalytics}
            label="Usage analytics"
            description="Help improve the product by sharing anonymous usage data"
          />
        </div>
      </div>
    );
  },
};

/**
 * Dark mode demonstration
 */
export const DarkMode: Story = {
  render: function Render() {
    const [unchecked, setUnchecked] = useState(false);
    const [checked, setChecked] = useState(true);
    const [disabled, setDisabled] = useState(false);
    return (
      <div className="dark bg-neutral-2 p-6 rounded-lg">
        <div className="space-y-4">
          <Toggle
            checked={unchecked}
            onChange={setUnchecked}
            label="Unchecked"
          />
          <Toggle checked={checked} onChange={setChecked} label="Checked" />
          <Toggle
            checked={disabled}
            onChange={setDisabled}
            disabled
            label="Disabled"
          />
        </div>
      </div>
    );
  },
};
