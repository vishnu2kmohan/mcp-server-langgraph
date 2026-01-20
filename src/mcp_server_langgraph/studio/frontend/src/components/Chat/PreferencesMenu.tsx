/**
 * PreferencesMenu Component
 *
 * Consolidated preferences dropdown for chat input settings.
 * Provides access to:
 * - Model selection (with thinking level)
 * - Tool selection mode
 * - Knowledge Base focus mode
 *
 * Design System Compliance:
 * - Uses CVA for variant styling
 * - Uses Radix 1-12 color scale
 * - Focus rings: focus-visible:ring-2 focus-visible:ring-primary-7
 * - Touch targets: 32px minimum (WCAG 2.5.8)
 *
 * @see Chat Input UX Plan for architecture details
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { Settings2, ChevronDown, Check, Brain, Wrench, Database, Loader2 } from "lucide-react";
import { cn } from "../../utils/cn";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import type { KBFocusMode } from "./KnowledgeBaseFocus";
import type { ToolSelectionMode } from "@/types/tools";

// =============================================================================
// Types
// =============================================================================

export interface PreferencesMenuProps {
  /** Currently selected model ID */
  selectedModel?: string;
  /** Callback when model selection changes */
  onModelChange?: (modelId: string) => void;
  /** Current thinking level */
  thinkingLevel?: ReasoningEffortLevel;
  /** Callback when thinking level changes */
  onThinkingLevelChange?: (level: ReasoningEffortLevel) => void;
  /** Current tool selection mode */
  toolMode?: ToolSelectionMode;
  /** Callback when tool mode changes */
  onToolModeChange?: (mode: ToolSelectionMode) => void;
  /** Currently selected tools */
  selectedTools?: string[];
  /** Callback when tools change */
  onToolsChange?: (tools: string[]) => void;
  /** Current KB focus mode */
  kbFocusMode?: KBFocusMode;
  /** Callback when KB focus mode changes */
  onKBFocusChange?: (mode: KBFocusMode) => void;
  /** Whether the menu is loading */
  isLoading?: boolean;
  /** Whether the menu is disabled */
  disabled?: boolean;
  /** Compact mode for smaller displays */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const THINKING_LEVELS: { value: ReasoningEffortLevel; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const TOOL_MODES: { value: ToolSelectionMode; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "manual", label: "Manual" },
  { value: "none", label: "None" },
];

const KB_FOCUS_MODES: { value: KBFocusMode; label: string }[] = [
  { value: "all", label: "All Sources" },
  { value: "kb_only", label: "KB Only" },
  { value: "web_only", label: "Web Only" },
  { value: "none", label: "None" },
];

// =============================================================================
// Component
// =============================================================================

