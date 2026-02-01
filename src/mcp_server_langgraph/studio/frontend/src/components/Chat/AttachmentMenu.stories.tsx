/**
 * AttachmentMenu Component Stories
 *
 * Storybook stories for the Slack-style plus (+) menu component.
 * Showcases all states and interactions for file upload and actions.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { AttachmentMenu } from "./AttachmentMenu";

const meta: Meta<typeof AttachmentMenu> = {
  title: "Chat/AttachmentMenu",
  component: AttachmentMenu,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Slack-style plus (+) menu for the chat input form. Provides access to file upload, Knowledge Base Focus, code snippets, and mentions.",
      },
    },
  },
  argTypes: {
    onFileSelect: {
      description: "Callback when files are selected",
    },
    isUploading: {
      control: "boolean",
      description: "Whether files are currently being uploaded",
    },
    showKBFocus: {
      control: "boolean",
      description: "Whether to show Knowledge Base Focus option",
    },
    kbFocusValue: {
      control: "select",
      options: ["all", "kb_only", "web_only", "none"],
      description: "Current KB Focus mode",
    },
    disabled: {
      control: "boolean",
      description: "Whether the menu is disabled",
    },
  },
};

export default meta;
type Story = StoryObj<typeof AttachmentMenu>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    onFileSelect: (files) => console.log("Files selected:", files),
    showKBFocus: true,
    kbFocusValue: "all",
    kbStatus: "ready",
    onKBFocusChange: (mode) => console.log("KB Focus changed to:", mode),
    onInsertCodeBlock: () => console.log("Insert code block"),
    onInsertMention: () => console.log("Insert mention"),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default state with all options available. Click the + button to open the menu.",
      },
    },
  },
};

export const WithoutKBFocus: Story = {
  args: {
    onFileSelect: (files) => console.log("Files selected:", files),
    showKBFocus: false,
    onInsertCodeBlock: () => console.log("Insert code block"),
    onInsertMention: () => console.log("Insert mention"),
  },
  parameters: {
    docs: {
      description: {
        story: "Menu without Knowledge Base Focus option.",
      },
    },
  },
};

export const Uploading: Story = {
  args: {
    onFileSelect: (files) => console.log("Files selected:", files),
    isUploading: true,
    showKBFocus: true,
    kbFocusValue: "all",
  },
  parameters: {
    docs: {
      description: {
        story: "Button is disabled while files are being uploaded.",
      },
    },
  },
};

export const Disabled: Story = {
  args: {
    onFileSelect: (files) => console.log("Files selected:", files),
    disabled: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Disabled state when the chat is processing.",
      },
    },
  },
};

// =============================================================================
// KB Focus Modes
// =============================================================================

export const KBFocusAllSources: Story = {
  args: {
    onFileSelect: (files) => console.log("Files selected:", files),
    showKBFocus: true,
    kbFocusValue: "all",
    kbStatus: "ready",
    onKBFocusChange: (mode) => console.log("KB Focus changed to:", mode),
    onInsertCodeBlock: () => console.log("Insert code block"),
    onInsertMention: () => console.log("Insert mention"),
  },
  parameters: {
    docs: {
      description: {
        story: "KB Focus set to 'All Sources' - searches both KB and web.",
      },
    },
  },
};

export const KBFocusKBOnly: Story = {
  args: {
    onFileSelect: (files) => console.log("Files selected:", files),
    showKBFocus: true,
    kbFocusValue: "kb_only",
    kbStatus: "ready",
    onKBFocusChange: (mode) => console.log("KB Focus changed to:", mode),
    onInsertCodeBlock: () => console.log("Insert code block"),
    onInsertMention: () => console.log("Insert mention"),
  },
  parameters: {
    docs: {
      description: {
        story:
          "KB Focus set to 'Knowledge Base Only' - restricts to internal knowledge.",
      },
    },
  },
};

// =============================================================================
// Context Stories
// =============================================================================

export const InChatInputContext: Story = {
  render: () => (
    <div className="flex items-center gap-2 p-3 bg-neutral-2 border border-neutral-6 rounded-lg w-96">
      <AttachmentMenu
        onFileSelect={(files) => console.log("Files:", files)}
        showKBFocus={true}
        kbFocusValue="all"
        onKBFocusChange={(mode) => console.log("Mode:", mode)}
        onInsertCodeBlock={() => console.log("Code")}
        onInsertMention={() => console.log("Mention")}
      />
      <span className="flex-1 text-sm text-neutral-9">Message...</span>
      <button className="p-2 rounded-full bg-primary-9 text-neutral-12">
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 10l7-7m0 0l7 7m-7-7v18"
          />
        </svg>
      </button>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "AttachmentMenu shown in context of a chat input form.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <div className="flex items-center gap-4">
        <AttachmentMenu
          onFileSelect={(files) => console.log("Files:", files)}
          showKBFocus={true}
          kbFocusValue="all"
          onKBFocusChange={(mode) => console.log("Mode:", mode)}
          onInsertCodeBlock={() => console.log("Code")}
          onInsertMention={() => console.log("Mention")}
        />
        <span className="text-sm text-neutral-9">
          Click to see dark mode menu
        </span>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "AttachmentMenu in dark mode context.",
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
        <h3 className="text-sm font-semibold text-neutral-11">
          Accessibility Features
        </h3>
        <ul className="text-xs text-neutral-11 list-disc list-inside space-y-1">
          <li>Keyboard navigable (Arrow keys, Enter, Escape)</li>
          <li>ARIA attributes (aria-haspopup, aria-expanded)</li>
          <li>Role="menu" and role="menuitem" for proper semantics</li>
          <li>Focus management on open/close</li>
          <li>Submenu navigation with ArrowRight/ArrowLeft</li>
        </ul>
      </div>
      <div className="pt-4 border-t border-neutral-6">
        <AttachmentMenu
          onFileSelect={(files) => console.log("Files:", files)}
          showKBFocus={true}
          kbFocusValue="all"
          onKBFocusChange={(mode) => console.log("Mode:", mode)}
          onInsertCodeBlock={() => console.log("Code")}
          onInsertMention={() => console.log("Mention")}
        />
        <p className="mt-2 text-xs text-neutral-10">
          Try navigating with Tab, Arrow keys, Enter to select, Escape to close.
        </p>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Demonstrates accessibility features of the AttachmentMenu.",
      },
    },
  },
};
