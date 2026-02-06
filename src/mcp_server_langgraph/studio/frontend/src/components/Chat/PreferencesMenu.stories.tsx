/**
 * PreferencesMenu Component Stories
 *
 * Storybook stories for the hierarchical preferences dropdown.
 * Showcases all states, submenus, and settings configurations.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { PreferencesMenu } from "./PreferencesMenu";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import type { KBFocusMode } from "./KnowledgeBaseFocus";
import type { ToolSelectionMode, ToolPreference } from "@/types/tools";
import type { ModelOption } from "@/types";

const sampleModels: ModelOption[] = [
  { id: "claude-opus-4-5", name: "Claude Opus 4.5", provider: "anthropic" },
  { id: "claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic" },
  {
    id: "gemini-2.0-flash",
    name: "Gemini 2.0 Flash",
    provider: "google",
    vendor: "vertex_ai",
  },
  { id: "gpt-4o", name: "GPT-4o", provider: "openai" },
  { id: "o1-preview", name: "o1-preview", provider: "openai" },
];

const meta: Meta<typeof PreferencesMenu> = {
  title: "Chat/PreferencesMenu",
  component: PreferencesMenu,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Hierarchical preferences dropdown for chat input settings. Provides access to model selection, thinking level, tools mode, and KB focus settings via Radix UI submenus.",
      },
    },
  },
  argTypes: {
    selectedModel: {
      control: "select",
      options: sampleModels.map((m) => m.id),
      description: "Currently selected model ID",
    },
    thinkingLevel: {
      control: "select",
      options: ["low", "medium", "high"] as ReasoningEffortLevel[],
      description: "Current thinking/reasoning effort level",
    },
    toolMode: {
      control: "select",
      options: ["auto", "manual", "none"] as ToolSelectionMode[],
      description: "Tool selection mode",
    },
    toolPreference: {
      control: "select",
      options: ["auto", "native", "builtin", "mcp"] as ToolPreference[],
      description: "Tool provider preference",
    },
    kbFocusMode: {
      control: "select",
      options: ["all", "kb_only", "web_only", "none"] as KBFocusMode[],
      description: "Knowledge Base focus mode",
    },
    isLoading: {
      control: "boolean",
      description: "Whether the menu is in loading state",
    },
    disabled: {
      control: "boolean",
      description: "Whether the menu is disabled",
    },
    compact: {
      control: "boolean",
      description: "Compact mode for smaller displays",
    },
    critiqueLoopEnabled: {
      control: "boolean",
      description: "Whether critique loop (executor/critic) is enabled",
    },
  },
};

export default meta;
type Story = StoryObj<typeof PreferencesMenu>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    selectedModel: "claude-sonnet-4",
    availableModels: sampleModels,
    onModelChange: (modelId) => console.log("Model changed:", modelId),
    thinkingLevel: "medium",
    onThinkingLevelChange: (level) =>
      console.log("Thinking level changed:", level),
    toolMode: "auto",
    onToolModeChange: (mode) => console.log("Tool mode changed:", mode),
    toolPreference: "auto",
    onToolPreferenceChange: (pref) =>
      console.log("Tool preference changed:", pref),
    kbFocusMode: "all",
    onKBFocusChange: (mode) => console.log("KB focus changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default state with all settings available. Click to open and explore hierarchical submenus.",
      },
    },
  },
};

export const Compact: Story = {
  args: {
    ...Default.args,
    compact: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Compact mode for smaller displays - shows only the icon.",
      },
    },
  },
};

export const Loading: Story = {
  args: {
    ...Default.args,
    isLoading: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Loading state with spinner animation.",
      },
    },
  },
};

export const Disabled: Story = {
  args: {
    ...Default.args,
    disabled: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Disabled state when chat is processing.",
      },
    },
  },
};

export const LoadingModels: Story = {
  args: {
    ...Default.args,
    isModelsLoading: true,
  },
  parameters: {
    docs: {
      description: {
        story: "State when models are still loading from the server.",
      },
    },
  },
};

// =============================================================================
// Setting Variations
// =============================================================================

export const HighThinking: Story = {
  args: {
    ...Default.args,
    thinkingLevel: "high",
  },
  parameters: {
    docs: {
      description: {
        story: "Thinking level set to 'High' for complex reasoning tasks.",
      },
    },
  },
};

export const ManualTools: Story = {
  args: {
    ...Default.args,
    toolMode: "manual",
    toolPreference: "native",
  },
  parameters: {
    docs: {
      description: {
        story: "Manual tool mode with native provider preference.",
      },
    },
  },
};

export const KBOnly: Story = {
  args: {
    ...Default.args,
    kbFocusMode: "kb_only",
  },
  parameters: {
    docs: {
      description: {
        story: "Knowledge Base Focus set to KB Only - no web search.",
      },
    },
  },
};

// =============================================================================
// Critique Loop (Executor/Critic)
// =============================================================================

export const WithCritiqueLoop: Story = {
  args: {
    ...Default.args,
    critiqueLoopEnabled: true,
    executorModel: "claude-opus-4-5",
    onExecutorModelChange: (modelId) =>
      console.log("Executor model changed:", modelId),
    criticModel: "gemini-2.0-flash",
    onCriticModelChange: (modelId) =>
      console.log("Critic model changed:", modelId),
  },
  parameters: {
    docs: {
      description: {
        story:
          "With critique loop enabled - shows additional Executor and Critic model submenus for multi-model reasoning.",
      },
    },
  },
};

export const CritiqueLoopAutoModels: Story = {
  args: {
    ...Default.args,
    critiqueLoopEnabled: true,
    executorModel: null,
    onExecutorModelChange: (modelId) =>
      console.log("Executor model changed:", modelId),
    criticModel: null,
    onCriticModelChange: (modelId) =>
      console.log("Critic model changed:", modelId),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Critique loop with automatic model selection (complexity-based for executor, cross-vendor for critic).",
      },
    },
  },
};

// =============================================================================
// Context Stories
// =============================================================================

export const InChatInputContext: Story = {
  render: () => (
    <div className="flex items-center gap-2 p-3 bg-neutral-2 border border-neutral-6 rounded-lg w-[480px]">
      <button className="p-2 rounded-full hover:bg-neutral-4 text-neutral-9">
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
          />
        </svg>
      </button>
      <span className="flex-1 text-sm text-neutral-9">Type a message...</span>
      <PreferencesMenu
        selectedModel="claude-sonnet-4"
        availableModels={sampleModels}
        onModelChange={(id) => console.log("Model:", id)}
        thinkingLevel="medium"
        onThinkingLevelChange={(l) => console.log("Thinking:", l)}
        toolMode="auto"
        onToolModeChange={(m) => console.log("Tool mode:", m)}
        toolPreference="auto"
        onToolPreferenceChange={(p) => console.log("Tool pref:", p)}
        kbFocusMode="all"
        onKBFocusChange={(m) => console.log("KB:", m)}
        compact
      />
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
        story: "PreferencesMenu shown in context of a chat input form.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <div className="flex items-center gap-4">
        <PreferencesMenu
          selectedModel="claude-opus-4-5"
          availableModels={sampleModels}
          onModelChange={(id) => console.log("Model:", id)}
          thinkingLevel="high"
          onThinkingLevelChange={(l) => console.log("Thinking:", l)}
          toolMode="auto"
          onToolModeChange={(m) => console.log("Tool mode:", m)}
          toolPreference="auto"
          onToolPreferenceChange={(p) => console.log("Tool pref:", p)}
          kbFocusMode="all"
          onKBFocusChange={(m) => console.log("KB:", m)}
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
        story: "PreferencesMenu in dark mode context.",
      },
    },
  },
};

// =============================================================================
// Accessibility Story
// =============================================================================

export const AccessibilityShowcase: Story = {
  render: () => (
    <div className="p-4 space-y-6 max-w-md">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-neutral-11">
          Accessibility Features
        </h3>
        <ul className="text-xs text-neutral-11 list-disc list-inside space-y-1">
          <li>Radix UI DropdownMenu for full WCAG 2.1 AA compliance</li>
          <li>Keyboard navigable (Arrow keys, Enter, Escape)</li>
          <li>ArrowRight opens submenu, ArrowLeft closes</li>
          <li>Roving tabindex for efficient focus management</li>
          <li>Role="menu", role="menuitemradio" semantics</li>
          <li>motion-reduce respects prefers-reduced-motion</li>
          <li>Touch targets meet 32px minimum (WCAG 2.5.8)</li>
        </ul>
      </div>
      <div className="pt-4 border-t border-neutral-6">
        <PreferencesMenu
          selectedModel="claude-sonnet-4"
          availableModels={sampleModels}
          onModelChange={(id) => console.log("Model:", id)}
          thinkingLevel="medium"
          onThinkingLevelChange={(l) => console.log("Thinking:", l)}
          toolMode="auto"
          onToolModeChange={(m) => console.log("Tool mode:", m)}
          toolPreference="auto"
          onToolPreferenceChange={(p) => console.log("Tool pref:", p)}
          kbFocusMode="all"
          onKBFocusChange={(m) => console.log("KB:", m)}
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
        story:
          "Demonstrates accessibility features of the hierarchical PreferencesMenu.",
      },
    },
  },
};

// =============================================================================
// All Settings Showcase
// =============================================================================

export const AllSettingsOpen: Story = {
  render: () => (
    <div className="p-4 space-y-4">
      <h3 className="text-sm font-semibold text-neutral-11">
        Menu Hierarchy Overview
      </h3>
      <div className="text-xs text-neutral-10 font-mono bg-neutral-3 p-3 rounded-md space-y-1">
        <div>PreferencesMenu (Main)</div>
        <div className="pl-4">
          {"\u251C\u2500\u2500"} Model: Claude Sonnet 4 → [Model List Submenu]
        </div>
        <div className="pl-4">
          {"\u251C\u2500\u2500"} Thinking: Medium → [Low/Medium/High Submenu]
        </div>
        <div className="pl-4">
          {"\u251C\u2500\u2500"} Tools: Auto → [Submenu with nested Provider]
        </div>
        <div className="pl-8">{"\u251C\u2500\u2500"} Auto / Manual / None</div>
        <div className="pl-8">
          {"\u2514\u2500\u2500"} Provider: Auto → [Sub-submenu]
        </div>
        <div className="pl-4">
          {"\u2514\u2500\u2500"} KB: All Sources → [All/KB Only/Web/None]
        </div>
      </div>
      <div className="pt-4">
        <PreferencesMenu
          selectedModel="claude-sonnet-4"
          availableModels={sampleModels}
          onModelChange={(id) => console.log("Model:", id)}
          thinkingLevel="medium"
          onThinkingLevelChange={(l) => console.log("Thinking:", l)}
          toolMode="auto"
          onToolModeChange={(m) => console.log("Tool mode:", m)}
          toolPreference="auto"
          onToolPreferenceChange={(p) => console.log("Tool pref:", p)}
          kbFocusMode="all"
          onKBFocusChange={(m) => console.log("KB:", m)}
        />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "Visual representation of the menu hierarchy. Click to explore the actual menu.",
      },
    },
  },
};
