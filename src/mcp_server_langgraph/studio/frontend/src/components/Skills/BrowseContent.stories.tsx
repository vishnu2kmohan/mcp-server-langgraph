/**
 * BrowseContent Component Stories
 *
 * Storybook stories for the browse marketplace skills tab component.
 * Showcases skill grid, pagination, empty states, and error handling.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { BrowseContent } from "./BrowseContent";
import type { SkillMetadata } from "../../types/skills";

const mockSkills: SkillMetadata[] = [
  {
    name: "web-research",
    description:
      "Search the web for information and retrieve relevant content.",
    version: "1.2.0",
    author: "Anthropic",
    tags: ["research", "web"],
  },
  {
    name: "code-review",
    description: "Review and analyze code for improvements and issues.",
    version: "2.1.0",
    author: "Community",
    tags: ["development", "code"],
  },
  {
    name: "data-analysis",
    description: "Analyze datasets and generate statistical insights.",
    version: "1.0.0",
    author: "Anthropic",
    tags: ["data", "analytics"],
  },
  {
    name: "document-generation",
    description: "Generate professional documents from templates.",
    version: "1.5.0",
    author: "Enterprise",
    tags: ["docs", "automation"],
  },
  {
    name: "api-testing",
    description: "Test API endpoints and validate responses.",
    version: "0.9.0",
    author: "Community",
    tags: ["testing", "api"],
  },
  {
    name: "image-processing",
    description: "Process and transform images with various filters.",
    version: "2.0.0",
    author: "Anthropic",
    tags: ["images", "media"],
  },
];

const meta: Meta<typeof BrowseContent> = {
  title: "Skills/BrowseContent",
  component: BrowseContent,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Browse marketplace skills tab displaying a grid of available skills with install actions, pagination, and error handling.",
      },
    },
  },
  argTypes: {
    skills: {
      description: "List of skills to display",
    },
    installedSkills: {
      description: "Names of already installed skills",
    },
    total: {
      description: "Total number of skills for pagination",
      control: { type: "number" },
    },
    isInstalling: {
      control: "boolean",
      description: "Whether installation is in progress",
    },
    isLoadingMore: {
      control: "boolean",
      description: "Whether more skills are being loaded",
    },
    error: {
      description: "Error object for error state",
    },
  },
};

export default meta;
type Story = StoryObj<typeof BrowseContent>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    skills: mockSkills,
    installedSkills: ["web-research"],
    onInstall: (name) => console.log("Install:", name),
    isInstalling: false,
    error: null,
    onRetry: () => console.log("Retry"),
    total: mockSkills.length,
    onLoadMore: () => console.log("Load more"),
    isLoadingMore: false,
    onViewDetails: (skill) => console.log("View details:", skill.name),
  },
  parameters: {
    docs: {
      description: {
        story: "Default browse view with skills grid and one installed skill.",
      },
    },
  },
};

export const Empty: Story = {
  args: {
    skills: [],
    installedSkills: [],
    onInstall: () => {},
    isInstalling: false,
    error: null,
    onRetry: () => {},
    total: 0,
  },
  parameters: {
    docs: {
      description: {
        story: "Empty state when no skills match the search/filter criteria.",
      },
    },
  },
};

export const WithPagination: Story = {
  args: {
    skills: mockSkills.slice(0, 3),
    installedSkills: [],
    onInstall: (name) => console.log("Install:", name),
    isInstalling: false,
    error: null,
    onRetry: () => {},
    total: 12,
    onLoadMore: () => console.log("Load more"),
    isLoadingMore: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Paginated view showing 3 of 12 skills with Load More button.",
      },
    },
  },
};

export const LoadingMore: Story = {
  args: {
    skills: mockSkills.slice(0, 3),
    installedSkills: [],
    onInstall: () => {},
    isInstalling: false,
    error: null,
    onRetry: () => {},
    total: 12,
    onLoadMore: () => {},
    isLoadingMore: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Loading state while fetching more skills.",
      },
    },
  },
};

export const Installing: Story = {
  args: {
    skills: mockSkills,
    installedSkills: [],
    onInstall: () => {},
    isInstalling: true,
    error: null,
    onRetry: () => {},
    total: mockSkills.length,
  },
  parameters: {
    docs: {
      description: {
        story: "State during skill installation with disabled buttons.",
      },
    },
  },
};

// =============================================================================
// Error States
// =============================================================================

export const NetworkError: Story = {
  args: {
    skills: [],
    installedSkills: [],
    onInstall: () => {},
    isInstalling: false,
    error: { status: 500, message: "Internal Server Error" },
    onRetry: () => console.log("Retry clicked"),
    total: 0,
  },
  parameters: {
    docs: {
      description: {
        story: "Error state with retry button for network errors.",
      },
    },
  },
};

export const AccessDenied: Story = {
  args: {
    skills: [],
    installedSkills: [],
    onInstall: () => {},
    isInstalling: false,
    error: {
      status: 403,
      data: { detail: "You don't have permission to access the marketplace." },
    },
    onRetry: () => {},
    total: 0,
  },
  parameters: {
    docs: {
      description: {
        story: "403 error state without retry button (authorization issue).",
      },
    },
  },
};
