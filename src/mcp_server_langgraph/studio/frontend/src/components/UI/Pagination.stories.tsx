/**
 * Pagination Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { PagePagination } from "./Pagination";

const meta: Meta<typeof PagePagination> = {
  title: "Design System/Pagination",
  component: PagePagination,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Page-based pagination component.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof PagePagination>;

export const Default: Story = {
  render: function Render() {
    const [page, setPage] = useState(1);
    return (
      <PagePagination
        currentPage={page}
        totalPages={10}
        onPageChange={setPage}
      />
    );
  },
};

export const ManyPages: Story = {
  render: function Render() {
    const [page, setPage] = useState(50);
    return (
      <PagePagination
        currentPage={page}
        totalPages={100}
        onPageChange={setPage}
      />
    );
  },
};
