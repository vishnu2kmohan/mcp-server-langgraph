/**
 * ConfidenceIndicator Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ConfidenceIndicator } from "./ConfidenceIndicator";

const meta: Meta<typeof ConfidenceIndicator> = {
  title: "Design System/ConfidenceIndicator",
  component: ConfidenceIndicator,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "AI confidence score display.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ConfidenceIndicator>;

export const AllLevels: Story = {
  render: () => (
    <div className="space-y-2">
      <ConfidenceIndicator score={0.95} label="High confidence" />
      <ConfidenceIndicator score={0.75} label="Medium confidence" />
      <ConfidenceIndicator score={0.45} label="Low confidence" />
    </div>
  ),
};

export const Sizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <ConfidenceIndicator score={0.85} size="sm" />
      <ConfidenceIndicator score={0.85} size="md" />
      <ConfidenceIndicator score={0.85} size="lg" />
    </div>
  ),
};

export const DecimalFormat: Story = {
  args: {
    score: 0.87,
    showDecimal: true,
  },
};
