/**
 * ContextMenu Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ContextMenu } from "./ContextMenu";

const meta: Meta<typeof ContextMenu> = {
  title: "Design System/ContextMenu",
  component: ContextMenu,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Right-click context menu.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ContextMenu>;

export const Default: Story = {
  render: () => (
    <div className="p-8">
      <p className="text-neutral-10 mb-4">Right-click on the area below:</p>
      <ContextMenu
        items={[
          { id: "edit", label: "Edit", action: () => console.log("Edit") },
          {
            id: "delete",
            label: "Delete",
            action: () => console.log("Delete"),
          },
          { id: "copy", label: "Copy", action: () => console.log("Copy") },
        ]}
      >
        <div className="w-64 h-32 border-2 border-dashed border-neutral-5 rounded-lg flex items-center justify-center">
          Right-click here
        </div>
      </ContextMenu>
    </div>
  ),
};

export const WithDisabledItems: Story = {
  render: () => (
    <div className="p-8">
      <ContextMenu
        items={[
          { id: "edit", label: "Edit", action: () => console.log("Edit") },
          {
            id: "delete",
            label: "Delete",
            action: () => console.log("Delete"),
            disabled: true,
          },
          { id: "copy", label: "Copy", action: () => console.log("Copy") },
        ]}
      >
        <div className="w-64 h-32 border-2 border-dashed border-neutral-5 rounded-lg flex items-center justify-center">
          Right-click here
        </div>
      </ContextMenu>
    </div>
  ),
};
