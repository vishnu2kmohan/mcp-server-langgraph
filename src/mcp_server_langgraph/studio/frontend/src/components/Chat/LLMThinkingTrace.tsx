/**
 * LLMThinkingTrace Component
 *
 * Displays the native thinking/reasoning content from LLM models that support
 * extended thinking, such as:
 * - Claude Opus 4.5 / Sonnet 4 (thinking blocks)
 * - Gemini 2.5 Pro/Flash (thinking_content)
 * - OpenAI o1/o3 (reasoning - count only, no content exposed)
 *
 * Features:
 * - Collapsible display with toggle
 * - Copy to clipboard
 * - Token count display
 * - Visual distinction from regular content (violet theme)
 * - Streaming state indicator
 * - Long content handling with show more/less
 */

import { useState, useCallback } from "react";
import {
  Brain,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Sparkles,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export interface LLMThinkingTraceProps {
  /** The thinking/reasoning content from the LLM */
  thinkingContent: string;
  /** Whether the trace is expanded */
  isExpanded: boolean;
  /** Callback to toggle expansion */
  onToggle: () => void;
  /** Number of thinking tokens used (optional) */
  thinkingTokens?: number;
  /** Model name for display (optional) */
  modelName?: string;
  /** Whether this model supports thinking (optional) */
  isThinkingModel?: boolean;
  /** Whether the response is still streaming */
  isStreaming?: boolean;
  /** Maximum preview length before truncation (default: 500) */
  maxPreviewLength?: number;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function LLMThinkingTrace({
  thinkingContent,
  isExpanded,
  onToggle,
  thinkingTokens,
  modelName,
  isThinkingModel = false,
  isStreaming = false,
  maxPreviewLength = 500,
  className = "",
}: LLMThinkingTraceProps) {
  const [copied, setCopied] = useState(false);
  const [showFullContent, setShowFullContent] = useState(false);

  // Copy thinking content to clipboard (must be before early return)
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(thinkingContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy thinking content:", err);
    }
  }, [thinkingContent]);

  // Don't render if no content
  if (!thinkingContent || !thinkingContent.trim()) {
    return null;
  }

  const isLongContent = thinkingContent.length > maxPreviewLength;
  const displayContent =
    showFullContent || !isLongContent
      ? thinkingContent
      : thinkingContent.slice(0, maxPreviewLength) + "...";

  // Format token count with commas
  const formatTokenCount = (count: number): string => {
    return count.toLocaleString();
  };

  return (
    <div
      data-testid="llm-thinking-trace"
      className={`rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-900/20 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-violet-100 dark:bg-violet-900/40">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-violet-600 dark:text-violet-400" />
          <span className="text-sm font-medium text-violet-700 dark:text-violet-300">
            Thinking
          </span>

          {/* Model Badge */}
          {isThinkingModel && (
            <span
              data-testid="thinking-model-badge"
              className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs bg-violet-200 dark:bg-violet-800 text-violet-700 dark:text-violet-300 rounded"
            >
              <Sparkles size={10} />
              Extended
            </span>
          )}

          {/* Model Name */}
          {modelName && (
            <span className="text-xs text-violet-500 dark:text-violet-400">
              {modelName}
            </span>
          )}

          {/* Token Count */}
          {thinkingTokens !== undefined && (
            <span className="text-xs text-violet-500 dark:text-violet-400">
              {formatTokenCount(thinkingTokens)} tokens
            </span>
          )}

          {/* Streaming Indicator */}
          {isStreaming && (
            <span
              data-testid="streaming-indicator"
              className="inline-flex items-center gap-1 text-xs text-violet-600 dark:text-violet-400 animate-pulse"
            >
              <span className="w-1.5 h-1.5 bg-violet-500 rounded-full" />
              Thinking...
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Copy Button (only when expanded) */}
          {isExpanded && (
            <button
              onClick={handleCopy}
              aria-label="Copy thinking content"
              className="p-1 rounded hover:bg-violet-200 dark:hover:bg-violet-800 text-violet-600 dark:text-violet-400 transition-colors"
            >
              {copied ? (
                <span className="flex items-center gap-1 text-xs text-green-600">
                  <Check size={14} />
                  Copied!
                </span>
              ) : (
                <Copy size={14} />
              )}
            </button>
          )}

          {/* Toggle Button */}
          <button
            onClick={onToggle}
            aria-label="Toggle thinking trace"
            aria-expanded={isExpanded}
            className="p-1 rounded hover:bg-violet-200 dark:hover:bg-violet-800 text-violet-600 dark:text-violet-400 transition-colors"
          >
            {isExpanded ? (
              <ChevronUp size={16} data-testid="chevron-icon" />
            ) : (
              <ChevronDown size={16} data-testid="chevron-icon" />
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-3">
          <div
            data-testid="thinking-content"
            className="text-sm text-violet-800 dark:text-violet-200 whitespace-pre-wrap font-mono leading-relaxed"
          >
            {displayContent}
          </div>

          {/* Show More/Less for long content */}
          {isLongContent && (
            <button
              onClick={() => setShowFullContent(!showFullContent)}
              className="mt-2 text-xs text-violet-600 dark:text-violet-400 hover:text-violet-800 dark:hover:text-violet-200 underline"
            >
              {showFullContent ? "Show less" : "Show more"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default LLMThinkingTrace;
