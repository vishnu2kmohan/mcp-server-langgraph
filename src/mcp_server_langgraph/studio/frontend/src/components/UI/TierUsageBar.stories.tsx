/**
 * TierUsageBar Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { TierUsageBar } from "./TierUsageBar";

const meta: Meta<typeof TierUsageBar> = {
  title: "Design System/TierUsageBar",
  component: TierUsageBar,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Tier-based usage indicator bar.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof TierUsageBar>;

export const AllLevels: Story = {
  render: () => (
    <div className="space-y-4 max-w-md">
      <TierUsageBar current={25} max={100} label="Storage" tier="shared" />
      <TierUsageBar current={75} max={100} label="API Calls" tier="hybrid" />
      <TierUsageBar current={95} max={100} label="Bandwidth" tier="dedicated" />
    </div>
  ),
};

export const Unlimited: Story = {
  args: {
    current: 500,
    max: -1,
    label: "Requests",
    tier: "dedicated",
  },
};

export const Compact: Story = {
  args: {
    current: 50,
    max: 100,
    label: "Usage",
    variant: "compact",
  },
};
