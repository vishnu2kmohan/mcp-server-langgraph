/**
 * StatusBadge Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { StatusBadge } from "./StatusBadge";

const meta: Meta<typeof StatusBadge> = {
  title: "Design System/StatusBadge",
  component: StatusBadge,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Semantic status badges with design system colors.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof StatusBadge>;

export const AllStatuses: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <StatusBadge status="success">Success</StatusBadge>
      <StatusBadge status="warning">Warning</StatusBadge>
      <StatusBadge status="error">Error</StatusBadge>
      <StatusBadge status="info">Info</StatusBadge>
      <StatusBadge status="neutral">Neutral</StatusBadge>
    </div>
  ),
};
