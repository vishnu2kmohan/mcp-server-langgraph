/**
 * RiskBadge Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { RiskBadge } from "./RiskBadge";

const meta: Meta<typeof RiskBadge> = {
  title: "Design System/RiskBadge",
  component: RiskBadge,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Risk level display with semantic colors.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof RiskBadge>;

export const AllLevels: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <RiskBadge level="critical" />
      <RiskBadge level="high" />
      <RiskBadge level="medium" />
      <RiskBadge level="low" />
    </div>
  ),
};

export const Sizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <RiskBadge level="high" size="sm" />
      <RiskBadge level="high" size="md" />
      <RiskBadge level="high" size="lg" />
    </div>
  ),
};

export const WithIcons: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <RiskBadge level="critical" showIcon />
      <RiskBadge level="high" showIcon />
      <RiskBadge level="medium" showIcon />
      <RiskBadge level="low" showIcon />
    </div>
  ),
};
