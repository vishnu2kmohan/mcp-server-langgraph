/**
 * InstalledContent Component Stories
 *
 * Storybook stories for the installed skills tab component.
 * Showcases skill list, uninstall actions, and empty state.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { InstalledContent } from "./InstalledContent";

const meta: Meta<typeof InstalledContent> = {
  title: "Skills/InstalledContent",
  component: InstalledContent,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Installed skills tab displaying a list of locally installed skills with uninstall actions.",
      },
    },
  },
  argTypes: {
    installedSkills: {
      description: "List of installed skill names",
    },
    isUninstalling: {
      control: "boolean",
      description: "Whether uninstallation is in progress",
    },
  },
};

export default meta;
type Story = StoryObj<typeof InstalledContent>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    installedSkills: ["web-research", "code-review", "data-analysis"],
    onUninstall: (name) => console.log("Uninstall:", name),
    isUninstalling: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Default view with three installed skills.",
      },
    },
  },
};

export const SingleSkill: Story = {
  args: {
    installedSkills: ["web-research"],
    onUninstall: (name) => console.log("Uninstall:", name),
    isUninstalling: false,
  },
  parameters: {
    docs: {
      description: {
        story: "View with a single installed skill.",
      },
    },
  },
};

export const Empty: Story = {
  args: {
    installedSkills: [],
    onUninstall: () => {},
    isUninstalling: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Empty state when no skills are installed.",
      },
    },
  },
};

export const Uninstalling: Story = {
  args: {
    installedSkills: ["web-research", "code-review"],
    onUninstall: () => {},
    isUninstalling: true,
  },
  parameters: {
    docs: {
      description: {
        story: "State during skill uninstallation with disabled buttons.",
      },
    },
  },
};

export const ManySkills: Story = {
  args: {
    installedSkills: [
      "web-research",
      "code-review",
      "data-analysis",
      "document-generation",
      "api-testing",
      "image-processing",
      "text-summarization",
      "translation",
    ],
    onUninstall: (name) => console.log("Uninstall:", name),
    isUninstalling: false,
  },
  parameters: {
    docs: {
      description: {
        story: "View with many installed skills.",
      },
    },
  },
};
