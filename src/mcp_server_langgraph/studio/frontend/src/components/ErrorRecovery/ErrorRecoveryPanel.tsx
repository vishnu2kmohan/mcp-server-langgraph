/**
 * ErrorRecoveryPanel Component
 *
 * Sprint 3 - Phase 6.4: AI Error Recovery
 *
 * Displays AI-powered error analysis and recovery suggestions.
 * Provides contextual guidance for resolving errors based on
 * their classification and similar past issues.
 */

import React, { useEffect } from "react";
import { useAIErrorRecovery, type AIRecoverySuggestion } from "../../hooks/useAIErrorRecovery";

// =============================================================================
// Types
// =============================================================================

export interface ErrorRecoveryPanelProps {
  /** The error to analyze and recover from */
  error: Error;
  /** Additional context about where the error occurred */
  context?: Record<string, unknown>;
  /** Called when user clicks a retry suggestion */
  onRetry?: () => void;
  /** Called when user dismisses the panel */
  onDismiss?: () => void;
  /** Called when user clicks a navigate suggestion */
  onNavigate?: (path: string) => void;
  /** Called when user clicks contact support */
  onContact?: () => void;
  /** Show confidence percentages for suggestions */
  showConfidence?: boolean;
  /** Show similar resolved issues */
  showSimilarIssues?: boolean;
  /** Custom className for styling */
  className?: string;
  /** Test ID for testing */
  testId?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get icon for suggestion action type
 */
function getSuggestionIcon(action: AIRecoverySuggestion["action"]): string {
  switch (action) {
    case "retry":
      return "🔄";
    case "simplify":
      return "✂️";
    case "navigate":
      return "➡️";
    case "contact":
      return "📧";
    case "wait":
      return "⏳";
    default:
      return "💡";
  }
}

/**
 * Get category display color
 */
function getCategoryColor(category: string): string {
  switch (category) {
    case "network":
      return "#f59e0b"; // amber
    case "authentication":
      return "#ef4444"; // red
    case "authorization":
      return "#dc2626"; // dark red
    case "validation":
      return "#3b82f6"; // blue
    case "quota":
      return "#8b5cf6"; // purple
    case "server":
      return "#f97316"; // orange
    default:
      return "#6b7280"; // gray
  }
}

/**
 * Get default navigation path for action
 */
function getNavigationPath(action: AIRecoverySuggestion["action"]): string {
  switch (action) {
    case "navigate":
      return "/login";
    default:
      return "/";
  }
}

// =============================================================================
// Component
// =============================================================================

export function ErrorRecoveryPanel({
  error,
  context,
  onRetry,
  onDismiss,
  onNavigate,
  onContact,
  showConfidence = false,
  showSimilarIssues = false,
  className = "",
  testId = "error-recovery-panel",
}: ErrorRecoveryPanelProps): React.ReactElement {
  const { analyze, isAnalyzing, lastAnalysis, analysisError } =
    useAIErrorRecovery();

  // Analyze error on mount
  useEffect(() => {
    analyze(error, context);
  }, [analyze, error, context]);

  /**
   * Handle suggestion button click
   */
  const handleSuggestionClick = (suggestion: AIRecoverySuggestion) => {
    switch (suggestion.action) {
      case "retry":
      case "wait":
        onRetry?.();
        break;
      case "navigate":
        onNavigate?.(getNavigationPath(suggestion.action));
        break;
      case "contact":
        onContact?.();
        break;
      case "simplify":
        // For simplify, we just dismiss - user needs to fix input
        onDismiss?.();
        break;
    }
  };

  // Loading state
  if (isAnalyzing) {
    return (
      <div
        role="alert"
        className={`error-recovery-panel loading ${className}`}
        data-testid={testId}
      >
        <div
          className="loading-indicator"
          data-testid="error-recovery-loading"
        >
          <span className="spinner" aria-hidden="true">⏳</span>
          <span>Analyzing error...</span>
        </div>
      </div>
    );
  }

  // Fallback UI when AI analysis fails or no analysis available
  const analysis = lastAnalysis;
  const hasSuggestions = analysis && analysis.suggestions.length > 0;

  return (
    <div
      role="alert"
      className={`error-recovery-panel ${className}`}
      data-testid={testId}
    >
      {/* Error Header */}
      <div className="error-header">
        <span className="error-icon" aria-hidden="true">⚠️</span>
        <div className="error-info">
          <h3 className="error-title">{error.message}</h3>
          {analysis && (
            <span
              className="error-category"
              style={{
                backgroundColor: getCategoryColor(analysis.classification.category),
              }}
            >
              {analysis.classification.category}
            </span>
          )}
        </div>
      </div>

      {/* Root Cause */}
      {analysis && (
        <p className="root-cause">{analysis.rootCause}</p>
      )}

      {/* Suggestions */}
      <div className="suggestions">
        {hasSuggestions ? (
          analysis.suggestions.map((suggestion, index) => (
            <button
              key={index}
              className="suggestion-button"
              onClick={() => handleSuggestionClick(suggestion)}
              aria-label={suggestion.label}
            >
              <span className="suggestion-icon" aria-hidden="true">
                {getSuggestionIcon(suggestion.action)}
              </span>
              <span className="suggestion-content">
                <span className="suggestion-label">{suggestion.label}</span>
                {suggestion.guidance && (
                  <span className="suggestion-guidance">{suggestion.guidance}</span>
                )}
                {showConfidence && suggestion.estimatedSuccess !== undefined && (
                  <span className="suggestion-confidence">
                    {Math.round(suggestion.estimatedSuccess * 100)}% success rate
                  </span>
                )}
              </span>
            </button>
          ))
        ) : (
          // Fallback suggestion when no AI suggestions
          <button
            className="suggestion-button"
            onClick={() => onRetry?.()}
            aria-label="Try again"
          >
            <span className="suggestion-icon" aria-hidden="true">🔄</span>
            <span className="suggestion-content">
              <span className="suggestion-label">Try again</span>
            </span>
          </button>
        )}
      </div>

      {/* Similar Issues */}
      {showSimilarIssues && analysis?.similarIssues && analysis.similarIssues.length > 0 && (
        <div className="similar-issues">
          <h4>Similar Issues</h4>
          <ul>
            {analysis.similarIssues.map((issue) => (
              <li key={issue.id}>
                <span className="issue-resolution">{issue.resolution}</span>
                <span className="issue-success-rate">
                  {Math.round(issue.successRate * 100)}% success rate
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dismiss Button */}
      <button
        className="dismiss-button"
        onClick={onDismiss}
        aria-label="Dismiss"
      >
        Dismiss
      </button>

      {/* Analysis Error Notice */}
      {analysisError && (
        <p className="analysis-error">
          <small>AI analysis unavailable. Showing default options.</small>
        </p>
      )}
    </div>
  );
}

export default ErrorRecoveryPanel;
