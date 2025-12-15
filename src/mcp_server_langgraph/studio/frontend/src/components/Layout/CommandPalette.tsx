/**
 * CommandPalette Component
 *
 * Cmd+K command palette for quick navigation and actions.
 * Features:
 * - Keyboard shortcut activation (Cmd+K / Ctrl+K)
 * - Search filtering
 * - Grouped commands by category
 * - RBAC-based command visibility
 * - Keyboard navigation (arrow keys, enter, escape)
 */

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useNavigate } from "react-router";
import {
  Search,
  MessageSquare,
  FolderKanban,
  GitBranch,
  Activity,
  DollarSign,
  Settings,
  LayoutDashboard,
  Plus,
  Trash2,
  Puzzle,
  Database,
  Cpu,
  Sparkles,
  Mic,
  Lightbulb,
  Share2,
} from "lucide-react";
import { useAppSelector } from "../../store/hooks";
import { selectUser } from "../../store/slices/authSlice";
import { selectPersona } from "../../store/slices/personaSlice";
import type { Persona } from "../../types/auth";

/**
 * Command definition
 */
interface Command {
  id: string;
  label: string;
  shortcut?: string;
  icon: React.ReactNode;
  group: CommandGroup;
  action: () => void;
  personas: Persona[];
}

type CommandGroup =
  | "ai"
  | "chat"
  | "workflow"
  | "navigation"
  | "connections"
  | "admin";

const GROUP_LABELS: Record<CommandGroup, string> = {
  ai: "AI",
  chat: "CHAT",
  workflow: "WORKFLOW",
  navigation: "NAVIGATION",
  connections: "CONNECTIONS",
  admin: "ADMIN",
};

const GROUP_ORDER: CommandGroup[] = [
  "ai",
  "chat",
  "workflow",
  "navigation",
  "connections",
  "admin",
];

/**
 * Check if running on Mac
 */
const isMac =
  typeof navigator !== "undefined" &&
  navigator.platform.toUpperCase().indexOf("MAC") >= 0;
