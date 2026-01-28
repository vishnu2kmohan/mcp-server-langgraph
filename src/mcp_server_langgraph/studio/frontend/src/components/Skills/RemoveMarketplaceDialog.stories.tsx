/**
 * RemoveMarketplaceDialog Component Stories
 *
 * Storybook stories for the remove marketplace confirmation dialog.
 * Showcases different states and marketplace name variations.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { RemoveMarketplaceDialog } from "./RemoveMarketplaceDialog";

const meta: Meta<typeof RemoveMarketplaceDialog> = {
  title: "Skills/RemoveMarketplaceDialog",
  component: RemoveMarketplaceDialog,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Confirmation dialog for removing a skill marketplace. Shows marketplace name and warning about consequences.",
      },
    },
  },
  argTypes: {
    marketplaceName: {
      control: "text",
      description: "Name of the marketplace to remove",
    },
    isOpen: {
      control: "boolean",
      description: "Whether the dialog is open",
    },
    isRemoving: {
      control: "boolean",
      description: "Whether removal is in progress",
    },
    onClose: {
      action: "closed",
      description: "Called when dialog should close",
    },
    onConfirm: {
      action: "confirmed",
      description: "Called when removal is confirmed",
    },
  },
};

export default meta;
type Story = StoryObj<typeof RemoveMarketplaceDialog>;

// =============================================================================
// Default State
// =============================================================================

export const Default: Story = {
  args: {
    marketplaceName: "community",
    isOpen: true,
    isRemoving: false,
    onClose: () => console.log("Close clicked"),
    onConfirm: () => console.log("Remove confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Default remove confirmation dialog ready for user action.",
      },
    },
  },
};

// =============================================================================
// Removing State
// =============================================================================

export const Removing: Story = {
  args: {
    marketplaceName: "community",
    isOpen: true,
    isRemoving: true,
    onClose: () => {},
    onConfirm: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          "Dialog while removal is in progress. Buttons are disabled and show loading state.",
      },
    },
  },
};

// =============================================================================
// Long Marketplace Name
// =============================================================================

export const LongMarketplaceName: Story = {
  args: {
    marketplaceName: "very-long-marketplace-name-for-testing-ui-wrapping",
    isOpen: true,
    isRemoving: false,
    onClose: () => console.log("Close clicked"),
    onConfirm: () => console.log("Remove confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Dialog with a very long marketplace name to test text wrapping.",
      },
    },
  },
};

// =============================================================================
// Special Characters
// =============================================================================

export const SpecialCharacters: Story = {
  args: {
    marketplaceName: "my-org/skills-repo",
    isOpen: true,
    isRemoving: false,
    onClose: () => console.log("Close clicked"),
    onConfirm: () => console.log("Remove confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog with special characters in marketplace name.",
      },
    },
  },
};

// =============================================================================
// Closed State
// =============================================================================

export const Closed: Story = {
  args: {
    marketplaceName: "community",
    isOpen: false,
    isRemoving: false,
    onClose: () => {},
    onConfirm: () => {},
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog in closed state (nothing rendered).",
      },
    },
  },
};
