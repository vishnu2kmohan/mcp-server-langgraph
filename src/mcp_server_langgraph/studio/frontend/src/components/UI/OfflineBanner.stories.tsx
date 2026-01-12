/**
 * OfflineBanner Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { OfflineBanner } from "./OfflineBanner";

const meta: Meta<typeof OfflineBanner> = {
  title: "Design System/OfflineBanner",
  component: OfflineBanner,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "PWA offline indicator banner.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof OfflineBanner>;

export const Default: Story = {
  render: () => <OfflineBanner />,
};
