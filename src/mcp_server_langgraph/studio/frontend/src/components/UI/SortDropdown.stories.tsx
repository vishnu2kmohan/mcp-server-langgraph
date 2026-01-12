/**
 * SortDropdown Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { SortDropdown, type SortOption, type SortOrder } from "./SortDropdown";

const meta: Meta<typeof SortDropdown> = {
  title: "Design System/SortDropdown",
  component: SortDropdown,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Sort field and order dropdown.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof SortDropdown>;

const options: SortOption[] = [
  { value: "name", label: "Name" },
  { value: "date", label: "Date" },
  { value: "size", label: "Size" },
];

export const Default: Story = {
  render: function Render() {
    const [sortBy, setSortBy] = useState("name");
    const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
    return (
      <SortDropdown
        options={options}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onChange={(newSortBy, newSortOrder) => {
          setSortBy(newSortBy);
          setSortOrder(newSortOrder);
        }}
      />
    );
  },
};

export const WithLabel: Story = {
  render: function Render() {
    const [sortBy, setSortBy] = useState("date");
    const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
    return (
      <SortDropdown
        options={options}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onChange={(newSortBy, newSortOrder) => {
          setSortBy(newSortBy);
          setSortOrder(newSortOrder);
        }}
        label="Sort by"
      />
    );
  },
};
