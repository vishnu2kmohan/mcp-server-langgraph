/**
 * SearchInput Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { SearchInput } from "./SearchInput";

const meta: Meta<typeof SearchInput> = {
  title: "Design System/SearchInput",
  component: SearchInput,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "A debounced search input with clear button.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof SearchInput>;

export const Default: Story = {
  render: function Render() {
    const [value, setValue] = useState("");
    return (
      <SearchInput value={value} onChange={setValue} placeholder="Search..." />
    );
  },
};

export const WithValue: Story = {
  render: function Render() {
    const [value, setValue] = useState("example search");
    return <SearchInput value={value} onChange={setValue} />;
  },
};