export function PreferencesMenu({
  selectedModel: _selectedModel,
  onModelChange: _onModelChange,
  thinkingLevel = "medium",
  onThinkingLevelChange,
  toolMode = "auto",
  onToolModeChange,
  selectedTools: _selectedTools,
  onToolsChange: _onToolsChange,
  kbFocusMode = "all",
  onKBFocusChange,
  isLoading = false,
  disabled = false,
  compact = false,
  className,
}: PreferencesMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
    return undefined;
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    },
    []
  );

  const handleToggle = useCallback(() => {
    if (!disabled && !isLoading) {
      setIsOpen((prev) => !prev);
    }
  }, [disabled, isLoading]);

  const handleThinkingLevelChange = useCallback(
    (level: ReasoningEffortLevel) => {
      onThinkingLevelChange?.(level);
    },
    [onThinkingLevelChange]
  );

  const handleToolModeChange = useCallback(
    (mode: ToolSelectionMode) => {
      onToolModeChange?.(mode);
    },
    [onToolModeChange]
  );

  const handleKBFocusChange = useCallback(
    (mode: KBFocusMode) => {
      onKBFocusChange?.(mode);
    },
    [onKBFocusChange]
  );

  return (
    <div
      ref={containerRef}
      data-testid="preferences-menu"
      className={cn("relative", className)}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      {/* eslint-disable-next-line react/forbid-elements -- Custom dropdown trigger with aria-expanded/aria-haspopup */}
      <button
        ref={buttonRef}
        type="button"
        data-testid="preferences-menu-trigger"
        onClick={handleToggle}
        disabled={disabled || isLoading}
        aria-label="Open preferences menu"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md text-sm font-medium",
          "min-h-8 transition-colors duration-150",
          "bg-neutral-3 text-neutral-11 hover:bg-neutral-4",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-7 focus-visible:ring-offset-2",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          compact ? "px-2" : "px-3"
        )}
      >
        {isLoading ? (
          <Loader2
            className="h-4 w-4 animate-spin"
            data-testid="preferences-loading"
            aria-hidden="true"
          />
        ) : (
          <Settings2 className="h-4 w-4" aria-hidden="true" />
        )}
        {!compact && <span>Preferences</span>}
        <ChevronDown
          className={cn(
            "h-3 w-3 transition-transform duration-150",
            isOpen && "rotate-180"
          )}
          aria-hidden="true"
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          data-testid="preferences-dropdown"
          role="menu"
          aria-label="Preferences menu"
          className={cn(
            "absolute right-0 top-full mt-1 z-50",
            "min-w-[240px] rounded-lg border border-neutral-6",
            "bg-neutral-2 shadow-lg",
            "py-2"
          )}
        >
          {/* Model Section */}
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
              <Brain className="h-3 w-3" aria-hidden="true" />
              Thinking Level
            </div>
            <div className="space-y-1" role="listbox" aria-label="Thinking level">
              {THINKING_LEVELS.map((level) => (
                // eslint-disable-next-line react/forbid-elements -- Custom listbox option with role="option" and aria-selected
                <button
                  key={level.value}
                  type="button"
                  role="option"
                  aria-selected={thinkingLevel === level.value}
                  onClick={() => handleThinkingLevelChange(level.value)}
                  className={cn(
                    "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                    "hover:bg-neutral-4 transition-colors",
                    thinkingLevel === level.value
                      ? "text-primary-11 bg-primary-3"
                      : "text-neutral-12"
                  )}
                >
                  <span>{level.label}</span>
                  {thinkingLevel === level.value && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-neutral-6 my-2" />

          {/* Tools Section */}
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
              <Wrench className="h-3 w-3" aria-hidden="true" />
              Tools
            </div>
            <div className="space-y-1" role="listbox" aria-label="Tool mode">
              {TOOL_MODES.map((mode) => (
                // eslint-disable-next-line react/forbid-elements -- Custom listbox option with role="option" and aria-selected
                <button
                  key={mode.value}
                  type="button"
                  role="option"
                  aria-selected={toolMode === mode.value}
                  onClick={() => handleToolModeChange(mode.value)}
                  className={cn(
                    "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                    "hover:bg-neutral-4 transition-colors",
                    toolMode === mode.value
                      ? "text-primary-11 bg-primary-3"
                      : "text-neutral-12"
                  )}
                >
                  <span>{mode.label}</span>
                  {toolMode === mode.value && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-neutral-6 my-2" />

          {/* KB Focus Section */}
          <div className="px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-11 uppercase tracking-wide mb-2">
              <Database className="h-3 w-3" aria-hidden="true" />
              Knowledge Base
            </div>
            <div className="space-y-1" role="listbox" aria-label="KB focus mode">
              {KB_FOCUS_MODES.map((mode) => (
                // eslint-disable-next-line react/forbid-elements -- Custom listbox option with role="option" and aria-selected
                <button
                  key={mode.value}
                  type="button"
                  role="option"
                  aria-selected={kbFocusMode === mode.value}
                  onClick={() => handleKBFocusChange(mode.value)}
                  className={cn(
                    "flex items-center justify-between w-full px-2 py-1.5 rounded text-sm",
                    "hover:bg-neutral-4 transition-colors",
                    kbFocusMode === mode.value
                      ? "text-primary-11 bg-primary-3"
                      : "text-neutral-12"
                  )}
                >
                  <span>{mode.label}</span>
                  {kbFocusMode === mode.value && (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

PreferencesMenu.displayName = "PreferencesMenu";
