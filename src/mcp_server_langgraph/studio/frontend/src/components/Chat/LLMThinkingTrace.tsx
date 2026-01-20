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

import { Button } from "@/components/UI";

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
      className={`rounded-lg border border-insight-4 dark:border-insight-12 bg-insight-2 dark:bg-insight-3 overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-insight-3 dark:bg-insight-4">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-insight-10 dark:text-insight-11" />
          <span className="text-sm font-medium text-insight-11 dark:text-insight-11">
            Thinking
          </span>

          {/* Model Badge */}
          {isThinkingModel && (
            <span
              data-testid="thinking-model-badge"
              className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs bg-insight-4 dark:bg-insight-12 text-insight-11 dark:text-insight-11 rounded"
            >
              <Sparkles size={10} />
              Extended
            </span>
          )}

          {/* Model Name */}
          {modelName && (
            <span className="text-xs text-insight-9 dark:text-insight-11">
              {modelName}
            </span>
          )}

          {/* Token Count */}
          {thinkingTokens !== undefined && (
            <span className="text-xs text-insight-9 dark:text-insight-11">
              {formatTokenCount(thinkingTokens)} tokens
            </span>
          )}

          {/* Streaming Indicator */}
          {isStreaming && (
            <span
              data-testid="streaming-indicator"
              className="inline-flex items-center gap-1 text-xs text-insight-10 dark:text-insight-11 animate-pulse"
            >
              <span className="w-1.5 h-1.5 bg-insight-9 rounded-full" />
              Thinking...
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Copy Button (only when expanded) */}
          {isExpanded && (
            <Button
              variant="ghost"
              size="icon"
              className="hover:bg-insight-4 dark:hover:bg-insight-12 text-insight-10 dark:text-insight-11"
              onClick={handleCopy}
              aria-label="Copy thinking content"
            >
              {copied ? (
                <span className="flex items-center gap-1 text-xs text-success-10">
                  <Check size={14} />
                  Copied!
                </span>
              ) : (
                <Copy size={14} />
              )}
            </Button>
          )}

          {/* Toggle Button */}
          <Button
            variant="ghost"
            size="icon"
            className="hover:bg-insight-4 dark:hover:bg-insight-12 text-insight-10 dark:text-insight-11"
            onClick={onToggle}
            aria-label="Toggle thinking trace"
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <ChevronUp size={16} data-testid="chevron-icon" />
            ) : (
              <ChevronDown size={16} data-testid="chevron-icon" />
            )}
          </Button>
        </div>
      </div>
      {/* Content */}
      {isExpanded && (
        <div className="p-3">
          <div
            data-testid="thinking-content"
            className="text-sm text-insight-12 dark:text-insight-4 whitespace-pre-wrap font-mono leading-relaxed"
          >
            {displayContent}
          </div>

          {/* Show More/Less for long content */}
          {isLongContent && (
            <Button
              variant="ghost"
              size="sm"
              className="mt-2 text-xs text-insight-10 dark:text-insight-11 hover:text-insight-12 dark:hover:text-insight-4 underline"
              onClick={() => setShowFullContent(!showFullContent)}
            >
              {showFullContent ? "Show less" : "Show more"}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export default LLMThinkingTrace;
