/**
 * SkillsPage Stories
 *
 * Storybook stories for the Skills Marketplace page.
 * Showcases the full page with tabs, search, filtering, and skill management.
 *
 * Uses MSW for API mocking to provide realistic data scenarios.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { http, HttpResponse, delay } from "msw";
import { SkillsPage } from "./SkillsPage";
import { api } from "../api";

// =============================================================================
// Mock Data
// =============================================================================

const mockSkills = [
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

const mockUpdates = [
  {
    skillName: "web-research",
    currentVersion: "1.1.0",
    newVersion: "1.2.0",
    marketplace: "anthropic",
    changelog: "Performance improvements and bug fixes.",
  },
];

// =============================================================================
// Store Setup
// =============================================================================

const createMockStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

// =============================================================================
// Decorator with Provider
// =============================================================================

const withProvider = (Story: React.ComponentType) => {
  const store = createMockStore();
  return (
    <Provider store={store}>
      <div className="min-h-screen bg-neutral-1 p-6">
        <Story />
      </div>
    </Provider>
  );
};

// =============================================================================
// Meta
// =============================================================================

const meta: Meta<typeof SkillsPage> = {
  title: "Pages/SkillsPage",
  component: SkillsPage,
  tags: ["autodocs"],
  decorators: [withProvider],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Skills Marketplace page for browsing, installing, and managing skills. Provides tabbed interface for Browse, Installed, and Updates.",
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof SkillsPage>;

// =============================================================================
// Default Story - Browse Tab with Skills
// =============================================================================

export const Default: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
            enable_skills_system: true,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json({
            skills: mockSkills,
            total: mockSkills.length,
            marketplace: "anthropic",
            cached: false,
          });
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: ["web-research"],
            count: 1,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story:
          "Default browse view with skills grid showing available marketplace skills.",
      },
    },
  },
};

// =============================================================================
// Empty Marketplace
// =============================================================================

export const EmptyMarketplace: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json({
            skills: [],
            total: 0,
            marketplace: "anthropic",
            cached: false,
          });
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: [],
            count: 0,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story: "Empty marketplace state when no skills are available.",
      },
    },
  },
};

// =============================================================================
// Loading State
// =============================================================================

export const Loading: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
          });
        }),
        http.get("*/admin/skills/list", async () => {
          await delay("infinite");
          return HttpResponse.json({});
        }),
        http.get("*/admin/skills/installed", async () => {
          await delay("infinite");
          return HttpResponse.json({});
        }),
        http.get("*/admin/skills/updates", async () => {
          await delay("infinite");
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story: "Loading state while fetching skills from the marketplace.",
      },
    },
  },
};

// =============================================================================
// Network Error
// =============================================================================

export const NetworkError: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json(
            { detail: "Internal Server Error" },
            { status: 500 },
          );
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: [],
            count: 0,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story: "Error state when marketplace API returns a network error.",
      },
    },
  },
};

// =============================================================================
// Access Denied (403)
// =============================================================================

export const AccessDenied: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json(
            { detail: "You don't have permission to access the marketplace." },
            { status: 403 },
          );
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: [],
            count: 0,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story:
          "403 error state when user lacks marketplace access permissions.",
      },
    },
  },
};

// =============================================================================
// Feature Disabled
// =============================================================================

export const FeatureDisabled: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: false,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json({
            skills: [],
            total: 0,
            marketplace: "anthropic",
            cached: false,
          });
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: [],
            count: 0,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story: "State when skills_marketplace feature flag is disabled.",
      },
    },
  },
};

// =============================================================================
// With Updates Available
// =============================================================================

export const WithUpdates: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json({
            skills: mockSkills,
            total: mockSkills.length,
            marketplace: "anthropic",
            cached: false,
          });
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: ["web-research", "code-review"],
            count: 2,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json(mockUpdates);
        }),
      ],
    },
    docs: {
      description: {
        story:
          "Page with skill updates available, showing badge on Updates tab.",
      },
    },
  },
};

// =============================================================================
// Many Skills (Pagination)
// =============================================================================

const manySkills = Array.from({ length: 20 }, (_, i) => ({
  name: `skill-${i + 1}`,
  description: `Description for skill ${i + 1} with various features.`,
  version: "1.0.0",
  author: i % 2 === 0 ? "Anthropic" : "Community",
  tags: [`category-${(i % 4) + 1}`],
}));

export const ManySkills: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json({
            skills: manySkills,
            total: manySkills.length,
            marketplace: "anthropic",
            cached: false,
          });
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: [],
            count: 0,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story: "Page with many skills showing pagination (Load More button).",
      },
    },
  },
};

// =============================================================================
// Multiple Installed Skills
// =============================================================================

export const MultipleInstalled: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/features", () => {
          return HttpResponse.json({
            skills_marketplace: true,
          });
        }),
        http.get("*/admin/skills/list", () => {
          return HttpResponse.json({
            skills: mockSkills,
            total: mockSkills.length,
            marketplace: "anthropic",
            cached: false,
          });
        }),
        http.get("*/admin/skills/installed", () => {
          return HttpResponse.json({
            skills: [
              "web-research",
              "code-review",
              "data-analysis",
              "api-testing",
            ],
            count: 4,
          });
        }),
        http.get("*/admin/skills/updates", () => {
          return HttpResponse.json([]);
        }),
      ],
    },
    docs: {
      description: {
        story: "Page with multiple installed skills, visible in Installed tab.",
      },
    },
  },
};
