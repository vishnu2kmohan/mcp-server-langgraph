/**
 * CursorPagination Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { CursorPagination } from "./CursorPagination";

const meta: Meta<typeof CursorPagination> = {
  title: "Design System/CursorPagination",
  component: CursorPagination,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Cursor-based pagination for infinite lists.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof CursorPagination>;

export const Default: Story = {
  args: {
    hasNextPage: true,
    hasPreviousPage: true,
    onNextPage: () => console.log("Next"),
    onPreviousPage: () => console.log("Previous"),
  },
};

export const FirstPage: Story = {
  args: {
    hasNextPage: true,
    hasPreviousPage: false,
    onNextPage: () => console.log("Next"),
    onPreviousPage: () => console.log("Previous"),
  },
};

export const LastPage: Story = {
  args: {
    hasNextPage: false,
    hasPreviousPage: true,
    onNextPage: () => console.log("Next"),
    onPreviousPage: () => console.log("Previous"),
  },
};

export const WithCounts: Story = {
  args: {
    hasNextPage: true,
    hasPreviousPage: true,
    onNextPage: () => console.log("Next"),
    onPreviousPage: () => console.log("Previous"),
    itemCount: 25,
    totalCount: 100,
  },
};

export const Loading: Story = {
  args: {
    hasNextPage: true,
    hasPreviousPage: true,
    onNextPage: () => console.log("Next"),
    onPreviousPage: () => console.log("Previous"),
    isLoading: true,
  },
};
