/**
 * RichTextInput Component Stories
 *
 * Storybook stories for the rich text input component with Slack-style formatting.
 * Showcases formatting toolbar, keyboard shortcuts, mentions, and inline suggestions.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { RichTextInput } from "./RichTextInput";

const SAMPLE_MENTION_OPTIONS = [
  { type: "model" as const, value: "claude-4.5", label: "Claude 4.5 Opus" },
  { type: "model" as const, value: "gemini-2.5", label: "Gemini 2.5 Pro" },
  { type: "model" as const, value: "gpt-5.1", label: "GPT-5.1" },
  { type: "file" as const, value: "README.md", label: "README.md" },
  { type: "file" as const, value: "package.json", label: "package.json" },
  { type: "user" as const, value: "alice", label: "Alice Smith" },
  { type: "user" as const, value: "bob", label: "Bob Johnson" },
];

const meta: Meta<typeof RichTextInput> = {
  title: "Chat/RichTextInput",
  component: RichTextInput,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Rich text input with Slack-style formatting toolbar. Supports bold, italic, strikethrough, code, lists, quotes, code blocks, mentions, and inline AI suggestions.",
      },
    },
  },
  argTypes: {
    onSubmit: {
      description: "Callback when text is submitted",
    },
    onChange: {
      description: "Callback when text changes",
    },
    value: {
      control: "text",
      description: "Controlled value",
    },
    placeholder: {
      control: "text",
      description: "Placeholder text",
    },
    maxLength: {
      control: "number",
      description: "Maximum character length",
    },
    disabled: {
      control: "boolean",
      description: "Disabled state",
    },
    submitOnEnter: {
      control: "boolean",
      description: "Enter submits (true) or Ctrl+Enter submits (false)",
    },
    defaultToolbarExpanded: {
      control: "boolean",
      description: "Whether toolbar is expanded by default",
    },
    enableInlineSuggestions: {
      control: "boolean",
      description: "Enable inline AI suggestions (ghost text)",
    },
  },
};

export default meta;
type Story = StoryObj<typeof RichTextInput>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Type a message...",
  },
  parameters: {
    docs: {
      description: {
        story: "Default state with collapsed toolbar. Click 'Aa' to expand formatting options.",
      },
    },
  },
};

export const ToolbarExpanded: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Type a message...",
    defaultToolbarExpanded: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Toolbar expanded showing all formatting options: Bold, Italic, Strikethrough, Code, Lists, Quote, Code Block.",
      },
    },
  },
};

export const WithPlaceholder: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Ask me anything about your codebase...",
    defaultToolbarExpanded: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Custom placeholder text for context-specific input.",
      },
    },
  },
};

export const Disabled: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Input disabled...",
    disabled: true,
    defaultToolbarExpanded: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Disabled state when processing or loading.",
      },
    },
  },
};

// =============================================================================
// Submit Modes
// =============================================================================

export const SubmitOnEnter: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Press Enter to submit, Shift+Enter for newline",
    submitOnEnter: true,
    defaultToolbarExpanded: true,
  },
  parameters: {
    docs: {
      description: {
        story: "ChatGPT-style: Enter submits, Shift+Enter creates newline.",
      },
    },
  },
};

export const SubmitOnCtrlEnter: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Press Ctrl+Enter to submit, Enter for newline",
    submitOnEnter: false,
    defaultToolbarExpanded: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Legacy-style: Ctrl/Cmd+Enter submits, Enter creates newline.",
      },
    },
  },
};

// =============================================================================
// Character Limit
// =============================================================================

export const WithMaxLength: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Limited to 100 characters...",
    maxLength: 100,
    defaultToolbarExpanded: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Character counter shown when maxLength is set.",
      },
    },
  },
};

// =============================================================================
// Mentions
// =============================================================================

export const WithMentions: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    placeholder: "Type @ to mention models, files, or users...",
    mentionOptions: SAMPLE_MENTION_OPTIONS,
    defaultToolbarExpanded: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Type @ to see mention suggestions. Supports @model, @file, and @user mentions.",
      },
    },
  },
};

// =============================================================================
// Inline Suggestions
// =============================================================================

export const WithInlineSuggestion: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    value: "How do I ",
    placeholder: "Type to see AI suggestions...",
    enableInlineSuggestions: true,
    inlineSuggestion: "implement authentication in React?",
    onAcceptSuggestion: (suggestion) => console.log("Accepted:", suggestion),
    onDismissSuggestion: () => console.log("Dismissed"),
  },
  parameters: {
    docs: {
      description: {
        story: "Inline AI suggestion shown as ghost text. Press Tab to accept, Escape to dismiss.",
      },
    },
  },
};

export const SuggestionLoading: Story = {
  args: {
    onSubmit: (text) => console.log("Submitted:", text),
    value: "What is the best way to",
    placeholder: "Type to see AI suggestions...",
    enableInlineSuggestions: true,
    isSuggestionLoading: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Loading state while fetching inline suggestion.",
      },
    },
  },
};

// =============================================================================
// Controlled Component
// =============================================================================

export const Controlled: Story = {
  render: function ControlledStory() {
    const [value, setValue] = useState("**Bold** and *italic* text");
    return (
      <div className="w-96 space-y-4">
        <RichTextInput
          value={value}
          onChange={setValue}
          onSubmit={(text) => {
            console.log("Submitted:", text);
            setValue("");
          }}
          placeholder="Controlled input..."
          defaultToolbarExpanded={true}
        />
        <div className="text-xs text-neutral-10">
          <strong>Current value:</strong>
          <pre className="mt-1 p-2 bg-neutral-3 rounded text-xs overflow-auto">
            {value || "(empty)"}
          </pre>
        </div>
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Controlled component with external state management.",
      },
    },
  },
};

// =============================================================================
// Formatting Examples
// =============================================================================

export const FormattingShowcase: Story = {
  render: () => (
    <div className="w-[500px] space-y-6">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-neutral-11">
          Formatting Options
        </h3>
        <ul className="text-xs text-neutral-11 space-y-1">
          <li><strong>Bold:</strong> **text** or Ctrl+B</li>
          <li><strong>Italic:</strong> *text* or Ctrl+I</li>
          <li><strong>Strikethrough:</strong> ~~text~~ or Ctrl+Shift+X</li>
          <li><strong>Code:</strong> `text` or Ctrl+`</li>
          <li><strong>Ordered List:</strong> 1. item (auto-continues on Enter)</li>
          <li><strong>Bullet List:</strong> - item (auto-continues on Enter)</li>
          <li><strong>Quote:</strong> &gt; text (auto-continues on Enter)</li>
          <li><strong>Code Block:</strong> ```code```</li>
        </ul>
      </div>
      <RichTextInput
        onSubmit={(text) => console.log("Submitted:", text)}
        placeholder="Try the formatting options..."
        defaultToolbarExpanded={true}
      />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Complete reference of all formatting options and keyboard shortcuts.",
      },
    },
  },
};

// =============================================================================
// List Auto-Continue
// =============================================================================

export const ListAutoContinue: Story = {
  render: function ListStory() {
    const [value, setValue] = useState("1. First item\n2. Second item\n3. ");
    return (
      <div className="w-96 space-y-4">
        <div className="text-xs text-neutral-10 space-y-1">
          <p><strong>Auto-continue lists:</strong></p>
          <ul className="list-disc list-inside">
            <li>Type in a list item and press Shift+Enter (or Enter in legacy mode)</li>
            <li>The next list number/bullet is auto-inserted</li>
            <li>Press Enter on empty item to exit list mode</li>
          </ul>
        </div>
        <RichTextInput
          value={value}
          onChange={setValue}
          onSubmit={(text) => {
            console.log("Submitted:", text);
            setValue("");
          }}
          placeholder="Continue the list..."
          submitOnEnter={true}
          defaultToolbarExpanded={true}
        />
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "Demonstrates Slack-style auto-continue for ordered lists, bullet lists, and quotes.",
      },
    },
  },
};

// =============================================================================
// Dark Mode
// =============================================================================

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg w-[500px]">
      <RichTextInput
        onSubmit={(text) => console.log("Submitted:", text)}
        placeholder="Dark mode input..."
        defaultToolbarExpanded={true}
        mentionOptions={SAMPLE_MENTION_OPTIONS}
      />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "RichTextInput in dark mode context.",
      },
    },
  },
};

// =============================================================================
// Accessibility
// =============================================================================

export const AccessibilityShowcase: Story = {
  render: () => (
    <div className="w-[500px] space-y-6">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-neutral-11">
          Accessibility Features
        </h3>
        <ul className="text-xs text-neutral-11 list-disc list-inside space-y-1">
          <li>Keyboard shortcuts for all formatting (Ctrl+B, Ctrl+I, etc.)</li>
          <li>Ctrl+Shift+F toggles toolbar visibility</li>
          <li>Tab navigation through toolbar buttons</li>
          <li>ARIA labels on all interactive elements</li>
          <li>Screen reader announcements for toolbar state</li>
          <li>Escape closes mention suggestions</li>
          <li>Listbox pattern for mention suggestions</li>
        </ul>
      </div>
      <RichTextInput
        onSubmit={(text) => console.log("Submitted:", text)}
        placeholder="Try keyboard navigation..."
        defaultToolbarExpanded={true}
        mentionOptions={SAMPLE_MENTION_OPTIONS}
      />
      <p className="text-xs text-neutral-10">
        Press Ctrl+Shift+F to toggle toolbar, Tab through buttons, type @ for mentions.
      </p>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Demonstrates accessibility features including keyboard navigation and ARIA support.",
      },
    },
  },
};

// =============================================================================
// Full Featured
// =============================================================================

export const FullFeatured: Story = {
  render: function FullFeaturedStory() {
    const [value, setValue] = useState("");
    return (
      <div className="w-[500px] space-y-4">
        <RichTextInput
          value={value}
          onChange={setValue}
          onSubmit={(text) => {
            console.log("Submitted:", text);
            setValue("");
          }}
          placeholder="Full-featured input with all options..."
          defaultToolbarExpanded={true}
          mentionOptions={SAMPLE_MENTION_OPTIONS}
          maxLength={500}
          submitOnEnter={true}
          enableInlineSuggestions={true}
          inlineSuggestion={value.length > 10 ? " - here's a suggestion" : undefined}
          onAcceptSuggestion={(suggestion) => setValue(value + suggestion)}
          onDismissSuggestion={() => console.log("Dismissed")}
        />
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: "All features enabled: formatting, mentions, character limit, inline suggestions.",
      },
    },
  },
};
