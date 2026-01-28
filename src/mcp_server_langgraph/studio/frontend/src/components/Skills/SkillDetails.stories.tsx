/**
 * SkillDetails Modal Stories
 *
 * Storybook stories for the skill details modal component.
 * Showcases different skill information and states.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { SkillDetails } from "./SkillDetails";
import type { SkillMetadata } from "../../types/skills";

const mockSkill: SkillMetadata = {
  name: "web-research",
  description:
    "Search the web for information and retrieve relevant content for your queries. Supports advanced search operators, filters, and can extract structured data from web pages.",
  version: "1.2.0",
  author: "Anthropic",
  tags: ["research", "web", "search", "data"],
};

const meta: Meta<typeof SkillDetails> = {
  title: "Skills/SkillDetails",
  component: SkillDetails,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "A modal dialog that displays full skill information including name, description, author, version, and tags. Provides install action for uninstalled skills.",
      },
    },
  },
  argTypes: {
    skill: {
      description: "Skill metadata to display (null when closed)",
    },
    isOpen: {
      control: "boolean",
      description: "Whether the modal is open",
    },
    isInstalled: {
      control: "boolean",
      description: "Whether the skill is already installed",
    },
    isInstalling: {
      control: "boolean",
      description: "Whether installation is in progress",
    },
    onClose: {
      description: "Callback when modal is closed",
    },
    onInstall: {
      description: "Callback when install button is clicked",
    },
  },
};

export default meta;
type Story = StoryObj<typeof SkillDetails>;

// =============================================================================
// Basic States
// =============================================================================

export const Open: Story = {
  args: {
    skill: mockSkill,
    isOpen: true,
    isInstalled: false,
    isInstalling: false,
    onClose: () => console.log("Close clicked"),
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Open modal showing skill details with Install button.",
      },
    },
  },
};

export const Installed: Story = {
  args: {
    skill: mockSkill,
    isOpen: true,
    isInstalled: true,
    isInstalling: false,
    onClose: () => console.log("Close clicked"),
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Modal showing installed skill with Installed badge.",
      },
    },
  },
};

export const Installing: Story = {
  args: {
    skill: mockSkill,
    isOpen: true,
    isInstalled: false,
    isInstalling: true,
    onClose: () => console.log("Close clicked"),
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Modal during installation with loading state.",
      },
    },
  },
};

export const Closed: Story = {
  args: {
    skill: mockSkill,
    isOpen: false,
    isInstalled: false,
    isInstalling: false,
    onClose: () => console.log("Close clicked"),
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Modal in closed state (renders nothing).",
      },
    },
  },
};

// =============================================================================
// Content Variations
// =============================================================================

export const CommunitySkill: Story = {
  args: {
    skill: {
      name: "code-review",
      description:
        "Automatically review code for potential issues, suggest improvements, and ensure adherence to best practices. Supports multiple programming languages including JavaScript, Python, Go, and Rust.",
      version: "2.1.0",
      author: "Community",
      tags: ["development", "code", "review", "quality", "automation"],
    },
    isOpen: true,
    isInstalled: false,
    isInstalling: false,
    onClose: () => console.log("Close clicked"),
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Community-authored skill with many tags.",
      },
    },
  },
};
