/**
 * StatusFilter Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { StatusFilter, type StatusOption } from "./StatusFilter";

const meta: Meta<typeof StatusFilter> = {
  title: "Design System/StatusFilter",
  component: StatusFilter,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Status dropdown filter.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof StatusFilter>;

const options: StatusOption[] = [
  { value: "active", label: "Active" },
  { value: "pending", label: "Pending" },
  { value: "completed", label: "Completed" },
];

export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState<string | null>(null);
    return <StatusFilter options={options} value={value} onChange={setValue} />;
  },
};

export const WithSelection: Story = {
  render: function Render() {
    const [value, setValue] = useState<string | null>("active");
    return <StatusFilter options={options} value={value} onChange={setValue} />;
  },
};
