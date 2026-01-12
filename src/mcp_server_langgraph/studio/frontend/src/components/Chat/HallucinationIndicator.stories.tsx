/**
 * HallucinationIndicator Component Stories
 *
 * Storybook stories for the HallucinationIndicator component.
 * Showcases all states and interactions for AI hallucination reporting.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { HallucinationIndicator } from "./HallucinationIndicator";

const meta: Meta<typeof HallucinationIndicator> = {
  title: "Chat/HallucinationIndicator",
  component: HallucinationIndicator,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Allows users to report potential AI hallucinations or inaccuracies. Critical for AI safety and trustworthiness. Supports four categories: factual error, outdated info, made up source, and other.",
      },
    },
  },
  argTypes: {
    messageId: {
      control: "text",
      description: "Unique identifier of the message being reported",
    },
    isReported: {
      control: "boolean",
      description: "Whether this message has already been reported",
    },
    onReport: {
      description: "Callback fired when user submits a hallucination report",
    },
  },
};

export default meta;
type Story = StoryObj<typeof HallucinationIndicator>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    messageId: "msg-123",
    isReported: false,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default state showing the Flag button. Click to open the report dialog.",
      },
    },
  },
};

export const AlreadyReported: Story = {
  args: {
    messageId: "msg-456",
    isReported: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          "State shown when a message has already been reported. Button is disabled and shows 'Reported' status.",
      },
    },
  },
};

// =============================================================================
// Interactive Stories
// =============================================================================

export const WithDialogOpen: Story = {
  args: {
    messageId: "msg-789",
    isReported: false,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Click the Flag button to open the hallucination report dialog. Select a category and optionally add details.",
      },
    },
  },
  play: async ({ canvasElement }) => {
    // Auto-click the Flag button to show the dialog
    const button = canvasElement.querySelector("button");
    if (button) {
      button.click();
    }
  },
};

// =============================================================================
// Showcase Stories
// =============================================================================

export const AllStates: Story = {
  render: () => (
    <div className="flex flex-col gap-6 p-4">
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-600 dark:text-neutral-400 w-32">
          Default:
        </span>
        <HallucinationIndicator
          messageId="msg-1"
          onReport={(report) => console.log("Report:", report)}
        />
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-neutral-600 dark:text-neutral-400 w-32">
          Reported:
        </span>
        <HallucinationIndicator
          messageId="msg-2"
          onReport={(report) => console.log("Report:", report)}
          isReported
        />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "All states of the HallucinationIndicator displayed together.",
      },
    },
  },
};

export const InMessageContext: Story = {
  render: () => (
    <div className="max-w-lg p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
      <div className="prose dark:prose-invert text-sm mb-3">
        <p>
          The Eiffel Tower was built in 1889 and is located in Rome, Italy. It
          stands at 324 meters tall and was designed by Leonardo da Vinci.
        </p>
      </div>
      <div className="flex items-center gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
        <span className="text-xs text-neutral-500">
          AI response may contain errors
        </span>
        <HallucinationIndicator
          messageId="msg-factual"
          onReport={(report) => console.log("Report:", report)}
        />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "HallucinationIndicator shown in context of an AI message with factual errors (Eiffel Tower is in Paris, not Rome; designed by Gustave Eiffel, not da Vinci).",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-900 p-6 rounded-lg">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <span className="text-sm text-neutral-400 w-32">Default:</span>
          <HallucinationIndicator
            messageId="dark-1"
            onReport={(report) => console.log("Report:", report)}
          />
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-neutral-400 w-32">Reported:</span>
          <HallucinationIndicator
            messageId="dark-2"
            onReport={(report) => console.log("Report:", report)}
            isReported
          />
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "HallucinationIndicator states in dark mode context.",
      },
    },
  },
};

// =============================================================================
// Accessibility Story
// =============================================================================

export const AccessibilityShowcase: Story = {
  render: () => (
    <div className="p-4 space-y-6">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">
          Accessibility Features
        </h3>
        <ul className="text-xs text-neutral-600 dark:text-neutral-400 list-disc list-inside space-y-1">
          <li>Keyboard navigable (Tab, Enter, Escape)</li>
          <li>Screen reader friendly with ARIA labels</li>
          <li>Focus trap in dialog</li>
          <li>Radio group pattern for category selection</li>
          <li>Form labels properly associated</li>
        </ul>
      </div>
      <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
        <HallucinationIndicator
          messageId="a11y-demo"
          onReport={(report) => console.log("Report:", report)}
        />
        <p className="mt-2 text-xs text-neutral-500">
          Try navigating with Tab key and pressing Enter to open dialog, Escape
          to close.
        </p>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Demonstrates accessibility features including keyboard navigation, ARIA labels, and focus management.",
      },
    },
  },
};
