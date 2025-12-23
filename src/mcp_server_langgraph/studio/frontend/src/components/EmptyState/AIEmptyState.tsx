/**
 * AIEmptyState Component
 *
 * An AI-enhanced wrapper around the EmptyState component.
 * Uses useAIEmptyState hook to fetch personalized suggestions from
 * the AI backend and falls back to EmptyStateRegistry when unavailable.
 *
 * Phase 6.2: AI-Native Integration Layer
 *
 * @example
 * <AIEmptyState
 *   context="workflows"
 *   onNavigate={(path) => navigate(path)}
 *   showConfidence
 * />
 */

import React, { useCallback } from "react";
import { Sparkles, ArrowRight } from "lucide-react";
import {
  EmptyState,
  type EmptyStateContext,
  type EmptyStateVariant,
} from "./EmptyState";
import {
  useAIEmptyState,
  type AISuggestion,
} from "../../hooks/useAIEmptyState";
import { cn } from "../../utils/cn";

/**
 * AIEmptyState component props
 */
export interface AIEmptyStateProps {
  /** Context determines the content and icon */
  context: EmptyStateContext;
  /** Display variant */
  variant?: EmptyStateVariant;
  /** Additional CSS classes */
  className?: string;
  /** Custom test ID */
  testId?: string;
  /** Enable AI-powered suggestions (default: true) */
  enableAI?: boolean;
  /** Show confidence indicator for AI suggestions */
  showConfidence?: boolean;
  /** Callback for navigation actions */
  onNavigate?: (path: string) => void;
  /** Callback for modal actions */
  onModal?: (modalId: string) => void;
  /** Callback for focus actions */
  onFocus?: (elementId: string) => void;
}

/**
 * Create a trigger button from an AI suggestion
 */
function AISuggestionTrigger({
  suggestion,
  showConfidence,
  onClick,
}: {
  suggestion: AISuggestion;
  showConfidence?: boolean;
  onClick: () => void;
}): React.ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
        "bg-indigo-600 hover:bg-indigo-700 text-white",
        "transition-colors duration-150",
        "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2",
      )}
    >
      {showConfidence && suggestion.confidence >= 0.85 && (
        <Sparkles
          size={16}
          data-testid="ai-suggestion-indicator"
          className="text-yellow-300"
        />
      )}
      <span>{suggestion.text}</span>
      {suggestion.action === "navigate" && <ArrowRight size={16} />}
    </button>
  );
}

/**
 * Create a fallback trigger button from registry config
 */
function FallbackTrigger({
  action,
  target,
  onClick,
}: {
  action: string;
  target: string;
  onClick: () => void;
}): React.ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
        "bg-gray-600 hover:bg-gray-700 text-white",
        "transition-colors duration-150",
        "focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2",
      )}
      data-target={target}
    >
      <span>{action}</span>
      <ArrowRight size={16} />
    </button>
  );
}

/**
 * AIEmptyState - An AI-enhanced empty state component
 *
 * Fetches personalized suggestions from AI backend and integrates
 * them into the Fogg-model-aware EmptyState component.
 */
export function AIEmptyState({
  context,
  variant = "default",
  className,
  testId,
  enableAI = true,
  showConfidence = false,
  onNavigate,
  onModal,
  onFocus,
}: AIEmptyStateProps): React.ReactElement {
  // Fetch AI suggestions (hook internally uses persona for fallback config)
  const {
    suggestions,
    primarySuggestion,
    fallbackConfig,
    isLoading,
    isAIAvailable,
  } = useAIEmptyState({
    context,
    enabled: enableAI,
  });

  // Use fallbackConfig from hook (it already calls getEmptyStateConfig with correct persona)
  const registryConfig = fallbackConfig;

  // Handle suggestion click
  const handleSuggestionClick = useCallback(
    (suggestion: AISuggestion) => {
      switch (suggestion.action) {
        case "navigate":
          onNavigate?.(suggestion.target);
          break;
        case "modal":
          onModal?.(suggestion.target);
          break;
        case "focus":
          onFocus?.(suggestion.target);
          break;
      }
    },
    [onNavigate, onModal, onFocus],
  );

  // Handle fallback trigger click
  const handleFallbackClick = useCallback(() => {
    if (registryConfig.target.startsWith("/")) {
      onNavigate?.(registryConfig.target);
    } else {
      onModal?.(registryConfig.target);
    }
  }, [registryConfig.target, onNavigate, onModal]);

  // Determine trigger content
  const trigger =
    isAIAvailable && primarySuggestion ? (
      <AISuggestionTrigger
        suggestion={primarySuggestion}
        showConfidence={showConfidence}
        onClick={() => handleSuggestionClick(primarySuggestion)}
      />
    ) : (
      <FallbackTrigger
        action={registryConfig.action}
        target={registryConfig.target}
        onClick={handleFallbackClick}
      />
    );

  // Secondary suggestions as additional triggers
  const secondSuggestion = suggestions[1];
  const secondaryTrigger =
    isAIAvailable && suggestions.length > 1 && secondSuggestion ? (
      <button
        type="button"
        onClick={() => handleSuggestionClick(secondSuggestion)}
        className={cn(
          "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
          "border border-gray-300 dark:border-gray-600",
          "text-gray-700 dark:text-gray-300",
          "hover:bg-gray-50 dark:hover:bg-gray-800",
          "transition-colors duration-150",
        )}
      >
        <span>{secondSuggestion.text}</span>
      </button>
    ) : undefined;

  // Use AI or fallback content
  const title =
    isAIAvailable && primarySuggestion
      ? registryConfig.title // Keep registry title even with AI
      : registryConfig.title;

  const motivation = registryConfig.motivation;
  const ability = registryConfig.ability;

  return (
    <EmptyState
      context={context}
      title={title}
      motivation={motivation}
      ability={ability}
      trigger={trigger}
      secondaryTrigger={secondaryTrigger}
      variant={variant}
      isLoading={isLoading}
      className={className}
      testId={testId}
    />
  );
}

export default AIEmptyState;
