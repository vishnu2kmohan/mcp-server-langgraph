/**
 * FilterChips Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { FilterChips, type FilterOption } from "./FilterChips";

const meta: Meta<typeof FilterChips> = {
  title: "Design System/FilterChips",
  component: FilterChips,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Clickable filter chips for enum filtering.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof FilterChips>;

const options: FilterOption[] = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "pending", label: "Pending" },
  { value: "completed", label: "Completed" },
];

export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState<string | null>("all");
    return <FilterChips options={options} value={value} onChange={setValue} />;
  },
};

export const WithColors: Story = {
  render: function Render() {
    const [value, setValue] = useState<string | null>("active");
    const coloredOptions: FilterOption[] = [
      { value: "all", label: "All" },
      { value: "active", label: "Active", color: "success" },
      { value: "pending", label: "Pending", color: "warning" },
      { value: "failed", label: "Failed", color: "error" },
    ];
    return (
      <FilterChips options={coloredOptions} value={value} onChange={setValue} />
    );
  },
};
