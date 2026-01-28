/**
 * UpdatesContent Component Stories
 *
 * Storybook stories for the skill updates tab component.
 * Showcases available updates and up-to-date state.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { UpdatesContent } from "./UpdatesContent";

const meta: Meta<typeof UpdatesContent> = {
  title: "Skills/UpdatesContent",
  component: UpdatesContent,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Skill updates tab displaying available updates with apply all action.",
      },
    },
  },
  argTypes: {
    updates: {
      description: "List of available updates",
    },
    isApplying: {
      control: "boolean",
      description: "Whether updates are being applied",
    },
  },
};

export default meta;
type Story = StoryObj<typeof UpdatesContent>;

// =============================================================================
// Basic States
// =============================================================================

export const NoUpdates: Story = {
  args: {
    updates: [],
    onApplyAll: () => console.log("Apply all updates"),
    isApplying: false,
  },
  parameters: {
    docs: {
      description: {
        story: "All skills are up to date - success state.",
      },
    },
  },
};

export const SingleUpdate: Story = {
  args: {
    updates: [
      {
        name: "web-research",
        currentVersion: "1.2.0",
        newVersion: "1.3.0",
      },
    ],
    onApplyAll: () => console.log("Apply all updates"),
    isApplying: false,
  },
  parameters: {
    docs: {
      description: {
        story: "One update available.",
      },
    },
  },
};

export const MultipleUpdates: Story = {
  args: {
    updates: [
      {
        name: "web-research",
        currentVersion: "1.2.0",
        newVersion: "1.3.0",
      },
      {
        name: "code-review",
        currentVersion: "2.1.0",
        newVersion: "3.0.0",
      },
      {
        name: "data-analysis",
        currentVersion: "1.0.0",
        newVersion: "1.1.0",
      },
    ],
    onApplyAll: () => console.log("Apply all updates"),
    isApplying: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Multiple updates available.",
      },
    },
  },
};

export const Applying: Story = {
  args: {
    updates: [
      {
        name: "web-research",
        currentVersion: "1.2.0",
        newVersion: "1.3.0",
      },
    ],
    onApplyAll: () => {},
    isApplying: true,
  },
  parameters: {
    docs: {
      description: {
        story: "State while applying updates with loading spinner.",
      },
    },
  },
};
