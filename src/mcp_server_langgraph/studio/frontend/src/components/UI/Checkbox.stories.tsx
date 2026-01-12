/**
 * Checkbox Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Checkbox } from "./Checkbox";

const meta: Meta<typeof Checkbox> = {
  title: "Design System/Checkbox",
  component: Checkbox,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component:
          "A checkbox component with accessible controls. Supports labels, descriptions, and indeterminate state.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof Checkbox>;

/**
 * Default checkbox in unchecked state
 */
export const Default: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return <Checkbox checked={checked} onChange={setChecked} />;
  },
};

/**
 * Checkbox in checked state
 */
export const Checked: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(true);
    return <Checkbox checked={checked} onChange={setChecked} />;
  },
};

/**
 * Checkbox with label
 */
export const WithLabel: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return (
      <Checkbox
        checked={checked}
        onChange={setChecked}
        label="Accept terms and conditions"
      />
    );
  },
};

/**
 * Checkbox with label and description
 */
export const WithDescription: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return (
      <Checkbox
        checked={checked}
        onChange={setChecked}
        label="Marketing emails"
        description="Receive occasional updates about new features and promotions"
      />
    );
  },
};

/**
 * Disabled checkbox
 */
export const Disabled: Story = {
  render: function Render() {
    const [checked1, setChecked1] = useState(false);
    const [checked2, setChecked2] = useState(true);
    return (
      <div className="space-y-4">
        <Checkbox
          checked={checked1}
          onChange={setChecked1}
          disabled
          label="Disabled (unchecked)"
        />
        <Checkbox
          checked={checked2}
          onChange={setChecked2}
          disabled
          label="Disabled (checked)"
        />
      </div>
    );
  },
};

/**
 * Indeterminate state (for parent checkboxes)
 */
export const Indeterminate: Story = {
  render: function Render() {
    const [checked, setChecked] = useState(false);
    return (
      <Checkbox
        checked={checked}
        onChange={setChecked}
        indeterminate={!checked}
        label="Select all (indeterminate when not all selected)"
      />
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
          <Checkbox checked={sm} onChange={setSm} size="sm" />
          <span className="text-sm text-neutral-600">Small</span>
        </div>
        <div className="flex items-center gap-4">
          <Checkbox checked={md} onChange={setMd} size="md" />
          <span className="text-sm text-neutral-600">Medium (default)</span>
        </div>
        <div className="flex items-center gap-4">
          <Checkbox checked={lg} onChange={setLg} size="lg" />
          <span className="text-sm text-neutral-600">Large</span>
        </div>
      </div>
    );
  },
};

/**
 * Settings form example
 */
export const SettingsExample: Story = {
  render: function Render() {
    const [notifications, setNotifications] = useState(true);
    const [marketing, setMarketing] = useState(false);
    const [analytics, setAnalytics] = useState(true);

    return (
      <div className="max-w-md space-y-4 p-4 bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          Email Preferences
        </h3>
        <div className="space-y-3">
          <Checkbox
            checked={notifications}
            onChange={setNotifications}
            label="Product notifications"
            description="Receive alerts about your account and usage"
          />
          <Checkbox
            checked={marketing}
            onChange={setMarketing}
            label="Marketing emails"
            description="Occasional updates about new features"
          />
          <Checkbox
            checked={analytics}
            onChange={setAnalytics}
            label="Usage analytics"
            description="Help improve the product with anonymous data"
          />
        </div>
      </div>
    );
  },
};
