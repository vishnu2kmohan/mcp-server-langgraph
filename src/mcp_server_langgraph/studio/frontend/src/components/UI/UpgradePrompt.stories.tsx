/**
 * UpgradePrompt Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { UpgradePrompt } from "./UpgradePrompt";

const meta: Meta<typeof UpgradePrompt> = {
  title: "Design System/UpgradePrompt",
  component: UpgradePrompt,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Tier upgrade call-to-action prompt.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof UpgradePrompt>;

export const Default: Story = {
  args: {
    show: true,
    feature: "Advanced Analytics",
    currentTier: "shared",
    targetTier: "hybrid",
    currentUsage: 90,
    maxUsage: 100,
  },
};

export const ToDedicated: Story = {
  args: {
    show: true,
    feature: "Custom Integrations",
    currentTier: "hybrid",
    targetTier: "dedicated",
  },
};

export const Hidden: Story = {
  args: {
    show: false,
    feature: "Test Feature",
    targetTier: "hybrid",
  },
};
