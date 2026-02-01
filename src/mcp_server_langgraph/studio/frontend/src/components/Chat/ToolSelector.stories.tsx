/**
 * ToolSelector Component Stories
 *
 * Storybook stories for the manual tool selection dropdown that allows users
 * to override semantic tool search with explicit tool choices.
 *
 * Features:
 * - Mode toggle (Auto/Manual/None)
 * - Search filtering
 * - Multi-select with checkboxes
 * - Grouped by source (built-in, MCP servers)
 *
 * @see Manual Tool Selection plan for architecture details
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { ToolSelector, type ToolOption } from "./ToolSelector";

// =============================================================================
// Sample Data
// =============================================================================

const SAMPLE_TOOLS: ToolOption[] = [
  // Built-in tools
  {
    name: "calculator",
    toolId: "builtin:calculator",
    displayName: "Calculator",
    source: "builtin",
    description: "Perform mathematical calculations",
    category: "math",
  },
  {
    name: "search_knowledge_base",
    toolId: "builtin:search_knowledge_base",
    displayName: "Search Knowledge Base",
    source: "builtin",
    description: "Search the knowledge base for relevant information",
    category: "search",
  },
  {
    name: "web_search",
    toolId: "builtin:web_search",
    displayName: "Web Search",
    source: "builtin",
    description: "Search the web for information",
    category: "search",
  },
  {
    name: "read_file",
    toolId: "builtin:read_file",
    displayName: "Read File",
    source: "builtin",
    description: "Read contents of a file",
    category: "filesystem",
  },
  {
    name: "list_directory",
    toolId: "builtin:list_directory",
    displayName: "List Directory",
    source: "builtin",
    description: "List files in a directory",
    category: "filesystem",
  },
  // MCP tools - GitHub server
  {
    name: "github:create_issue",
    toolId: "github:create_issue",
    displayName: "Create Issue",
    source: "mcp",
    serverName: "github",
    description: "Create a new GitHub issue",
    category: "github",
  },
  {
    name: "github:list_repos",
    toolId: "github:list_repos",
    displayName: "List Repositories",
    source: "mcp",
    serverName: "github",
    description: "List GitHub repositories",
    category: "github",
  },
  {
    name: "github:create_pr",
    toolId: "github:create_pr",
    displayName: "Create Pull Request",
    source: "mcp",
    serverName: "github",
    description: "Create a new pull request",
    category: "github",
  },
  // MCP tools - Slack server
  {
    name: "slack:send_message",
    toolId: "slack:send_message",
    displayName: "Send Message",
    source: "mcp",
    serverName: "slack",
    description: "Send a message to a Slack channel",
    category: "slack",
  },
  {
    name: "slack:list_channels",
    toolId: "slack:list_channels",
    displayName: "List Channels",
    source: "mcp",
    serverName: "slack",
    description: "List available Slack channels",
    category: "slack",
  },
];

// =============================================================================
// Meta
// =============================================================================

const meta: Meta<typeof ToolSelector> = {
  title: "Chat/ToolSelector",
  component: ToolSelector,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Manual tool selection dropdown for chat input. Allows users to override " +
          "semantic tool search with explicit tool choices. Supports three modes: " +
          "Auto (semantic search), Manual (explicit selection), and None (disabled).",
      },
    },
  },
  argTypes: {
    mode: {
      control: "select",
      options: ["auto", "manual", "none"],
      description: "Current selection mode",
    },
    isLoading: {
      control: "boolean",
      description: "Whether tools are loading",
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
type Story = StoryObj<typeof ToolSelector>;

// =============================================================================
// Basic States
// =============================================================================

export const Default: Story = {
  args: {
    selectedTools: [],
    mode: "auto",
    availableTools: SAMPLE_TOOLS,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Default state in Auto mode. Tools are automatically selected based on message content using semantic search.",
      },
    },
  },
};

export const ManualModeEmpty: Story = {
  args: {
    selectedTools: [],
    mode: "manual",
    availableTools: SAMPLE_TOOLS,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Manual mode with no tools selected. The pill shows 'Select' to indicate tools need to be chosen.",
      },
    },
  },
};

export const ManualModeWithSelection: Story = {
  args: {
    selectedTools: ["calculator", "web_search", "github:create_issue"],
    mode: "manual",
    availableTools: SAMPLE_TOOLS,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Manual mode with 3 tools selected. The pill shows the count (3) to indicate active selections.",
      },
    },
  },
};

export const NoneMode: Story = {
  args: {
    selectedTools: [],
    mode: "none",
    availableTools: SAMPLE_TOOLS,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "None mode - tools are disabled. The AI will respond without tool access.",
      },
    },
  },
};

// =============================================================================
// Loading & Disabled States
// =============================================================================

export const Loading: Story = {
  args: {
    selectedTools: [],
    mode: "auto",
    availableTools: [],
    isLoading: true,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story: "Loading state while tools are being fetched from the server.",
      },
    },
  },
};

export const Disabled: Story = {
  args: {
    selectedTools: ["calculator"],
    mode: "manual",
    availableTools: SAMPLE_TOOLS,
    disabled: true,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story: "Disabled state when chat is processing a message.",
      },
    },
  },
};

// =============================================================================
// Compact Mode
// =============================================================================

export const Compact: Story = {
  args: {
    selectedTools: ["calculator", "web_search"],
    mode: "manual",
    availableTools: SAMPLE_TOOLS,
    compact: true,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Compact mode for use in tight spaces like the chat input controls row.",
      },
    },
  },
};

// =============================================================================
// Context Stories
// =============================================================================

export const InChatInputControls: Story = {
  render: () => (
    <div className="w-[600px] flex items-center gap-2 px-4 py-2 bg-neutral-2 border border-neutral-6 rounded-lg">
      <span className="text-xs text-neutral-11">Model: Claude Opus 4.5</span>
      <span className="text-neutral-6">|</span>
      <span className="text-xs text-neutral-11">KB: All</span>
      <span className="text-neutral-6">|</span>
      <ToolSelector
        selectedTools={["calculator", "web_search"]}
        mode="manual"
        availableTools={SAMPLE_TOOLS}
        onSelectionChange={(tools) => console.log("Selection changed:", tools)}
        onModeChange={(mode) => console.log("Mode changed:", mode)}
        compact
      />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story:
          "ToolSelector in its typical context: the chat input controls row alongside model and KB focus selectors.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <ToolSelector
        selectedTools={["github:create_issue", "slack:send_message"]}
        mode="manual"
        availableTools={SAMPLE_TOOLS}
        onSelectionChange={(tools) => console.log("Selection changed:", tools)}
        onModeChange={(mode) => console.log("Mode changed:", mode)}
      />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "ToolSelector in dark mode context.",
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
          <li>Full keyboard navigation (Tab, Enter, Escape)</li>
          <li>ARIA listbox pattern for tool selection</li>
          <li>ARIA option roles for mode toggle buttons</li>
          <li>Checkbox labels for screen readers</li>
          <li>Focus management in dropdown</li>
          <li>aria-expanded and aria-haspopup states</li>
        </ul>
      </div>
      <div className="pt-4 border-t border-neutral-6">
        <ToolSelector
          selectedTools={[]}
          mode="manual"
          availableTools={SAMPLE_TOOLS}
          onSelectionChange={(tools) =>
            console.log("Selection changed:", tools)
          }
          onModeChange={(mode) => console.log("Mode changed:", mode)}
        />
        <p className="mt-3 text-xs text-neutral-10">
          Try: Tab to focus → Enter to open → Tab through options → Space to
          toggle
        </p>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Demonstrates accessibility features of the ToolSelector.",
      },
    },
  },
};

// =============================================================================
// Mode Comparison
// =============================================================================

export const ModeComparison: Story = {
  render: () => (
    <div className="space-y-4 p-4">
      <h3 className="text-sm font-semibold text-neutral-11">
        Selection Mode Comparison
      </h3>
      <div className="space-y-3">
        <div className="flex items-center gap-4">
          <span className="w-20 text-xs text-neutral-10">Auto:</span>
          <ToolSelector
            selectedTools={[]}
            mode="auto"
            availableTools={SAMPLE_TOOLS}
            onSelectionChange={() => {}}
            onModeChange={() => {}}
          />
        </div>
        <div className="flex items-center gap-4">
          <span className="w-20 text-xs text-neutral-10">Manual (0):</span>
          <ToolSelector
            selectedTools={[]}
            mode="manual"
            availableTools={SAMPLE_TOOLS}
            onSelectionChange={() => {}}
            onModeChange={() => {}}
          />
        </div>
        <div className="flex items-center gap-4">
          <span className="w-20 text-xs text-neutral-10">Manual (3):</span>
          <ToolSelector
            selectedTools={["calculator", "web_search", "read_file"]}
            mode="manual"
            availableTools={SAMPLE_TOOLS}
            onSelectionChange={() => {}}
            onModeChange={() => {}}
          />
        </div>
        <div className="flex items-center gap-4">
          <span className="w-20 text-xs text-neutral-10">None:</span>
          <ToolSelector
            selectedTools={[]}
            mode="none"
            availableTools={SAMPLE_TOOLS}
            onSelectionChange={() => {}}
            onModeChange={() => {}}
          />
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Side-by-side comparison of all selection mode displays.",
      },
    },
  },
};

// =============================================================================
// Empty State
// =============================================================================

export const NoToolsAvailable: Story = {
  args: {
    selectedTools: [],
    mode: "manual",
    availableTools: [],
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Manual mode with no tools available. Shows 'No tools found' message in dropdown.",
      },
    },
  },
};

// =============================================================================
// Many Tools
// =============================================================================

const MANY_TOOLS: ToolOption[] = [
  ...SAMPLE_TOOLS,
  {
    name: "execute_python",
    toolId: "builtin:execute_python",
    displayName: "Execute Python",
    source: "builtin",
    description: "Execute Python code in a sandbox",
    category: "code",
  },
  {
    name: "execute_bash",
    toolId: "builtin:execute_bash",
    displayName: "Execute Bash",
    source: "builtin",
    description: "Execute Bash commands in a sandbox",
    category: "code",
  },
  {
    name: "write_file",
    toolId: "builtin:write_file",
    displayName: "Write File",
    source: "builtin",
    description: "Write content to a file",
    category: "filesystem",
  },
  {
    name: "edit_file",
    toolId: "builtin:edit_file",
    displayName: "Edit File",
    source: "builtin",
    description: "Edit an existing file",
    category: "filesystem",
  },
  {
    name: "jira:create_ticket",
    toolId: "jira:create_ticket",
    displayName: "Create Ticket",
    source: "mcp",
    serverName: "jira",
    description: "Create a new Jira ticket",
  },
  {
    name: "jira:update_ticket",
    toolId: "jira:update_ticket",
    displayName: "Update Ticket",
    source: "mcp",
    serverName: "jira",
    description: "Update an existing Jira ticket",
  },
  {
    name: "confluence:create_page",
    toolId: "confluence:create_page",
    displayName: "Create Page",
    source: "mcp",
    serverName: "confluence",
    description: "Create a new Confluence page",
  },
];

export const ManyTools: Story = {
  args: {
    selectedTools: [],
    mode: "manual",
    availableTools: MANY_TOOLS,
    onSelectionChange: (tools) => console.log("Selection changed:", tools),
    onModeChange: (mode) => console.log("Mode changed:", mode),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Selector with many tools from multiple sources. Demonstrates search filtering and scrolling.",
      },
    },
  },
};
