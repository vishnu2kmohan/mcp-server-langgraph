/**
 * SkillCard Component Stories
 *
 * Storybook stories for the skill card component.
 * Showcases all states: default, installed, installing, and with tags.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { SkillCard } from "./SkillCard";
import type { SkillMetadata } from "../../types/skills";

const mockSkill: SkillMetadata = {
  name: "web-research",
  description:
    "Search the web for information and retrieve relevant content for your queries.",
  version: "1.2.0",
  author: "Anthropic",
  tags: ["research", "web", "search"],
};

const meta: Meta<typeof SkillCard> = {
  title: "Skills/SkillCard",
  component: SkillCard,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "A card component that displays skill information in the marketplace browser. Shows skill name, description, version, tags, and install/installed status.",
      },
    },
  },
  argTypes: {
    skill: {
      description: "Skill metadata to display",
    },
    isInstalled: {
      control: "boolean",
      description: "Whether the skill is already installed",
    },
    isInstalling: {
      control: "boolean",
      description: "Whether installation is in progress",
    },
    onInstall: {
      description: "Callback when install button is clicked",
    },
    onViewDetails: {
      description: "Callback when card is clicked for details",
    },
  },
  decorators: [
    (Story) => (
      <div style={{ width: "320px" }}>
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof SkillCard>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    skill: mockSkill,
    isInstalled: false,
    isInstalling: false,
    onInstall: () => console.log("Install clicked"),
    onViewDetails: (skill) => console.log("View details:", skill.name),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default state showing an uninstalled skill with Install button.",
      },
    },
  },
};

export const Installed: Story = {
  args: {
    skill: mockSkill,
    isInstalled: true,
    isInstalling: false,
    onInstall: () => console.log("Install clicked"),
    onViewDetails: (skill) => console.log("View details:", skill.name),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Installed state showing the Installed badge instead of Install button.",
      },
    },
  },
};

export const Installing: Story = {
  args: {
    skill: mockSkill,
    isInstalled: false,
    isInstalling: true,
    onInstall: () => console.log("Install clicked"),
    onViewDetails: (skill) => console.log("View details:", skill.name),
  },
  parameters: {
    docs: {
      description: {
        story: "Installing state with disabled button and loading spinner.",
      },
    },
  },
};

// =============================================================================
// Content Variations
// =============================================================================

export const LongDescription: Story = {
  args: {
    skill: {
      ...mockSkill,
      name: "advanced-data-analysis",
      description:
        "Analyze complex datasets, generate statistical insights, create visualizations, and provide actionable recommendations based on your data. Supports CSV, JSON, Excel, and database connections.",
    },
    isInstalled: false,
    isInstalling: false,
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Skill with a longer description to show text handling.",
      },
    },
  },
};

export const ManyTags: Story = {
  args: {
    skill: {
      ...mockSkill,
      tags: ["research", "web", "search", "api", "data", "automation"],
    },
    isInstalled: false,
    isInstalling: false,
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Skill with many tags (only first 3 are displayed).",
      },
    },
  },
};

export const NoTags: Story = {
  args: {
    skill: {
      ...mockSkill,
      tags: [],
    },
    isInstalled: false,
    isInstalling: false,
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Skill without any tags.",
      },
    },
  },
};

export const CommunityAuthor: Story = {
  args: {
    skill: {
      ...mockSkill,
      name: "code-review",
      description: "Review and analyze code for improvements and issues",
      author: "Community",
    },
    isInstalled: false,
    isInstalling: false,
    onInstall: () => console.log("Install clicked"),
  },
  parameters: {
    docs: {
      description: {
        story: "Skill from a community author.",
      },
    },
  },
};

// =============================================================================
// Grid Layout
// =============================================================================

export const InGrid: Story = {
  args: {
    skill: mockSkill,
    isInstalled: false,
    isInstalling: false,
    onInstall: () => console.log("Install clicked"),
  },
  decorators: [
    (Story) => (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 320px)",
          gap: "16px",
        }}
      >
        <Story />
        <SkillCard
          skill={{
            name: "code-review",
            description: "Review and analyze code for improvements",
            version: "2.1.0",
            author: "Community",
            tags: ["development", "code"],
          }}
          isInstalled={true}
          isInstalling={false}
          onInstall={() => {}}
        />
        <SkillCard
          skill={{
            name: "data-analysis",
            description: "Analyze datasets and generate insights",
            version: "1.0.0",
            author: "Anthropic",
            tags: ["data", "analytics"],
          }}
          isInstalled={false}
          isInstalling={true}
          onInstall={() => {}}
        />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        story:
          "Multiple SkillCards displayed in a grid layout showing different states.",
      },
    },
  },
};
