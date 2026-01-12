/**
 * Tooltip Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Tooltip } from "./Tooltip";
import { Button } from "./Button";

const meta: Meta<typeof Tooltip> = {
  title: "Design System/Tooltip",
  component: Tooltip,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Tooltip for additional information on hover.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const Default: Story = {
  render: () => (
    <div className="p-8">
      <Tooltip content="This is a tooltip">
        <Button>Hover me</Button>
      </Tooltip>
    </div>
  ),
};

export const Positions: Story = {
  render: () => (
    <div className="flex gap-4 p-8">
      <Tooltip content="Top tooltip" position="top">
        <Button>Top</Button>
      </Tooltip>
      <Tooltip content="Bottom tooltip" position="bottom">
        <Button>Bottom</Button>
      </Tooltip>
      <Tooltip content="Left tooltip" position="left">
        <Button>Left</Button>
      </Tooltip>
      <Tooltip content="Right tooltip" position="right">
        <Button>Right</Button>
      </Tooltip>
    </div>
  ),
};