const modKey = isMac ? "⌘" : "Ctrl+";

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Get persona from auth or persona slice
  const authUser = useAppSelector(selectUser);
  const personaFromSlice = useAppSelector(selectPersona);
  const persona: Persona = authUser?.persona ?? personaFromSlice ?? "user";

  // Define commands
  const allCommands: Command[] = useMemo(
    () => [
      // AI commands
      {
        id: "ask-ai",
        label: "Ask AI Assistant",
        shortcut: `${modKey}I`,
        icon: <Sparkles size={16} />,
        group: "ai",
        action: () => {
          navigate("/studio/chat");
        },
        personas: ["admin", "developer", "user"],
      },
      {
        id: "ai-suggestions",
        label: "Get AI Suggestions",
        shortcut: `${modKey}Shift+I`,
        icon: <Lightbulb size={16} />,
        group: "ai",
        action: () => {
          navigate("/studio/workflows?suggestions=true");
        },
        personas: ["admin", "developer"],
      },
      {
        id: "voice-input",
        label: "Toggle Voice Input",
        shortcut: `${modKey}Shift+V`,
        icon: <Mic size={16} />,
        group: "ai",
        action: () => {
          navigate("/studio/chat?voice=true");
        },
        personas: ["admin", "developer", "user"],
      },

      // CHAT commands
      {
        id: "new-session",
        label: "New Session",
        shortcut: `${modKey}N`,
        icon: <Plus size={16} />,
        group: "chat",
        action: () => {
          navigate("/studio/chat?new=true");
        },
        personas: ["admin", "developer", "user"],
      },
      {
        id: "clear-messages",
        label: "Clear Messages",
        shortcut: `${modKey}L`,
        icon: <Trash2 size={16} />,
        group: "chat",
        action: () => {
          // This would dispatch a clear action - for now just navigate
          navigate("/studio/chat");
        },
        personas: ["admin", "developer", "user"],
      },

      // WORKFLOW commands
      {
        id: "new-workflow",
        label: "New Workflow",
        shortcut: `${modKey}Shift+N`,
        icon: <Plus size={16} />,
        group: "workflow",
        action: () => {
          navigate("/studio/workflows?new=true");
        },
        personas: ["admin", "developer"],
      },
      {
        id: "go-workflows",
        label: "Go to Workflows",
        shortcut: "G then W",
        icon: <GitBranch size={16} />,
        group: "workflow",
        action: () => {
          navigate("/studio/workflows");
        },
        personas: ["admin", "developer"],
      },
      {
        id: "shared-workflows",
        label: "Shared Workflows",
        icon: <Share2 size={16} />,
        group: "workflow",
        action: () => {
          navigate("/studio/shared-workflows");
        },
        personas: ["admin", "developer", "user"],
      },

      // NAVIGATION commands
      {
        id: "go-chat",
        label: "Go to Chat",
        shortcut: "G then C",
        icon: <MessageSquare size={16} />,
        group: "navigation",
        action: () => {
          navigate("/studio/chat");
        },
        personas: ["admin", "developer", "user"],
      },
      {
        id: "go-projects",
        label: "Go to Projects",
        shortcut: "G then P",
        icon: <FolderKanban size={16} />,
        group: "navigation",
        action: () => {
          navigate("/studio/projects");
        },
        personas: ["admin", "developer", "user"],
      },
      {
        id: "go-observability",
        label: "Go to Observability",
        shortcut: `${modKey}Shift+T`,
        icon: <Activity size={16} />,
        group: "navigation",
        action: () => {
          navigate("/studio/observability");
        },
        personas: ["admin", "developer"],
      },
      {
        id: "go-cost",
        label: "Go to Cost",
        shortcut: `${modKey}$`,
        icon: <DollarSign size={16} />,
        group: "navigation",
        action: () => {
          navigate("/studio/cost");
        },
        personas: ["admin", "developer"],
      },
      {
        id: "go-settings",
        label: "Go to Settings",
        shortcut: "G then S",
        icon: <Settings size={16} />,
        group: "navigation",
        action: () => {
          navigate("/studio/settings");
        },
        personas: ["admin", "developer"],
      },

      // CONNECTIONS commands
      {
        id: "go-mcp",
        label: "Go to MCP Explorer",
        shortcut: `${modKey}Shift+M`,
        icon: <Puzzle size={16} />,
        group: "connections",
        action: () => {
          navigate("/studio/connections/mcp");
        },
        personas: ["admin", "developer"],
      },
      {
        id: "go-agents",
        label: "Go to Agents",
        icon: <Cpu size={16} />,
        group: "connections",
        action: () => {
          navigate("/studio/connections/agents");
        },
        personas: ["admin", "developer"],
      },
      {
        id: "go-vectors",
        label: "Go to Vectors",
        icon: <Database size={16} />,
        group: "connections",
        action: () => {
          navigate("/studio/connections/vectors");
        },
        personas: ["admin", "developer"],
      },

      // ADMIN commands
      {
        id: "go-admin",
        label: "Go to Admin Dashboard",
        icon: <LayoutDashboard size={16} />,
        group: "admin",
        action: () => {
          navigate("/studio/admin/dashboard");
        },
        personas: ["admin"],
      },
    ],
    [navigate],
  );

  // Filter commands by persona and search
  const filteredCommands = useMemo(() => {
    return allCommands
      .filter((cmd) => cmd.personas.includes(persona))
      .filter((cmd) => {
        if (!search) return true;
        const searchLower = search.toLowerCase();
        return (
          cmd.label.toLowerCase().includes(searchLower) ||
          cmd.group.toLowerCase().includes(searchLower)
        );
      });
  }, [allCommands, persona, search]);

  // Group filtered commands
  const groupedCommands = useMemo(() => {
    const groups: Record<CommandGroup, Command[]> = {
      ai: [],
      chat: [],
      workflow: [],
      navigation: [],
      connections: [],
      admin: [],
    };

    filteredCommands.forEach((cmd) => {
      groups[cmd.group].push(cmd);
    });

    return groups;
  }, [filteredCommands]);

  // Get visible groups (non-empty)
  const visibleGroups = useMemo(() => {
    return GROUP_ORDER.filter((group) => groupedCommands[group].length > 0);
  }, [groupedCommands]);

  // Flatten commands for keyboard navigation
  const flatCommands = useMemo(() => {
    return visibleGroups.flatMap((group) => groupedCommands[group]);
  }, [visibleGroups, groupedCommands]);

  // Execute a command
  const executeCommand = useCallback((command: Command) => {
    command.action();
    setIsOpen(false);
  }, []);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Open on Cmd+K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen(true);
        setSearch("");
        setSelectedIndex(0);
        return;
      }

      if (!isOpen) return;

      // Close on Escape
      if (e.key === "Escape") {
        e.preventDefault();
        setIsOpen(false);
        return;
      }

      // Navigate with arrow keys
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, flatCommands.length - 1));
        return;
      }

      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        return;
      }

      // Execute on Enter
      if (e.key === "Enter") {
        e.preventDefault();
        if (flatCommands[selectedIndex]) {
          executeCommand(flatCommands[selectedIndex]);
        }
        return;
      }
    },
    [isOpen, flatCommands, selectedIndex, executeCommand],
  );

  // Register keyboard listener
  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Reset selection when search changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
    >
      {/* Backdrop */}
      <div
        data-testid="command-palette-backdrop"
        className="absolute inset-0 bg-black/50"
        onClick={() => setIsOpen(false)}
      />

      {/* Palette */}
      <div className="relative w-full max-w-lg bg-white dark:bg-gray-800 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <Search size={18} className="text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search commands..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
          />
          <kbd className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded">
            {isMac ? "⌘" : "Ctrl"}K
          </kbd>
        </div>

        {/* Commands List */}
        <div className="max-h-80 overflow-y-auto py-2">
          {visibleGroups.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
              No commands found
            </div>
          ) : (
            visibleGroups.map((group) => (
              <div key={group} className="mb-2">
                {/* Group Header */}
                <div className="px-4 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {GROUP_LABELS[group]}
                </div>

                {/* Commands */}
                {groupedCommands[group].map((command) => {
                  const globalIndex = flatCommands.indexOf(command);
                  const isSelected = globalIndex === selectedIndex;

                  return (
                    <button
                      key={command.id}
                      onClick={() => executeCommand(command)}
                      data-selected={isSelected}
                      className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors ${
                        isSelected
                          ? "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400"
                          : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                      }`}
                    >
                      <span className="text-gray-400">{command.icon}</span>
                      <span className="flex-1">{command.label}</span>
                      {command.shortcut && (
                        <kbd className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded">
                          {command.shortcut}
                        </kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-4">
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
              ↑↓
            </kbd>
            <span>Navigate</span>
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
              ↵
            </kbd>
            <span>Select</span>
          </span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
              Esc
            </kbd>
            <span>Close</span>
          </span>
        </div>
      </div>
    </div>
  );
}
