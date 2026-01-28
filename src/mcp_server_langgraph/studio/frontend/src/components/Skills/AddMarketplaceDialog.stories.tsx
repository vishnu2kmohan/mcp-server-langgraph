/**
 * AddMarketplaceDialog Component Stories
 *
 * Storybook stories for the add marketplace dialog.
 * Showcases different states including form validation, submission, and errors.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { AddMarketplaceDialog } from "./AddMarketplaceDialog";

const meta: Meta<typeof AddMarketplaceDialog> = {
  title: "Skills/AddMarketplaceDialog",
  component: AddMarketplaceDialog,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Dialog for adding a new skill marketplace. Includes form fields for name, URI, type, and security options.",
      },
    },
  },
  argTypes: {
    isOpen: {
      control: "boolean",
      description: "Whether the dialog is open",
    },
    onClose: {
      action: "closed",
      description: "Called when dialog should close",
    },
    onSubmit: {
      action: "submitted",
      description: "Called when form is submitted with valid data",
    },
    isSubmitting: {
      control: "boolean",
      description: "Loading state during submission",
    },
    error: {
      control: "text",
      description: "Error message to display",
    },
  },
};

export default meta;
type Story = StoryObj<typeof AddMarketplaceDialog>;

// =============================================================================
// Default State
// =============================================================================

export const Default: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log("Close clicked"),
    onSubmit: (data) => console.log("Submitted:", data),
    isSubmitting: false,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default add marketplace dialog with empty form ready for input.",
      },
    },
  },
};

// =============================================================================
// Submitting State
// =============================================================================

export const Submitting: Story = {
  args: {
    isOpen: true,
    onClose: () => {},
    onSubmit: () => {},
    isSubmitting: true,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Dialog while submission is in progress. Buttons are disabled and show loading state.",
      },
    },
  },
};

// =============================================================================
// With Error
// =============================================================================

export const WithError: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log("Close clicked"),
    onSubmit: () => {},
    isSubmitting: false,
    error: "A marketplace with this name already exists.",
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog showing a server-side error after failed submission.",
      },
    },
  },
};

// =============================================================================
// Network Error
// =============================================================================

export const NetworkError: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log("Close clicked"),
    onSubmit: () => {},
    isSubmitting: false,
    error: "Unable to connect to server. Please check your network connection.",
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog showing a network error message.",
      },
    },
  },
};

// =============================================================================
// Closed State
// =============================================================================

export const Closed: Story = {
  args: {
    isOpen: false,
    onClose: () => {},
    onSubmit: () => {},
    isSubmitting: false,
    error: null,
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog in closed state (nothing rendered).",
      },
    },
  },
};
