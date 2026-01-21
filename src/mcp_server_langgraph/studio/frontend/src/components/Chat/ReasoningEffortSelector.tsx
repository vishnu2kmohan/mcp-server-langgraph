/**
 * ReasoningEffortSelector Component
 *
 * UI for selecting the reasoning effort/thinking budget level for LLM models
 * that support extended thinking capabilities.
 *
 * Effort Levels:
 * - low: Quick responses, minimal reasoning (~1K thinking tokens)
 * - medium: Balanced reasoning (default, ~10K thinking tokens)
 * - high: Deep reasoning, comprehensive analysis (~100K thinking tokens)
 *
 * Supported models (via LiteLLM):
 * - Claude Opus 4.5, Sonnet 4 (extended_thinking budget)
 * - Gemini 2.5 Pro/Flash (thinking_budget)
 * - OpenAI o1/o3 (reasoning_effort: low/medium/high)
 */

import { useCallback } from "react";
import { Brain } from "lucide-react";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

/**
 * Reasoning effort levels for extended thinking models.
 *
 * Maps to FF_MAX_THINKING_BUDGET on the backend:
 * - none: No extended thinking, standard response mode
 * - low: Quick responses, minimal reasoning (~1K thinking tokens)
 * - medium: Balanced reasoning (default, ~10K thinking tokens)
 * - high: Deep reasoning, comprehensive analysis (~100K thinking tokens)
 * - ultra: Maximum reasoning depth, exhaustive analysis (model-dependent max)
 *
 * Support varies by vendor:
 * - OpenAI o1/o3: low, medium, high (native reasoning_effort)
 * - Anthropic Claude: all levels (extended_thinking budget)
 * - Google Gemini: all levels (thinking_budget)
 */
export type ReasoningEffortLevel = "none" | "low" | "medium" | "high" | "ultra";

export interface ReasoningEffortSelectorProps {
  /** Current effort level */
  value: ReasoningEffortLevel;
  /** Callback when effort level changes */
  onChange: (level: ReasoningEffortLevel) => void;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Whether the current model supports thinking */
  modelSupportsThinking?: boolean;
  /** Model name for display */
  modelName?: string;
  /** Compact mode for smaller UI */
  compact?: boolean;
  /** Show description of selected level */
  showDescription?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const EFFORT_LEVELS: {
  value: ReasoningEffortLevel;
  label: string;
  shortLabel: string;
  tooltip: string;
  description: string;
}[] = [
  {
    value: "none",
    label: "None",
    shortLabel: "0",
    tooltip: "No extended thinking - Standard response mode",
    description:
      "Standard response mode without extended thinking. Fastest, lowest cost.",
  },
  {
    value: "low",
    label: "Low",
    shortLabel: "L",
    tooltip: "Quick, minimal reasoning - Fast responses",
    description:
      "Quick responses with minimal reasoning. Best for simple questions.",
  },
  {
    value: "medium",
    label: "Medium",
    shortLabel: "M",
    tooltip: "Balanced reasoning - Default mode",
    description: "Balanced reasoning depth. Good for most tasks.",
  },
  {
    value: "high",
    label: "High",
    shortLabel: "H",
    tooltip: "Deep, comprehensive reasoning - Thorough analysis",
    description: "Deep, comprehensive analysis. Best for complex problems.",
  },
  {
    value: "ultra",
    label: "Ultra",
    shortLabel: "U",
    tooltip: "Maximum reasoning depth - Exhaustive analysis",
    description:
      "Maximum reasoning depth with exhaustive analysis. Best for hardest problems.",
  },
];

// =============================================================================
// Component
// =============================================================================

export function ReasoningEffortSelector({
  value,
  onChange,
  disabled = false,
  modelSupportsThinking = true,
  modelName,
  compact = false,
  showDescription = false,
  className = "",
}: ReasoningEffortSelectorProps) {
  const isDisabled = disabled || !modelSupportsThinking;

  const handleSelect = useCallback(
    (level: ReasoningEffortLevel) => {
      if (isDisabled || level === value) return;
      onChange(level);
    },
    [isDisabled, value, onChange],
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, currentLevel: ReasoningEffortLevel) => {
      if (isDisabled) return;

      const currentIndex = EFFORT_LEVELS.findIndex(
        (l) => l.value === currentLevel,
      );

      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        event.preventDefault();
        const nextIndex = Math.min(currentIndex + 1, EFFORT_LEVELS.length - 1);
        const nextLevel = EFFORT_LEVELS[nextIndex];
        if (nextLevel) onChange(nextLevel.value);
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        event.preventDefault();
        const prevIndex = Math.max(currentIndex - 1, 0);
        const prevLevel = EFFORT_LEVELS[prevIndex];
        if (prevLevel) onChange(prevLevel.value);
      }
    },
    [isDisabled, onChange],
  );

  const selectedLevel = EFFORT_LEVELS.find((l) => l.value === value);

  return (
    <div
      data-testid="reasoning-effort-selector"
      className={`flex flex-col ${compact ? "gap-1" : "gap-2"} ${isDisabled ? "opacity-50" : ""} ${className}`}
    >
      {/* Label Row */}
      <div className="flex items-center gap-2">
        <Brain
          size={14}
          className="text-insight-10 dark:text-insight-11"
          data-testid="brain-icon"
        />
        <span className="text-xs font-medium text-neutral-11">
          Thinking
        </span>
        {modelName && (
          <span className="text-xs text-neutral-9">
            ({modelName})
          </span>
        )}
        {!modelSupportsThinking && (
          <span className="text-xs text-warning-9 dark:text-warning-9">
            Not supported
          </span>
        )}
      </div>
      {/* Button Group */}
      <div
        role="radiogroup"
        aria-label="Reasoning effort level"
        className={`flex ${compact ? "gap-0.5" : "gap-1"}`}
      >
        {EFFORT_LEVELS.map((level) => {
          const isSelected = value === level.value;
          return (
            <Button
              variant="primary"
              className="rounded"
              key={level.value}
              onClick={() => handleSelect(level.value)}
              onKeyDown={(e) => handleKeyDown(e, level.value)}
              disabled={isDisabled}
              title={level.tooltip}
              aria-pressed={isSelected}>
              {compact ? level.shortLabel : level.label}
            </Button>
          );
        })}
      </div>
      {/* Description */}
      {showDescription && selectedLevel && (
        <p
          data-testid="effort-description"
          className="text-xs text-neutral-10"
        >
          {selectedLevel.description}
        </p>
      )}
    </div>
  );
}

export default ReasoningEffortSelector;
