/**
 * Help Page Data
 *
 * Constants for the help center and keyboard shortcuts.
 * Extracted from HelpPage.tsx to support React fast refresh.
 */

import type { HelpTopic } from "./HelpPane";
import type { ShortcutCategory } from "./KeyboardShortcuts";

// =============================================================================
// Default Help Topics
// =============================================================================

export const DEFAULT_HELP_TOPICS: HelpTopic[] = [
  {
    id: "getting-started",
    title: "Getting Started",
    category: "basics",
    content:
      "Welcome to the AI Studio! Start by typing a message in the chat input or use keyboard shortcuts to navigate.",
    keywords: ["start", "begin", "intro", "welcome", "tutorial"],
  },
  {
    id: "chat-basics",
    title: "Chat Basics",
    category: "basics",
    content:
      "Use the chat panel to communicate with AI agents. Type your message and press Enter to send. Use / for slash commands.",
    keywords: ["chat", "message", "send", "slash", "commands"],
  },
  {
    id: "canvas-workspace",
    title: "Canvas Workspace",
    category: "basics",
    content:
      "The canvas shows artifacts generated during your conversation. You can view, edit, and export code, documents, and more.",
    keywords: ["canvas", "artifact", "code", "edit", "export"],
  },
  {
    id: "keyboard-shortcuts",
    title: "Keyboard Shortcuts",
    category: "productivity",
    content:
      "Use Cmd+K to open the command palette, Cmd+/ to toggle the canvas, Cmd+I to toggle AI insights, and Escape to close dialogs.",
    keywords: ["keyboard", "shortcut", "hotkey", "cmd", "ctrl", "insights"],
  },
  {
    id: "sessions",
    title: "Sessions",
    category: "productivity",
    content:
      "Sessions save your conversation history. Create new sessions from the session nav or use Cmd+N.",
    keywords: ["session", "history", "save", "new", "conversation"],
  },
  {
    id: "compliance-overview",
    title: "Compliance Overview",
    category: "compliance",
    content:
      "Monitor compliance status for SOC2, GDPR, HIPAA, and FedRAMP frameworks in the Compliance dashboard.",
    keywords: ["compliance", "soc2", "gdpr", "hipaa", "fedramp", "audit"],
  },
  {
    id: "audit-logs",
    title: "Audit Logs",
    category: "compliance",
    content:
      "Access audit logs from the Admin panel to track user actions and system events.",
    keywords: ["audit", "logs", "admin", "track", "security"],
  },
  {
    id: "mcp-overview",
    title: "MCP Connections",
    category: "advanced",
    content:
      "Connect to external tools and resources via Model Context Protocol (MCP). MCP servers expose tools, resources, and prompts that extend AI capabilities. Use Cmd+M to toggle the MCP panel.",
    keywords: [
      "mcp",
      "model context protocol",
      "tools",
      "resources",
      "prompts",
      "connections",
      "servers",
    ],
  },
  {
    id: "mcp-tools",
    title: "MCP Tools",
    category: "advanced",
    content:
      "MCP tools are executable functions exposed by connected servers. Use Cmd+Shift+T to open the tool invocation dialog. Tools can read files, execute commands, query databases, and more.",
    keywords: ["mcp", "tools", "invoke", "execute", "function", "action"],
  },
  {
    id: "mcp-resources",
    title: "MCP Resources",
    category: "advanced",
    content:
      "MCP resources provide access to external data like files, documents, and API responses. Use Cmd+Shift+R to browse available resources. Resources can be text, images, or structured data.",
    keywords: ["mcp", "resources", "files", "data", "content", "read"],
  },
  {
    id: "mcp-prompts",
    title: "MCP Prompts",
    category: "advanced",
    content:
      "MCP prompts are reusable templates for common tasks. Use Cmd+Shift+P to test prompts. Prompts can include arguments that customize their behavior.",
    keywords: ["mcp", "prompts", "templates", "reusable", "test"],
  },
];

// =============================================================================
// Default Keyboard Shortcuts
// =============================================================================

export const DEFAULT_SHORTCUT_CATEGORIES: ShortcutCategory[] = [
  {
    id: "navigation",
    name: "Navigation",
    shortcuts: [
      {
        id: "command-palette",
        keys: ["Cmd", "K"],
        description: "Open command palette",
      },
      {
        id: "toggle-canvas",
        keys: ["Cmd", "/"],
        description: "Toggle canvas panel",
      },
      {
        id: "toggle-insights",
        keys: ["Cmd", "I"],
        description: "Toggle AI insights panel",
      },
      {
        id: "new-session",
        keys: ["Cmd", "N"],
        description: "Create new session",
      },
      {
        id: "close-dialog",
        keys: ["Esc"],
        description: "Close dialog or panel",
      },
    ],
  },
  {
    id: "chat",
    name: "Chat",
    shortcuts: [
      {
        id: "send-message",
        keys: ["Enter"],
        description: "Send message",
      },
      {
        id: "new-line",
        keys: ["Shift", "Enter"],
        description: "Insert new line",
      },
      {
        id: "slash-command",
        keys: ["/"],
        description: "Open slash command menu",
      },
    ],
  },
  {
    id: "canvas",
    name: "Canvas",
    shortcuts: [
      {
        id: "save-artifact",
        keys: ["Cmd", "S"],
        description: "Save artifact",
      },
      {
        id: "copy-artifact",
        keys: ["Cmd", "C"],
        description: "Copy selected content",
      },
      {
        id: "undo",
        keys: ["Cmd", "Z"],
        description: "Undo last change",
      },
      {
        id: "redo",
        keys: ["Cmd", "Shift", "Z"],
        description: "Redo last change",
      },
    ],
  },
  {
    id: "admin",
    name: "Admin Dashboard",
    shortcuts: [
      {
        id: "admin-overview",
        keys: ["Shift", "O"],
        description: "Go to Overview tab",
      },
      {
        id: "admin-users",
        keys: ["Shift", "U"],
        description: "Go to Users tab",
      },
      {
        id: "admin-alerts",
        keys: ["Shift", "A"],
        description: "Go to Alerts tab",
      },
    ],
  },
  {
    id: "mcp",
    name: "MCP (Model Context Protocol)",
    shortcuts: [
      {
        id: "mcp-toggle-panel",
        keys: ["Cmd", "M"],
        description: "Toggle MCP connections panel",
      },
      {
        id: "mcp-tool-dialog",
        keys: ["Cmd", "Shift", "T"],
        description: "Open tool invocation dialog",
      },
      {
        id: "mcp-resource-viewer",
        keys: ["Cmd", "Shift", "R"],
        description: "Open resource viewer",
      },
      {
        id: "mcp-prompt-tester",
        keys: ["Cmd", "Shift", "P"],
        description: "Open prompt tester",
      },
    ],
  },
];
