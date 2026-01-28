/**
 * InstallDialog Component Stories
 *
 * Storybook stories for the skill installation confirmation dialog.
 * Showcases confirmation flow and loading states.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { InstallDialog } from "./InstallDialog";
import type { SkillMetadata } from "../../types/skills";

const mockSkill: SkillMetadata = {
  name: "web-research",
  description: "Search the web for information and retrieve relevant content.",
  version: "1.2.0",
  author: "Anthropic",
  tags: ["research", "web"],
};

const meta: Meta<typeof InstallDialog> = {
  title: "Skills/InstallDialog",
  component: InstallDialog,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "A confirmation dialog for skill installation. Shows skill name and version, and provides Cancel and Install actions.",
      },
    },
  },
  argTypes: {
    skill: {
      description: "Skill to install (null when closed)",
    },
    isOpen: {
      control: "boolean",
      description: "Whether the dialog is open",
    },
    isInstalling: {
      control: "boolean",
      description: "Whether installation is in progress",
    },
    onClose: {
      description: "Callback when Cancel is clicked",
    },
    onConfirm: {
      description: "Callback when Install is confirmed",
    },
  },
};

export default meta;
type Story = StoryObj<typeof InstallDialog>;

// =============================================================================
// Basic States
// =============================================================================

export const Open: Story = {
  args: {
    skill: mockSkill,
    isOpen: true,
    isInstalling: false,
    onClose: () => console.log("Cancel clicked"),
    onConfirm: () => console.log("Install confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Open dialog prompting user to confirm installation.",
      },
    },
  },
};

export const Installing: Story = {
  args: {
    skill: mockSkill,
    isOpen: true,
    isInstalling: true,
    onClose: () => console.log("Cancel clicked"),
    onConfirm: () => console.log("Install confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Dialog during installation with disabled buttons and loading spinner.",
      },
    },
  },
};

export const Closed: Story = {
  args: {
    skill: mockSkill,
    isOpen: false,
    isInstalling: false,
    onClose: () => console.log("Cancel clicked"),
    onConfirm: () => console.log("Install confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog in closed state (renders nothing).",
      },
    },
  },
};

// =============================================================================
// Different Skills
// =============================================================================

export const CommunitySkill: Story = {
  args: {
    skill: {
      name: "code-review",
      description: "Review and analyze code for improvements",
      version: "2.1.0",
      author: "Community",
      tags: ["development"],
    },
    isOpen: true,
    isInstalling: false,
    onClose: () => console.log("Cancel clicked"),
    onConfirm: () => console.log("Install confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Installation confirmation for a community skill.",
      },
    },
  },
};
