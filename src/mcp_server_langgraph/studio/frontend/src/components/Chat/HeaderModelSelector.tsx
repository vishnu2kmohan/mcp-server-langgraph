/**
 * HeaderModelSelector Component
 *
 * Unified header-based model selector combining model selection and thinking level.
 * Follows ChatGPT/Gemini pattern with combined display: "Claude Opus 4.5 (High)"
 *
 * Design decisions based on user research:
 * - Header-based placement (industry standard)
 * - Combined selector for model + thinking level
 * - Set-and-forget usage pattern (rarely changed)
 * - Compact pill display with dropdown for full options
 *
 * @see ADR-0102 for model selector consolidation decision
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { ChevronDown, Check, Loader2, Brain } from "lucide-react";
import { cn } from "../../utils/cn";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import type { ModelStatus } from "@/types";

// =============================================================================
// Types
// =============================================================================

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  supportsThinking?: boolean;
  supportsVision?: boolean;
  supportsTools?: boolean;
  status?: ModelStatus;
  sunsetDate?: string;
}

export interface HeaderModelSelectorProps {
  /** Currently selected model ID */
  selectedModel?: string;
  /** Available models for selection */
  availableModels?: ModelOption[];
  /** Callback when model selection changes */
  onModelChange?: (modelId: string) => void;
  /** Current thinking level */
  thinkingLevel?: ReasoningEffortLevel;
  /** Callback when thinking level changes */
  onThinkingLevelChange?: (level: ReasoningEffortLevel) => void;
  /** Whether models are currently loading */
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

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  preview: {
    label: "Preview",
    className:
      "bg-info-3 text-info-11",
  },
  legacy: {
    label: "Legacy",
    className:
      "bg-warning-3 text-warning-11",
  },
  deprecated: {
    label: "Deprecated",
    className:
      "bg-error-3 text-error-11",
  },
};

const THINKING_LEVELS: {
  value: ReasoningEffortLevel;
  label: string;
  description: string;
}[] = [
  {
    value: "low",
    label: "Low",
    description: "Quick responses, minimal reasoning",
  },
  {
    value: "medium",
    label: "Medium",
    description: "Balanced reasoning (default)",
  },
  {
    value: "high",
    label: "High",
    description: "Deep, comprehensive analysis",
  },
];

// =============================================================================
// Component
// =============================================================================

