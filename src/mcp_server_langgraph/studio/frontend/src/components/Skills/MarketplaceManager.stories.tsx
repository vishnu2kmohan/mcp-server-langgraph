/**
 * MarketplaceManager Component Stories
 *
 * Storybook stories for the marketplace manager panel.
 * Showcases different states including loading, error, and various marketplace configurations.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { MarketplaceManager } from "./MarketplaceManager";
import type { MarketplaceInfo } from "../../types/skills";

const meta: Meta<typeof MarketplaceManager> = {
  title: "Skills/MarketplaceManager",
  component: MarketplaceManager,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Panel for managing skill marketplaces. Shows registered marketplaces with actions to add, remove, and sync.",
      },
    },
  },
  argTypes: {
    marketplaces: {
      control: "object",
      description: "List of registered marketplaces",
    },
    onAdd: {
      action: "add clicked",
      description: "Called when Add Marketplace button clicked",
    },
    onRemove: {
      action: "remove clicked",
      description: "Called when Remove button clicked with marketplace name",
    },
    onSync: {
      action: "sync clicked",
      description: "Called when Sync button clicked with marketplace name",
    },
    isLoading: {
      control: "boolean",
      description: "Loading state for initial data fetch",
    },
    isSyncing: {
      control: "boolean",
      description: "Whether a sync operation is in progress",
    },
    syncingMarketplace: {
      control: "text",
      description: "Name of marketplace currently being synced",
    },
    error: {
      control: "text",
      description: "Error message to display",
    },
  },
  decorators: [
    (Story) => (
      <div className="w-[400px] bg-neutral-1 p-4 rounded-lg border border-neutral-6">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof MarketplaceManager>;

// =============================================================================
// Mock Data
// =============================================================================

const mockMarketplaces: MarketplaceInfo[] = [
  {
    name: "anthropic",
    uri: "https://github.com/anthropics/skills-marketplace",
    type: "github",
    trusted: true,
    autoSync: true,
    requiresApproval: false,
  },
  {
    name: "community",
    uri: "https://github.com/community/skills",
    type: "github",
    trusted: false,
    autoSync: false,
    requiresApproval: true,
  },
];

// =============================================================================
// Default State
// =============================================================================

export const Default: Story = {
  args: {
    marketplaces: mockMarketplaces,
    onAdd: () => console.log("Add clicked"),
    onRemove: (name) => console.log("Remove clicked:", name),
    onSync: (name) => console.log("Sync clicked:", name),
    isLoading: false,
    isSyncing: false,
    syncingMarketplace: null,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default marketplace manager showing registered marketplaces with available actions.",
      },
    },
  },
};

// =============================================================================
// Loading State
// =============================================================================

export const Loading: Story = {
  args: {
    marketplaces: [],
    onAdd: () => {},
    onRemove: () => {},
    onSync: () => {},
    isLoading: true,
    isSyncing: false,
    syncingMarketplace: null,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story: "Loading state while fetching marketplace data.",
      },
    },
  },
};

// =============================================================================
// Syncing State
// =============================================================================

export const Syncing: Story = {
  args: {
    marketplaces: mockMarketplaces,
    onAdd: () => {},
    onRemove: () => {},
    onSync: () => {},
    isLoading: false,
    isSyncing: true,
    syncingMarketplace: "anthropic",
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story:
          "State when a marketplace is being synced. Sync button shows loading indicator.",
      },
    },
  },
};

// =============================================================================
// Error State
// =============================================================================

export const WithError: Story = {
  args: {
    marketplaces: mockMarketplaces,
    onAdd: () => {},
    onRemove: () => {},
    onSync: () => {},
    isLoading: false,
    isSyncing: false,
    syncingMarketplace: null,
    error: "Failed to load marketplaces. Please try again.",
  },
  parameters: {
    docs: {
      description: {
        story:
          "Error state showing an error message above the marketplace list.",
      },
    },
  },
};

// =============================================================================
// Empty State
// =============================================================================

export const Empty: Story = {
  args: {
    marketplaces: [],
    onAdd: () => console.log("Add clicked"),
    onRemove: () => {},
    onSync: () => {},
    isLoading: false,
    isSyncing: false,
    syncingMarketplace: null,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story: "Empty state when no marketplaces are registered.",
      },
    },
  },
};

// =============================================================================
// Single Marketplace
// =============================================================================

export const SingleMarketplace: Story = {
  args: {
    marketplaces: [mockMarketplaces[0]],
    onAdd: () => console.log("Add clicked"),
    onRemove: (name) => console.log("Remove clicked:", name),
    onSync: (name) => console.log("Sync clicked:", name),
    isLoading: false,
    isSyncing: false,
    syncingMarketplace: null,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Manager with only the default Anthropic marketplace (remove button hidden).",
      },
    },
  },
};

// =============================================================================
// Many Marketplaces
// =============================================================================

export const ManyMarketplaces: Story = {
  args: {
    marketplaces: [
      ...mockMarketplaces,
      {
        name: "enterprise",
        uri: "https://github.com/enterprise/skills",
        type: "github",
        trusted: true,
        autoSync: true,
        requiresApproval: false,
      },
      {
        name: "internal",
        uri: "https://registry.internal/skills",
        type: "registry",
        trusted: true,
        autoSync: false,
        requiresApproval: true,
      },
    ],
    onAdd: () => console.log("Add clicked"),
    onRemove: (name) => console.log("Remove clicked:", name),
    onSync: (name) => console.log("Sync clicked:", name),
    isLoading: false,
    isSyncing: false,
    syncingMarketplace: null,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Manager with multiple registered marketplaces showing scrollable list.",
      },
    },
  },
};
