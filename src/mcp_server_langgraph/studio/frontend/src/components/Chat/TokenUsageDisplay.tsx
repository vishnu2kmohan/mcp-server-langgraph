/**
 * TokenUsageDisplay Component
 *
 * Inline token usage display that shows prompt and completion token counts
 * directly below AI responses. Optionally shows estimated cost.
 *
 * Features:
 * - Prompt/completion token breakdown
 * - Total token count
 * - Optional cost estimation by provider
 * - Compact mode for space-constrained UIs
 */

import { useMemo } from "react";
import { Zap, DollarSign } from "lucide-react";
import type { ModelProvider } from "../../types/session";

// Re-export for consumers
export type { ModelProvider };

// =============================================================================
// Types
// =============================================================================

export interface TokenUsageDisplayProps {
  /** Number of prompt/input tokens */
  promptTokens: number;
  /** Number of completion/output tokens */
  completionTokens: number;
  /** Whether to show cost estimation */
  showCost?: boolean;
  /** Model provider for cost calculation */
  modelProvider?: ModelProvider;
  /** Whether to show labels (input/output) */
  showLabels?: boolean;
  /** Compact mode for smaller display */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

// Cost per 1K tokens by provider (simplified estimates in USD)
const COST_PER_1K_TOKENS: Record<
  ModelProvider,
  { input: number; output: number }
> = {
  openai: { input: 0.01, output: 0.03 },
  anthropic: { input: 0.015, output: 0.075 },
  google: { input: 0.00025, output: 0.0005 },
  azure: { input: 0.01, output: 0.03 },
  unknown: { input: 0, output: 0 }, // No cost for unknown provider
};

// =============================================================================
// Component
// =============================================================================

export function TokenUsageDisplay({
  promptTokens,
  completionTokens,
  showCost = false,
  modelProvider = "openai",
  showLabels = false,
  compact = false,
  className = "",
}: TokenUsageDisplayProps) {
  const totalTokens = promptTokens + completionTokens;

  // Calculate estimated cost (must be called before early return per React hooks rules)
  const estimatedCost = useMemo(() => {
    const rates = COST_PER_1K_TOKENS[modelProvider];
    const inputCost = (promptTokens / 1000) * rates.input;
    const outputCost = (completionTokens / 1000) * rates.output;
    return inputCost + outputCost;
  }, [promptTokens, completionTokens, modelProvider]);

  // Don't render if no tokens
  if (totalTokens === 0) {
    return null;
  }

  // Format number with commas
  const formatNumber = (n: number) => n.toLocaleString();

  // Format cost with appropriate precision
  const formatCost = (cost: number) => {
    if (cost < 0.01) {
      return `$${cost.toFixed(4)}`;
    }
    return `$${cost.toFixed(2)}`;
  };

  const textSize = compact ? "text-[10px]" : "text-xs";
  const iconSize = compact ? 10 : 12;

  return (
    <div
      data-testid="token-usage-container"
      className={`inline-flex items-center gap-2 ${textSize} text-gray-400 dark:text-gray-500 ${className}`}
    >
      <Zap size={iconSize} className="flex-shrink-0" />

      {/* Token counts */}
      <span className="inline-flex items-center gap-1">
        {showLabels && (
          <span className="text-gray-500 dark:text-gray-400">Input:</span>
        )}
        <span>{formatNumber(promptTokens)}</span>
        <span className="text-gray-300 dark:text-gray-600">/</span>
        {showLabels && (
          <span className="text-gray-500 dark:text-gray-400">Output:</span>
        )}
        <span>{formatNumber(completionTokens)}</span>
        <span className="text-gray-300 dark:text-gray-600">=</span>
        <span className="font-medium text-gray-500 dark:text-gray-400">
          {formatNumber(totalTokens)}
        </span>
        <span className="text-gray-400 dark:text-gray-500">tokens</span>
      </span>

      {/* Cost estimation */}
      {showCost && (
        <span
          data-testid="estimated-cost"
          className="inline-flex items-center gap-0.5 text-gray-500 dark:text-gray-400"
        >
          <DollarSign size={iconSize - 2} />
          <span>{formatCost(estimatedCost)}</span>
        </span>
      )}
    </div>
  );
}

export default TokenUsageDisplay;