export function HeaderModelSelector({
  selectedModel,
  availableModels = [],
  onModelChange,
  thinkingLevel = "medium",
  onThinkingLevelChange,
  isLoading = false,
  disabled = false,
  compact = false,
  className,
}: HeaderModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const optionsRef = useRef<(HTMLButtonElement | null)[]>([]);

  // Get the selected model object
  const selectedModelObj = useMemo(
    () => availableModels.find((m) => m.id === selectedModel),
    [availableModels, selectedModel]
  );

  // Check if current model supports thinking
  const modelSupportsThinking = selectedModelObj?.supportsThinking ?? false;

  // Get display name (abbreviated in compact mode)
  const displayName = useMemo(() => {
    if (!selectedModelObj) return "Select model";

    if (compact) {
      // Extract short name: "Claude Opus 4.5" -> "Opus 4.5"
      const parts = selectedModelObj.name.split(" ");
      if (parts.length > 2) {
        return parts.slice(1).join(" ");
      }
      return selectedModelObj.name;
    }

    return selectedModelObj.name;
  }, [selectedModelObj, compact]);

  // Get thinking level label
  const thinkingLabel = useMemo(() => {
    const level = THINKING_LEVELS.find((l) => l.value === thinkingLevel);
    return level?.label ?? "Medium";
  }, [thinkingLevel]);

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
        buttonRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Reset focus when dropdown opens/closes and focus first option
  useEffect(() => {
    if (!isOpen) {
      setFocusedIndex(-1);
    }
  }, [isOpen]);

  // Focus element when focusedIndex changes
  useEffect(() => {
    if (isOpen && focusedIndex >= 0 && optionsRef.current[focusedIndex]) {
      optionsRef.current[focusedIndex]?.focus();
    }
  }, [isOpen, focusedIndex]);

  // Handle model selection
  const handleModelSelect = useCallback(
    (modelId: string) => {
      onModelChange?.(modelId);
      setIsOpen(false);
    },
    [onModelChange]
  );

  // Handle thinking level change
  const handleThinkingChange = useCallback(
    (level: ReasoningEffortLevel) => {
      onThinkingLevelChange?.(level);
      // Keep dropdown open for further adjustments
    },
    [onThinkingLevelChange]
  );

  // Handle keyboard navigation in dropdown
  const handleDropdownKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          setFocusedIndex((prev) => {
            const next = prev < 0 ? 0 : Math.min(prev + 1, availableModels.length - 1);
            return next;
          });
          break;
        case "ArrowUp":
          event.preventDefault();
          setFocusedIndex((prev) => {
            const next = prev < 0 ? availableModels.length - 1 : Math.max(prev - 1, 0);
            return next;
          });
          break;
        case "Enter":
          event.preventDefault();
          if (focusedIndex >= 0 && availableModels[focusedIndex]) {
            handleModelSelect(availableModels[focusedIndex].id);
          }
          break;
      }
    },
    [focusedIndex, availableModels, handleModelSelect]
  );

  const toggleDropdown = useCallback(() => {
    if (!disabled) {
      setIsOpen((prev) => !prev);
    }
  }, [disabled]);

  // Handle keyboard on the trigger button
  const handleButtonKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggleDropdown();
      } else if (event.key === "ArrowDown" && isOpen) {
        event.preventDefault();
        setFocusedIndex(0);
      } else if (event.key === "ArrowUp" && isOpen) {
        event.preventDefault();
        setFocusedIndex(availableModels.length - 1);
      }
    },
    [toggleDropdown, isOpen, availableModels.length]
  );

  return (
    <div className={cn("relative inline-block", className)}>
      {/* Pill button */}
      {/* eslint-disable-next-line react/forbid-elements -- Pill trigger requires native button for ref forwarding */}
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={toggleDropdown}
        onKeyDown={handleButtonKeyDown}
        aria-label={`Select model. Current: ${displayName}${modelSupportsThinking ? ` (${thinkingLabel} thinking)` : "" }`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        data-testid="header-model-selector"
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 text-sm",
          "bg-neutral-3",
          "border border-neutral-6",
          "rounded-full",
          "hover:bg-neutral-5",
          "text-neutral-11",
          "transition-colors",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          compact && "compact px-2 py-1 text-xs"
        )}
      >
        {isLoading ? (
          <Loader2
            className="w-4 h-4 animate-spin"
            data-testid="model-loading-spinner"
          />
        ) : (
          <>
            <span className="font-medium">{displayName}</span>
            {modelSupportsThinking && (
              <span className="text-neutral-10">
                ({thinkingLabel})
              </span>
            )}
          </>
        )}
        <ChevronDown
          className={cn(
            "w-3.5 h-3.5 text-neutral-9 transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          ref={dropdownRef}
          role="listbox"
          aria-label="Select a model"
          data-testid="model-dropdown"
          className={cn(
            "absolute left-0 bottom-full mb-1",
            "w-80 max-h-96 overflow-y-auto",
            "bg-neutral-2",
            "border border-neutral-6",
            "rounded-lg shadow-lg",
            "z-dropdown"
          )}
        >
          {/* Thinking Level Section (only for thinking-capable models) */}
          {modelSupportsThinking && (
            <div
              data-testid="thinking-level-section"
              className="p-3 border-b border-neutral-6"
            >
              <div className="flex items-center gap-2 mb-2">
                <Brain
                  size={14}
                  className="text-insight-11"
                />
                <span className="text-xs font-medium text-neutral-11">
                  Thinking Level
                </span>
              </div>
              <div className="flex gap-1" role="radiogroup" aria-label="Thinking level">
                {THINKING_LEVELS.map((level) => (
                  <label
                    key={level.value}
                    className={cn(
                      "flex-1 px-3 py-1.5 text-center text-sm cursor-pointer rounded",
                      "transition-colors",
                      thinkingLevel === level.value
                        ? "bg-insight-10 text-neutral-12"
                        : "bg-neutral-4 text-neutral-11 hover:bg-neutral-5"
                    )}
                  >
                    <input
                      type="radio"
                      name="thinking-level"
                      value={level.value}
                      checked={thinkingLevel === level.value}
                      onChange={() => handleThinkingChange(level.value)}
                      className="sr-only"
                      aria-label={`${level.label}: ${level.description}`}
                    />
                    {level.label}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Models Section */}
          <div className="py-1">
            <div className="px-3 py-1.5 text-xs font-medium text-neutral-10 uppercase tracking-wider">
              Models
            </div>
            {availableModels.map((model, index) => {
              const isSelected = model.id === selectedModel;
              const statusBadge = model.status && STATUS_BADGES[model.status];

              return (
                // eslint-disable-next-line react/forbid-elements -- Listbox options require native button
                <button
                  key={model.id}
                  ref={(el) => {
                    optionsRef.current[index] = el;
                  }}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleModelSelect(model.id)}
                  onKeyDown={handleDropdownKeyDown}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2",
                    "text-sm text-left",
                    "text-neutral-11",
                    "hover:bg-neutral-4",
                    "focus:bg-neutral-2",
                    "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:ring-inset",
                    "transition-colors"
                  )}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{model.name}</span>
                      {model.supportsThinking && (
                        <Brain
                          size={12}
                          className="text-insight-9 shrink-0"
                          data-testid="thinking-badge"
                        />
                      )}
                      {statusBadge && (
                        <span
                          className={cn(
                            "px-1.5 py-0.5 text-xs rounded",
                            statusBadge.className
                          )}
                        >
                          {statusBadge.label}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-neutral-10 capitalize">
                      {model.provider}
                    </div>
                  </div>
                  {isSelected && (
                    <Check
                      className="w-4 h-4 text-primary-9 shrink-0"
                      data-testid="model-selected-check"
                    />
                  )}
                </button>
              );
            })}
            {availableModels.length === 0 && (
              <div className="px-3 py-4 text-sm text-center text-neutral-10">
                No models available
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default HeaderModelSelector;
