/**
 * ToolSelector Component
 *
 * Dropdown selector for manual tool selection in chat input.
 * Allows users to override semantic tool selection with explicit choices.
 *
 * Features:
 * - Mode toggle (Auto/Manual/None)
 * - Search filtering
 * - Multi-select with checkboxes
 * - Grouped by source (built-in) and server (MCP)
 * - Keyboard navigation
 * - ARIA listbox pattern for accessibility
 *
 * @see Manual Tool Selection plan for architecture details
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { ChevronDown, Search, Loader2, Wrench } from "lucide-react";
import { cn } from "../../utils/cn";
import type { ToolSelectionMode } from "@/types/tools";

import { Input } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

/** Simplified tool representation for the selector */
export interface ToolOption {
  /** Tool name for execution (LangChain-compatible name) */
  name: string;
  /** Unique tool identifier for selection (v7: REQUIRED - use for selection) */
  toolId: string;
  displayName: string;
  /** Tool source: builtin, mcp, or native (v7) */
  source: "builtin" | "mcp" | "native";
  serverName?: string;
  /** Native tool provider (v7: anthropic, google) */
  provider?: string;
  description?: string;
  category?: string;
}

export interface ToolSelectorProps {
  /** Currently selected tool IDs (v7: use tool_id for unique identification) */
  selectedTools: string[];
  /** Callback when selection changes */
  onSelectionChange: (tools: string[]) => void;
  /** Current selection mode */
  mode: ToolSelectionMode;
  /** Callback when mode changes */
  onModeChange: (mode: ToolSelectionMode) => void;
  /** Available tools for selection */
  availableTools?: ToolOption[];
  /** Whether tools are loading */
  isLoading?: boolean;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Compact mode for smaller displays */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const MODE_OPTIONS: { value: ToolSelectionMode; label: string; description: string }[] = [
  { value: "auto", label: "Auto", description: "Semantic search selects tools" },
  { value: "manual", label: "Manual", description: "You choose which tools to use" },
  { value: "none", label: "None", description: "No tools available" },
];

// =============================================================================
// Component
// =============================================================================

export function ToolSelector({
  selectedTools,
  onSelectionChange,
  mode,
  onModeChange,
  availableTools = [],
  isLoading = false,
  disabled = false,
  compact = false,
  className,
}: ToolSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Get display text for the button
  const displayText = useMemo(() => {
    if (mode === "none") return "None";
    if (mode === "auto") return "Auto";
    if (selectedTools.length === 0) return "Select";
    return `${selectedTools.length}`;
  }, [mode, selectedTools.length]);

  // Filter tools based on search term
  const filteredTools = useMemo(() => {
    if (!searchTerm.trim()) return availableTools;

    const term = searchTerm.toLowerCase().trim();
    return availableTools.filter(
      (tool) =>
        tool.name.toLowerCase().includes(term) ||
        tool.displayName.toLowerCase().includes(term) ||
        (tool.description && tool.description.toLowerCase().includes(term)) ||
        (tool.serverName && tool.serverName.toLowerCase().includes(term))
    );
  }, [availableTools, searchTerm]);

  // Group filtered tools by source (v7: includes native tools)
  const groupedTools = useMemo(() => {
    const builtin: ToolOption[] = [];
    const native: Record<string, ToolOption[]> = {}; // Grouped by provider
    const mcp: Record<string, ToolOption[]> = {};

    for (const tool of filteredTools) {
      if (tool.source === "builtin") {
        builtin.push(tool);
      } else if (tool.source === "native" && tool.provider) {
        // Group native tools by provider (e.g., "anthropic", "google")
        if (!native[tool.provider]) {
          native[tool.provider] = [];
        }
        native[tool.provider].push(tool);
      } else if (tool.source === "mcp" && tool.serverName) {
        if (!mcp[tool.serverName]) {
          mcp[tool.serverName] = [];
        }
        mcp[tool.serverName].push(tool);
      }
    }

    return { builtin, native, mcp };
  }, [filteredTools]);

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchTerm("");
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        setSearchTerm("");
        buttonRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && mode === "manual" && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen, mode]);

  // Handle toggle
  const handleToggle = useCallback(() => {
    if (disabled || isLoading) return;
    setIsOpen((prev) => !prev);
    if (isOpen) {
      setSearchTerm("");
    }
  }, [disabled, isLoading, isOpen]);

  // Handle mode change
  const handleModeChange = useCallback(
    (newMode: ToolSelectionMode) => {
      onModeChange(newMode);
      if (newMode !== "manual") {
        // Clear selection when switching away from manual
        onSelectionChange([]);
      }
    },
    [onModeChange, onSelectionChange]
  );

  // Handle tool toggle (v7: uses toolId for unique identification)
  const handleToolToggle = useCallback(
    (toolId: string) => {
      const newSelection = selectedTools.includes(toolId)
        ? selectedTools.filter((t) => t !== toolId)
        : [...selectedTools, toolId];
      onSelectionChange(newSelection);
    },
    [selectedTools, onSelectionChange]
  );

  return (
    <div className={cn("relative inline-block", className)}>
      {/* Trigger Button */}
      {/* eslint-disable-next-line react/forbid-elements -- ARIA listbox pattern requires native button semantics */}
      <button
        ref={buttonRef}
        type="button"
        onClick={handleToggle}
        disabled={disabled || isLoading}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={`Tools: ${displayText}`}
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md",
          "bg-neutral-3 border border-neutral-6 hover:bg-neutral-4",
          "text-neutral-12 transition-colors duration-200",
          "focus:outline-none focus:ring-2 focus:ring-primary-8 focus:ring-offset-1",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          compact ? "text-xs" : "text-sm"
        )}
      >
        {isLoading ? (
          <Loader2
            className="h-3.5 w-3.5 animate-spin"
            data-testid="tool-selector-loading"
          />
        ) : (
          <Wrench className="h-3.5 w-3.5" />
        )}
        <span className="font-medium">{displayText}</span>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 transition-transform duration-200",
            isOpen && "rotate-180"
          )}
        />
      </button>
      {/* Dropdown */}
      {isOpen && (
        <div
          ref={dropdownRef}
          role="listbox"
          aria-label="Tool selection"
          className={cn(
            "absolute left-0 top-full mt-1 z-dropdown",
            "w-72 max-h-96 overflow-y-auto",
            "bg-neutral-1 border border-neutral-6 rounded-lg shadow-lg",
            "animate-in fade-in-0 zoom-in-95 duration-150"
          )}
        >
          {/* Mode Selector */}
          <div className="p-2 border-b border-neutral-6">
            <div className="text-xs font-medium text-neutral-11 mb-2">
              Selection Mode
            </div>
            {/* eslint-disable react/forbid-elements -- role="option" pattern requires native button */}
            <div className="flex gap-1">
              {MODE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  aria-selected={mode === option.value}
                  onClick={() => handleModeChange(option.value)}
                  title={option.description}
                  className={cn(
                    "flex-1 px-2 py-1 text-xs font-medium rounded",
                    "transition-colors duration-150",
                    mode === option.value
                      ? "bg-primary-9 text-neutral-12"
                      : "bg-neutral-3 text-neutral-11 hover:bg-neutral-4"
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
            {/* eslint-enable react/forbid-elements */}
          </div>

          {/* Tool Selection (only in manual mode) */}
          {mode === "manual" && (
            <>
              {/* Search Input */}
              <div className="p-2 border-b border-neutral-6">
                <div className="relative">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-9" />
                  <Input
                    ref={searchInputRef}
                    placeholder="Search tools..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className={cn(
                      "w-full pl-8 pr-3 py-1.5 text-sm",
                      "bg-neutral-2 border border-neutral-6 rounded",
                      "text-neutral-12 placeholder:text-neutral-9",
                      "focus:outline-none focus:ring-1 focus:ring-primary-8"
                    )} />
                </div>
              </div>

              {/* Tool List */}
              <div className="p-2 max-h-60 overflow-y-auto">
                {filteredTools.length === 0 ? (
                  <div className="text-center py-4 text-sm text-neutral-9">
                    No tools found
                  </div>
                ) : (
                  <>
                    {/* Built-in Tools */}
                    {groupedTools.builtin.length > 0 && (
                      <div className="mb-3">
                        <div className="text-xs font-medium text-neutral-9 mb-1 px-1">
                          Built-in
                        </div>
                        {groupedTools.builtin.map((tool) => (
                          <ToolCheckboxItem
                            key={tool.toolId}
                            tool={tool}
                            isSelected={selectedTools.includes(tool.toolId)}
                            onToggle={() => handleToolToggle(tool.toolId)}
                          />
                        ))}
                      </div>
                    )}

                    {/* Native Tools by Provider (v7) */}
                    {Object.entries(groupedTools.native).map(([provider, tools]) => (
                      <div key={`native-${provider}`} className="mb-3">
                        <div className="text-xs font-medium text-neutral-9 mb-1 px-1 capitalize">
                          {provider} Native
                        </div>
                        {tools.map((tool) => (
                          <ToolCheckboxItem
                            key={tool.toolId}
                            tool={tool}
                            isSelected={selectedTools.includes(tool.toolId)}
                            onToggle={() => handleToolToggle(tool.toolId)}
                          />
                        ))}
                      </div>
                    ))}

                    {/* MCP Tools by Server */}
                    {Object.entries(groupedTools.mcp).map(([serverName, tools]) => (
                      <div key={serverName} className="mb-3">
                        <div className="text-xs font-medium text-neutral-9 mb-1 px-1 capitalize">
                          {serverName}
                        </div>
                        {tools.map((tool) => (
                          <ToolCheckboxItem
                            key={tool.toolId}
                            tool={tool}
                            isSelected={selectedTools.includes(tool.toolId)}
                            onToggle={() => handleToolToggle(tool.toolId)}
                          />
                        ))}
                      </div>
                    ))}
                  </>
                )}
              </div>
            </>
          )}

          {/* Mode Description (for auto/none modes) */}
          {mode !== "manual" && (
            <div className="p-3 text-sm text-neutral-11">
              {mode === "auto" && (
                <p>
                  Tools are automatically selected based on your message content.
                </p>
              )}
              {mode === "none" && (
                <p>
                  No tools will be used. The AI will respond without tool access.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Subcomponents
// =============================================================================

interface ToolCheckboxItemProps {
  tool: ToolOption;
  isSelected: boolean;
  onToggle: () => void;
}

function ToolCheckboxItem({ tool, isSelected, onToggle }: ToolCheckboxItemProps) {
  return (
    <label
      className={cn(
        "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer",
        "hover:bg-neutral-3 transition-colors duration-150"
      )}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onToggle}
        aria-label={tool.displayName}
        className={cn(
          "h-3.5 w-3.5 rounded border-neutral-6",
          "text-primary-9 focus:ring-primary-8 focus:ring-offset-0"
        )}
      />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-neutral-12 truncate">
          {tool.displayName}
        </div>
        {tool.description && (
          <div className="text-xs text-neutral-9 truncate">{tool.description}</div>
        )}
      </div>
    </label>
  );
}
