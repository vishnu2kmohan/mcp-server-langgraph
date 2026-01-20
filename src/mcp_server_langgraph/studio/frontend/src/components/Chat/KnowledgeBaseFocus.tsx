/**
 * KnowledgeBaseFocus Component
 *
 * Dropdown selector for knowledge base context focus mode.
 * Inspired by Perplexity's "Focus" mode and ChatGPT's pill-based controls.
 *
 * Features:
 * - Pill-shaped dropdown button in chat input controls
 * - Options: All (Web + KB), Knowledge Base only, Web only, None
 * - Status indicator for KB availability
 * - Compact mode for space-constrained layouts
 * - Full keyboard navigation support
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { ChevronDown, Database, Globe, Search, Ban, Check } from "lucide-react";
import { cn } from "../../utils/cn";
import type { KBStatusValue } from "../../types/api";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

/** Knowledge Base Focus Mode */
export type KBFocusMode = "all" | "kb_only" | "web_only" | "none";

/** KB Status for indicator (alias for KBStatusValue) */
export type KBStatus = KBStatusValue;

/** Option definition for dropdown */
interface FocusOption {
  value: KBFocusMode;
  label: string;
  description: string;
  icon: React.ElementType;
}

export interface KnowledgeBaseFocusProps {
  /** Current focus mode */
  value: KBFocusMode;
  /** Callback when mode changes */
  onChange: (mode: KBFocusMode) => void;
  /** Whether the dropdown is disabled */
  disabled?: boolean;
  /** KB status for indicator */
  kbStatus?: KBStatus;
  /** Status message for tooltip (e.g., config guidance) */
  kbStatusMessage?: string;
  /** Compact mode (icon only in button) */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const FOCUS_OPTIONS: FocusOption[] = [
  {
    value: "all",
    label: "All",
    description: "Search web and knowledge base",
    icon: Search,
  },
  {
    value: "kb_only",
    label: "Knowledge Base",
    description: "Search internal knowledge only",
    icon: Database,
  },
  {
    value: "web_only",
    label: "Web",
    description: "Search external web only",
    icon: Globe,
  },
  {
    value: "none",
    label: "None",
    description: "No context injection",
    icon: Ban,
  },
];

// =============================================================================
// Component
// =============================================================================

export function KnowledgeBaseFocus({
  value,
  onChange,
  disabled = false,
  kbStatus,
  kbStatusMessage,
  compact = false,
  className,
}: KnowledgeBaseFocusProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Find current option
  const currentOption = FOCUS_OPTIONS.find((opt) => opt.value === value);
  const CurrentIcon = currentOption?.icon || Search;

  // Handle click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setFocusedIndex(-1);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Handle option selection
  const handleSelect = useCallback(
    (mode: KBFocusMode) => {
      onChange(mode);
      setIsOpen(false);
      setFocusedIndex(-1);
      buttonRef.current?.focus();
    },
    [onChange],
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      switch (event.key) {
        case "Enter":
        case " ":
          event.preventDefault();
          if (!isOpen) {
            setIsOpen(true);
            setFocusedIndex(0);
          } else if (focusedIndex >= 0) {
            handleSelect(FOCUS_OPTIONS[focusedIndex].value);
          }
          break;
        case "ArrowDown":
          event.preventDefault();
          if (!isOpen) {
            setIsOpen(true);
            setFocusedIndex(0);
          } else {
            setFocusedIndex((prev) =>
              prev < FOCUS_OPTIONS.length - 1 ? prev + 1 : 0,
            );
          }
          break;
        case "ArrowUp":
          event.preventDefault();
          if (isOpen) {
            setFocusedIndex((prev) =>
              prev > 0 ? prev - 1 : FOCUS_OPTIONS.length - 1,
            );
          }
          break;
        case "Escape":
          event.preventDefault();
          setIsOpen(false);
          setFocusedIndex(-1);
          buttonRef.current?.focus();
          break;
        case "Tab":
          setIsOpen(false);
          setFocusedIndex(-1);
          break;
      }
    },
    [isOpen, focusedIndex, handleSelect],
  );

  // Toggle dropdown
  const handleToggle = () => {
    if (!disabled) {
      setIsOpen((prev) => !prev);
      if (!isOpen) {
        setFocusedIndex(0);
      }
    }
  };

  // Status indicator color
  const getStatusColor = (status: KBStatus): string => {
    switch (status) {
      case "ready":
        return "bg-success-9";
      case "misconfigured":
        return "bg-warning-9";
      case "unavailable":
        return "bg-neutral-4";
    }
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Main button */}
      <Button
        ref={buttonRef}
        type="button"
        data-testid="kb-focus-button"
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-label="Select source focus mode"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls="kb-focus-listbox"
        className={cn(
          "flex items-center gap-1.5 rounded-lg transition-colors",
          "border border-neutral-5",
          "bg-neutral-1",
          "hover:bg-neutral-1",
          "focus:outline-none focus:ring-2 focus:ring-primary-7",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          compact ? "p-2" : "px-3 py-1.5 text-sm",
        )}
      >
        {/* Status indicator (only when kbStatus provided) */}
        {kbStatus && (
          <span
            data-testid="kb-status-indicator"
            title={kbStatusMessage}
            className={cn(
              "w-2 h-2 rounded-full flex-shrink-0",
              getStatusColor(kbStatus),
            )}
          />
        )}

        {/* Icon */}
        <CurrentIcon className="w-4 h-4 text-neutral-10" />

        {/* Label (hidden in compact mode) */}
        {!compact && (
          <span className="font-medium text-neutral-11">
            {currentOption?.label || "All"}
          </span>
        )}

        {/* Chevron */}
        <ChevronDown
          className={cn(
            "w-3 h-3 text-neutral-9 transition-transform",
            isOpen && "rotate-180",
          )}
          aria-hidden="true"
        />
      </Button>
      {/* Dropdown menu */}
      {isOpen && (
        <div
          ref={listRef}
          id="kb-focus-listbox"
          role="listbox"
          aria-label="Source focus options"
          className={cn(
            "absolute z-dropdown mt-1 w-56 py-1",
            "bg-neutral-1",
            "border border-neutral-5",
            "rounded-lg shadow-lg",
            // Position above or below based on space (simplified: always below)
            "bottom-full mb-1", // Position above the button for chat input
          )}
        >
          {FOCUS_OPTIONS.map((option, index) => {
            const isSelected = option.value === value;
            const isFocused = index === focusedIndex;
            const Icon = option.icon;

            return (
              <Button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(option.value)}
                onMouseEnter={() => setFocusedIndex(index)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 text-sm",
                  "transition-colors",
                  isFocused && "bg-neutral-2",
                  isSelected &&
                    "bg-primary-1 bg-primary-4 text-primary-11 dark:text-primary-11",
                )}
              >
                <Icon
                  className={cn(
                    "w-4 h-4 flex-shrink-0",
                    isSelected
                      ? "text-primary-10 dark:text-primary-11"
                      : "text-neutral-10",
                  )}
                />
                <div className="flex-1 text-left">
                  <div
                    className={cn(
                      "font-medium",
                      isSelected
                        ? "text-primary-11 dark:text-primary-11"
                        : "text-neutral-12",
                    )}
                  >
                    {option.label}
                  </div>
                  <div className="text-xs text-neutral-10">
                    {option.description}
                  </div>
                </div>
                {isSelected && (
                  <Check
                    className="w-4 h-4 text-primary-10 dark:text-primary-11 flex-shrink-0"
                    aria-hidden="true"
                  />
                )}
              </Button>
            );
          })}
        </div>
      )}
    </div>
  );
}
