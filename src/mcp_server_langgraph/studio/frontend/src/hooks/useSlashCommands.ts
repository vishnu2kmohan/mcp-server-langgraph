/**
 * useSlashCommands Hook
 *
 * Provides slash commands for the chat input by combining:
 * 1. Built-in commands (help, clear, export, etc.)
 * 2. Workflow templates from the backend API
 *
 * Usage:
 *   const { commands, isLoading, handleSelect } = useSlashCommands({
 *     onTemplateSelect: (template) => { ... },
 *     onBuiltInCommand: (command) => { ... },
 *   });
 */

import { useMemo, useCallback } from "react";
import { useGetWorkflowTemplatesQuery } from "../api";
import type {
  SlashCommand,
  CommandIcon,
} from "../components/Chat/SlashCommandMenu";

// =============================================================================
// Types
// =============================================================================

export interface TemplateSelectEvent {
  /** Template ID from the backend */
  templateId: string;
  /** Template name */
  name: string;
  /** Template category */
  category: string;
}

export interface UseSlashCommandsOptions {
  /** Callback when a template command is selected */
  onTemplateSelect?: (template: TemplateSelectEvent) => void;
  /** Callback when a built-in command is selected */
  onBuiltInCommand?: (command: SlashCommand) => void;
  /** Whether to skip fetching templates (e.g., for tests) */
  skipTemplates?: boolean;
}

export interface UseSlashCommandsResult {
  /** All available slash commands */
  commands: SlashCommand[];
  /** Whether templates are being loaded */
  isLoading: boolean;
  /** Handle command selection */
  handleSelect: (command: SlashCommand) => void;
  /** Error if template fetch failed */
  error: Error | null;
}

// =============================================================================
// Built-in Commands
// =============================================================================

const BUILT_IN_COMMANDS: SlashCommand[] = [
  {
    name: "help",
    description: "Show available commands and usage help",
    icon: "help",
    shortcut: "?",
  },
  {
    name: "clear",
    description: "Clear the current conversation",
    icon: "trash",
  },
  {
    name: "export",
    description: "Export the conversation as text or JSON",
    icon: "download",
  },
  {
    name: "copy",
    description: "Copy the last response to clipboard",
    icon: "copy",
  },
  {
    name: "settings",
    description: "Open settings panel",
    icon: "settings",
  },
  {
    name: "refresh",
    description: "Refresh the current session",
    icon: "refresh",
  },
];

// =============================================================================
// Template to Command Conversion
// =============================================================================

/**
 * Convert a template name to a command name.
 * "Simple Chatbot" -> "simple-chatbot" -> "chatbot" (simplified)
 */
function templateToCommandName(name: string): string {
  // Remove common prefixes and convert to lowercase slug
  let slug = name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim();

  // Remove common prefixes like "simple-", "basic-", "advanced-"
  const prefixes = ["simple-", "basic-", "advanced-", "custom-"];
  for (const prefix of prefixes) {
    if (slug.startsWith(prefix)) {
      slug = slug.slice(prefix.length);
      break;
    }
  }

  return slug;
}

/**
 * Get an icon for a template category.
 */
function getCategoryIcon(category: string): CommandIcon {
  const categoryIconMap: Record<string, CommandIcon> = {
    chat: "message",
    chatbot: "message",
    retrieval: "file-text",
    rag: "file-text",
    agents: "settings",
    workflow: "refresh",
    default: "message",
  };

  const icon =
    categoryIconMap[category.toLowerCase()] ?? categoryIconMap["default"];
  return icon ?? "message";
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useSlashCommands(
  options: UseSlashCommandsOptions = {},
): UseSlashCommandsResult {
  const { onTemplateSelect, onBuiltInCommand, skipTemplates = false } = options;

  // Fetch workflow templates from backend
  const {
    data: templates,
    isLoading,
    error,
  } = useGetWorkflowTemplatesQuery(undefined, {
    skip: skipTemplates,
  });

  // Convert templates to slash commands
  const templateCommands = useMemo((): SlashCommand[] => {
    if (!templates) return [];

    return templates.map((template) => ({
      name: templateToCommandName(template.name),
      description: template.description,
      icon: getCategoryIcon(template.category),
      // Store template ID in a data attribute for selection
      // We'll use the name to match back to the template
    }));
  }, [templates]);

  // Combine built-in and template commands
  const commands = useMemo(() => {
    // Built-in commands come first
    return [...BUILT_IN_COMMANDS, ...templateCommands];
  }, [templateCommands]);

  // Handle command selection
  const handleSelect = useCallback(
    (command: SlashCommand) => {
      // Check if it's a built-in command
      const isBuiltIn = BUILT_IN_COMMANDS.some((c) => c.name === command.name);

      if (isBuiltIn) {
        onBuiltInCommand?.(command);
      } else {
        // Find the matching template
        const template = templates?.find(
          (t) => templateToCommandName(t.name) === command.name,
        );

        if (template) {
          onTemplateSelect?.({
            templateId: template.id,
            name: template.name,
            category: template.category,
          });
        }
      }
    },
    [templates, onTemplateSelect, onBuiltInCommand],
  );

  return {
    commands,
    isLoading,
    handleSelect,
    error: error ? new Error(String(error)) : null,
  };
}

export default useSlashCommands;
