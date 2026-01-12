/**
 * ErrorState Component Stories
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ErrorState } from "./ErrorState";

const meta: Meta<typeof ErrorState> = {
  title: "Design System/ErrorState",
  component: ErrorState,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component: "Standardized error display component.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof ErrorState>;

export const Default: Story = {
  args: {
    title: "Something went wrong",
    message: "An unexpected error occurred. Please try again.",
  },
};

export const WithRetry: Story = {
  args: {
    title: "Failed to load data",
    message: "Unable to fetch the requested data.",
    onRetry: () => console.log("Retry clicked"),
    retryText: "Try Again",
  },
};

export const Compact: Story = {
  args: {
    title: "Error",
    message: "Something went wrong.",
    variant: "compact",
  },
};

export const Fullscreen: Story = {
  args: {
    title: "Page Not Found",
    message: "The requested page could not be found.",
    variant: "fullscreen",
    onRetry: () => console.log("Go Home"),
    retryText: "Go Home",
  },
};
