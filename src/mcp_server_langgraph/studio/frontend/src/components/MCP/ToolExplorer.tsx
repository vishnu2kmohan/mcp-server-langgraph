/**
 * ToolExplorer Component
 *
 * Browse and invoke aggregated tools from all connected MCP servers.
 * Supports the MCP Protocol 2025-11-25 capability aggregation feature.
 */

import { useState, useMemo } from "react";
import { useListAggregatedToolsQuery } from "../../api";
import { Badge } from "../UI/Badge";
import { Card } from "../UI/Card";

import { Button, Input } from "@/components/UI";

export interface ToolExplorerProps {
  /** Optional filter by server name */
  serverFilter?: string;
  /** Callback when invoke button is clicked */
  onInvoke?: (qualifiedName: string) => void;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * ToolExplorer component for browsing and invoking aggregated tools
 */
export function ToolExplorer({ serverFilter, onInvoke }: ToolExplorerProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const { data, isLoading, error } = useListAggregatedToolsQuery(serverFilter);

  // Filter tools by search term
  const filteredTools = useMemo(() => {
    if (!data?.tools) return [];

    const term = searchTerm.toLowerCase();
    if (!term) return data.tools;

    return data.tools.filter(
      (tool) =>
        tool.qualifiedName.toLowerCase().includes(term) ||
        tool.name.toLowerCase().includes(term) ||
        tool.description.toLowerCase().includes(term) ||
        tool.serverName.toLowerCase().includes(term),
    );
  }, [data?.tools, searchTerm]);

  const handleInvoke = (qualifiedName: string) => {
    onInvoke?.(qualifiedName);
  };

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center p-8"
        data-testid="loading-spinner"
      >
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-error-9">
        Failed to load tools. Please try again.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Search input */}
      <div className="relative">
        <Input
          placeholder="Search tools..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={cn(
            "w-full px-4 py-2 rounded-lg border",
            "border-neutral-5",
            "bg-neutral-1",
            "text-neutral-12",
            "placeholder-neutral-9",
            "focus:outline-none focus:ring-2 focus:ring-brand-primary",
          )}
        />
        <svg
          className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-9"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>
      {/* Tool list */}
      <div className="flex flex-col gap-2">
        {filteredTools.length === 0 ? (
          <div className="p-4 text-center text-neutral-10">
            No tools found
          </div>
        ) : (
          filteredTools.map((tool) => (
            <Card
              key={tool.qualifiedName}
              variant="default"
              padding="sm"
              className="hover:bg-neutral-1 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                {/* Tool info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm font-medium text-neutral-12">
                      {tool.qualifiedName}
                    </span>
                    <Badge variant="outline" size="sm">
                      {tool.serverName}
                    </Badge>
                  </div>
                  <p className="text-sm text-neutral-11 line-clamp-2">
                    {tool.description}
                  </p>
                </div>

                {/* Invoke button */}
                <Button
                  type="button"
                  onClick={() => handleInvoke(tool.qualifiedName)}
                  className={cn(
                    "shrink-0 px-3 py-1.5 text-sm font-medium rounded-md",
                    "bg-brand-primary text-neutral-12",
                    "hover:bg-brand-primary/90",
                    "focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2",
                    "transition-colors",
                  )}
                >
                  Invoke
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
