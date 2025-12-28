/**
 * MCPServerCard Component
 *
 * Displays a summary of an MCP server's capabilities (tools, resources, prompts).
 * Supports the MCP Protocol 2025-11-25 capability aggregation feature.
 */

import { Card } from "../UI/Card";

export interface MCPServerCardProps {
  /** Name of the MCP server */
  serverName: string;
  /** Number of tools provided by this server */
  toolCount: number;
  /** Number of resources provided by this server */
  resourceCount: number;
  /** Number of prompts provided by this server */
  promptCount: number;
  /** Callback when the card is selected */
  onSelect: (serverName: string) => void;
  /** Optional className for styling */
  className?: string;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Tool icon for capability display
 */
function ToolIcon() {
  return (
    <svg
      data-testid="tool-icon"
      className="w-4 h-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );
}

/**
 * Resource icon for capability display
 */
function ResourceIcon() {
  return (
    <svg
      data-testid="resource-icon"
      className="w-4 h-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
      />
    </svg>
  );
}

/**
 * Prompt icon for capability display
 */
function PromptIcon() {
  return (
    <svg
      data-testid="prompt-icon"
      className="w-4 h-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
      />
    </svg>
  );
}

/**
 * Capability stat display
 */
function CapabilityStat({
  icon,
  count,
  label,
}: {
  icon: React.ReactNode;
  count: number;
  label: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-sm">
      <span className="text-gray-500 dark:text-gray-400">{icon}</span>
      <span className="font-medium text-gray-900 dark:text-gray-100">
        {count}
      </span>
      <span className="sr-only">{label}</span>
    </div>
  );
}

/**
 * MCPServerCard displays a summary of server capabilities
 */
export function MCPServerCard({
  serverName,
  toolCount,
  resourceCount,
  promptCount,
  onSelect,
  className,
}: MCPServerCardProps) {
  const handleClick = () => {
    onSelect(serverName);
  };

  return (
    <Card
      variant="default"
      padding="md"
      interactive
      className={cn("min-w-[200px]", className)}
    >
      <button
        type="button"
        onClick={handleClick}
        className="w-full text-left focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2 rounded-md"
      >
        {/* Server name */}
        <div className="mb-3">
          <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100 truncate">
            {serverName}
          </h4>
        </div>

        {/* Capability counts */}
        <div className="flex items-center gap-4">
          <CapabilityStat icon={<ToolIcon />} count={toolCount} label="tools" />
          <CapabilityStat
            icon={<ResourceIcon />}
            count={resourceCount}
            label="resources"
          />
          <CapabilityStat
            icon={<PromptIcon />}
            count={promptCount}
            label="prompts"
          />
        </div>
      </button>
    </Card>
  );
}
