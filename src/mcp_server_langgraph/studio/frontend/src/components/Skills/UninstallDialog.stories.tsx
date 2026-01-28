/**
 * UninstallDialog Component Stories
 *
 * Storybook stories for the uninstall confirmation dialog.
 * Showcases different states and user interactions.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { UninstallDialog } from "./UninstallDialog";

const meta: Meta<typeof UninstallDialog> = {
  title: "Skills/UninstallDialog",
  component: UninstallDialog,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Confirmation dialog for skill uninstallation. Shows skill name and warning before removing a skill.",
      },
    },
  },
  argTypes: {
    skillName: {
      control: "text",
      description: "Name of the skill to uninstall",
    },
    isOpen: {
      control: "boolean",
      description: "Whether the dialog is open",
    },
    isUninstalling: {
      control: "boolean",
      description: "Whether uninstallation is in progress",
    },
    onClose: {
      action: "closed",
      description: "Called when dialog should close",
    },
    onConfirm: {
      action: "confirmed",
      description: "Called when uninstall is confirmed",
    },
  },
};

export default meta;
type Story = StoryObj<typeof UninstallDialog>;

// =============================================================================
// Default State
// =============================================================================

export const Default: Story = {
  args: {
    skillName: "web-research",
    isOpen: true,
    isUninstalling: false,
    onClose: () => console.log("Close clicked"),
    onConfirm: () => console.log("Uninstall confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Default uninstall confirmation dialog ready for user action.",
      },
    },
  },
};

// =============================================================================
// Uninstalling State
// =============================================================================

export const Uninstalling: Story = {
  args: {
    skillName: "web-research",
    isOpen: true,
    isUninstalling: true,
    onClose: () => {},
    onConfirm: () => {},
  },
  parameters: {
    docs: {
      description: {
        story:
          "Dialog while uninstallation is in progress. Buttons are disabled and show loading state.",
      },
    },
  },
};

// =============================================================================
// Long Skill Name
// =============================================================================

export const LongSkillName: Story = {
  args: {
    skillName: "very-long-skill-name-for-testing-ui-wrapping-behavior",
    isOpen: true,
    isUninstalling: false,
    onClose: () => console.log("Close clicked"),
    onConfirm: () => console.log("Uninstall confirmed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog with a very long skill name to test text wrapping.",
      },
    },
  },
};

// =============================================================================
// Closed State
// =============================================================================

export const Closed: Story = {
  args: {
    skillName: "web-research",
    isOpen: false,
    isUninstalling: false,
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
