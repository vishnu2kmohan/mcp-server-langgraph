/**
 * HeaderModelSelector Component Stories
 *
 * Storybook stories for the unified header-based model selector that combines
 * model selection and thinking level into a single compact control.
 *
 * Based on user research: ChatGPT/Gemini header-based pattern.
 * @see ADR-0102 for model selector consolidation decision
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { HeaderModelSelector } from "./HeaderModelSelector";
import type { ModelOption } from "./HeaderModelSelector";

// =============================================================================
// Sample Data
// =============================================================================

const SAMPLE_MODELS: ModelOption[] = [
  {
    id: "claude-opus-4.5",
    name: "Claude Opus 4.5",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "claude-sonnet-4",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    supportsThinking: false,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "preview",
  },
  {
    id: "claude-3-opus",
    name: "Claude 3 Opus",
    provider: "anthropic",
    supportsThinking: false,
    supportsVision: true,
    supportsTools: true,
    status: "legacy",
  },
  {
    id: "gpt-4-turbo",
    name: "GPT-4 Turbo",
    provider: "openai",
    supportsThinking: false,
    supportsVision: true,
    supportsTools: true,
    status: "deprecated",
    sunsetDate: "2025-06-30",
  },
];

// =============================================================================
// Meta
// =============================================================================

const meta: Meta<typeof HeaderModelSelector> = {
  title: "Chat/HeaderModelSelector",
  component: HeaderModelSelector,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Unified header-based model selector combining model selection and thinking level. " +
          "Follows ChatGPT/Gemini pattern with combined display: 'Claude Opus 4.5 (Medium)'.",
      },
    },
  },
  argTypes: {
    selectedModel: {
      control: "select",
      options: SAMPLE_MODELS.map((m) => m.id),
      description: "Currently selected model ID",
    },
    thinkingLevel: {
      control: "select",
      options: ["low", "medium", "high"],
      description: "Current thinking level for thinking-capable models",
    },
    isLoading: {
      control: "boolean",
      description: "Whether models are loading",
    },
    disabled: {
      control: "boolean",
      description: "Whether the selector is disabled",
    },
    compact: {
      control: "boolean",
      description: "Compact mode for smaller displays",
    },
  },
};

export default meta;
type Story = StoryObj<typeof HeaderModelSelector>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    selectedModel: "claude-opus-4.5",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "medium",
    onModelChange: (id) => console.log("Model changed to:", id),
    onThinkingLevelChange: (level) =>
      console.log("Thinking level changed to:", level),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default state with a thinking-capable model selected. Shows model name and thinking level.",
      },
    },
  },
};

export const HighThinking: Story = {
  args: {
    selectedModel: "claude-opus-4.5",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "high",
    onModelChange: (id) => console.log("Model changed to:", id),
    onThinkingLevelChange: (level) =>
      console.log("Thinking level changed to:", level),
  },
  parameters: {
    docs: {
      description: {
        story: "Thinking level set to High for deep, comprehensive analysis.",
      },
    },
  },
};

export const LowThinking: Story = {
  args: {
    selectedModel: "claude-opus-4.5",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "low",
    onModelChange: (id) => console.log("Model changed to:", id),
    onThinkingLevelChange: (level) =>
      console.log("Thinking level changed to:", level),
  },
  parameters: {
    docs: {
      description: {
        story: "Thinking level set to Low for quick responses.",
      },
    },
  },
};

// =============================================================================
// Non-Thinking Model
// =============================================================================

export const NonThinkingModel: Story = {
  args: {
    selectedModel: "gpt-4o",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "medium",
    onModelChange: (id) => console.log("Model changed to:", id),
    onThinkingLevelChange: (level) =>
      console.log("Thinking level changed to:", level),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Model without thinking support (GPT-4o). Thinking level indicator is hidden.",
      },
    },
  },
};

// =============================================================================
// Loading & Disabled States
// =============================================================================

export const Loading: Story = {
  args: {
    selectedModel: "claude-opus-4.5",
    availableModels: SAMPLE_MODELS,
    isLoading: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Loading state while models are being fetched.",
      },
    },
  },
};

export const Disabled: Story = {
  args: {
    selectedModel: "claude-opus-4.5",
    availableModels: SAMPLE_MODELS,
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

// =============================================================================
// Compact Mode
// =============================================================================

export const Compact: Story = {
  args: {
    selectedModel: "claude-opus-4.5",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "medium",
    compact: true,
    onModelChange: (id) => console.log("Model changed to:", id),
    onThinkingLevelChange: (level) =>
      console.log("Thinking level changed to:", level),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Compact mode shows abbreviated model name ('Opus 4.5' instead of 'Claude Opus 4.5').",
      },
    },
  },
};

// =============================================================================
// Model Status Badges
// =============================================================================

export const PreviewModel: Story = {
  args: {
    selectedModel: "gemini-2.5-pro",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "medium",
    onModelChange: (id) => console.log("Model changed to:", id),
  },
  parameters: {
    docs: {
      description: {
        story: "Model with preview status badge in dropdown.",
      },
    },
  },
};

export const LegacyModel: Story = {
  args: {
    selectedModel: "claude-3-opus",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "medium",
    onModelChange: (id) => console.log("Model changed to:", id),
  },
  parameters: {
    docs: {
      description: {
        story: "Model with legacy status badge in dropdown.",
      },
    },
  },
};

export const DeprecatedModel: Story = {
  args: {
    selectedModel: "gpt-4-turbo",
    availableModels: SAMPLE_MODELS,
    thinkingLevel: "medium",
    onModelChange: (id) => console.log("Model changed to:", id),
  },
  parameters: {
    docs: {
      description: {
        story: "Deprecated model with sunset date shown in dropdown.",
      },
    },
  },
};

// =============================================================================
// Context Stories
// =============================================================================

export const InSessionHeader: Story = {
  render: () => (
    <div className="w-[600px] flex items-center justify-between px-4 py-2 bg-neutral-2 border-b border-neutral-6 rounded-t-lg">
      <div className="flex items-center gap-3 min-w-0">
        <h2 className="text-sm font-medium text-neutral-12 truncate">
          New Conversation
        </h2>
        <HeaderModelSelector
          selectedModel="claude-opus-4.5"
          availableModels={SAMPLE_MODELS}
          thinkingLevel="medium"
          onModelChange={(id) => console.log("Model changed to:", id)}
          onThinkingLevelChange={(level) =>
            console.log("Thinking level changed to:", level)
          }
          compact
        />
      </div>
      <div className="flex items-center gap-2">
        <button className="p-1.5 text-neutral-10 hover:bg-neutral-4 rounded">
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
            />
          </svg>
        </button>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "HeaderModelSelector in its typical context: the session header alongside the conversation title.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <HeaderModelSelector
        selectedModel="claude-opus-4.5"
        availableModels={SAMPLE_MODELS}
        thinkingLevel="high"
        onModelChange={(id) => console.log("Model changed to:", id)}
        onThinkingLevelChange={(level) =>
          console.log("Thinking level changed to:", level)
        }
      />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "HeaderModelSelector in dark mode context.",
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
          <li>Full keyboard navigation (Tab, Arrow keys, Enter, Escape)</li>
          <li>ARIA listbox pattern for model selection</li>
          <li>ARIA radiogroup for thinking level selection</li>
          <li>Thinking badges with screen reader labels</li>
          <li>Focus trap and management in dropdown</li>
          <li>aria-expanded and aria-selected states</li>
        </ul>
      </div>
      <div className="pt-4 border-t border-neutral-6">
        <HeaderModelSelector
          selectedModel="claude-opus-4.5"
          availableModels={SAMPLE_MODELS}
          thinkingLevel="medium"
          onModelChange={(id) => console.log("Model changed to:", id)}
          onThinkingLevelChange={(level) =>
            console.log("Thinking level changed to:", level)
          }
        />
        <p className="mt-3 text-xs text-neutral-10">
          Try: Tab to focus → Enter to open → Arrow keys to navigate → Enter to
          select
        </p>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Demonstrates accessibility features of the HeaderModelSelector.",
      },
    },
  },
};

// =============================================================================
// All Thinking Levels Comparison
// =============================================================================

export const ThinkingLevelComparison: Story = {
  render: () => (
    <div className="space-y-4 p-4">
      <h3 className="text-sm font-semibold text-neutral-11">
        Thinking Level Comparison
      </h3>
      <div className="space-y-3">
        <div className="flex items-center gap-4">
          <span className="w-20 text-xs text-neutral-10">Low:</span>
          <HeaderModelSelector
            selectedModel="claude-opus-4.5"
            availableModels={SAMPLE_MODELS}
            thinkingLevel="low"
          />
        </div>
        <div className="flex items-center gap-4">
          <span className="w-20 text-xs text-neutral-10">Medium:</span>
          <HeaderModelSelector
            selectedModel="claude-opus-4.5"
            availableModels={SAMPLE_MODELS}
            thinkingLevel="medium"
          />
        </div>
        <div className="flex items-center gap-4">
          <span className="w-20 text-xs text-neutral-10">High:</span>
          <HeaderModelSelector
            selectedModel="claude-opus-4.5"
            availableModels={SAMPLE_MODELS}
            thinkingLevel="high"
          />
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Side-by-side comparison of all thinking level displays.",
      },
    },
  },
};
