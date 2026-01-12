/**
 * BulkActionBar Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { BulkActionBar } from "./BulkActionBar";

const meta: Meta<typeof BulkActionBar> = {
  title: "Design System/BulkActionBar",
  component: BulkActionBar,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Bulk action toolbar for multi-select operations.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof BulkActionBar>;

export const Default: Story = {
  args: {
    selectedCount: 5,
    onClearSelection: () => console.log("Clear selection"),
    onDelete: () => console.log("Delete"),
  },
};

export const WithCustomActions: Story = {
  args: {
    selectedCount: 3,
    onClearSelection: () => console.log("Clear selection"),
    onDelete: () => console.log("Delete"),
    customActions: [
      { label: "Archive", onClick: () => console.log("Archive") },
      { label: "Export", onClick: () => console.log("Export") },
    ],
  },
};
