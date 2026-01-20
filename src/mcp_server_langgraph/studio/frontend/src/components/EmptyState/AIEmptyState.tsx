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

import { Button } from "@/components/UI";

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

  // ==========================================================================
  // New props (Sprint 2 - AIEmptyState Foundation)
  // ==========================================================================

  /**
   * Empty state type: "empty" (true empty) or "no-matches" (filtered empty)
   * @default "empty"
   */
  emptyType?: "empty" | "no-matches";
  /** Search query to display in "no-matches" title */
  searchQuery?: string;
  /** Custom action callback (takes precedence over onNavigate/registry target) */
  onAction?: () => void;
  /** Custom action label (overrides registry action text) */
  actionLabel?: string;
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
    <Button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
        "bg-primary-10 hover:bg-primary-11 text-neutral-12",
        "transition-colors duration-150",
        "focus:outline-none focus:ring-2 focus:ring-primary-9 focus:ring-offset-2",
      )}
    >
      {showConfidence && suggestion.confidence >= 0.85 && (
        <Sparkles
          size={16}
          data-testid="ai-suggestion-indicator"
          className="text-warning-6"
        />
      )}
      <span>{suggestion.text}</span>
      {suggestion.action === "navigate" && <ArrowRight size={16} />}
    </Button>
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
    <Button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
        "bg-neutral-5 hover:bg-neutral-4 text-neutral-12",
        "transition-colors duration-150",
        "focus:outline-none focus:ring-2 focus:ring-neutral-8 focus:ring-offset-2",
      )}
      data-target={target}
    >
      <span>{action}</span>
      <ArrowRight size={16} />
    </Button>
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
  // New props (Sprint 2)
  emptyType = "empty",
  searchQuery,
  onAction,
  actionLabel: actionLabelProp,
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

  // Handle fallback trigger click - onAction takes precedence
  const handleFallbackClick = useCallback(() => {
    // Custom action takes precedence (for modals, custom handlers)
    if (onAction) {
      onAction();
      return;
    }
    // Default to registry navigation/modal behavior
    if (registryConfig.target.startsWith("/")) {
      onNavigate?.(registryConfig.target);
    } else {
      onModal?.(registryConfig.target);
    }
  }, [onAction, registryConfig.target, onNavigate, onModal]);

  // Determine action label (prop overrides registry)
  const actionLabel = actionLabelProp ?? registryConfig.action;

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
        action={actionLabel}
        target={registryConfig.target}
        onClick={handleFallbackClick}
      />
    );

  // Secondary suggestions as additional triggers
  const secondSuggestion = suggestions[1];
  const secondaryTrigger =
    isAIAvailable && suggestions.length > 1 && secondSuggestion ? (
      <Button
        type="button"
        onClick={() => handleSuggestionClick(secondSuggestion)}
        className={cn(
          "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
          "border border-neutral-5",
          "text-neutral-11",
          "hover:bg-neutral-1",
          "transition-colors duration-150",
        )}
      >
        <span>{secondSuggestion.text}</span>
      </Button>
    ) : undefined;

  // Determine title based on emptyType
  // "no-matches" shows a search-oriented title, "empty" uses registry default
  const title =
    emptyType === "no-matches"
      ? searchQuery
        ? `No ${context} matching "${searchQuery}"`
        : `No ${context} found`
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
