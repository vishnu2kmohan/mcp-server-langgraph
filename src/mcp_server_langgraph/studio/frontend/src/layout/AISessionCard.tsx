/**
 * AISessionCard Component
 *
 * Sprint 2: Session Intelligence
 * - Displays AI-generated session summary
 * - Shows key topics as tags
 * - Indicates loading state
 * - Handles click events for session selection
 *
 * Uses useSessionSummary hook from useSessionIntelligence.
 */

import React from "react";
import { useSessionSummary } from "../hooks/useSessionIntelligence";

/**
 * Props for AISessionCard component
 */
export interface AISessionCardProps {
  /** Unique session identifier */
  sessionId: string;
  /** Session title */
  title: string;
  /** User ID for AI analysis */
  userId: string;
  /** Whether to show AI-generated summary */
  showSummary?: boolean;
  /** Whether to show key topics as tags */
  showTopics?: boolean;
  /** Session timestamp */
  timestamp?: Date;
  /** Click handler for session selection */
  onClick?: (sessionId: string) => void;
  /** Whether this session is currently active/selected */
  isActive?: boolean;
  /** Enable AI features (default: true) */
  enableAI?: boolean;
}

/**
 * AISessionCard displays a session with optional AI-powered insights.
 *
 * Features:
 * - Session title and timestamp
 * - AI-generated one-line summary
 * - Key topics as clickable tags
 * - Loading skeleton during AI analysis
 * - Active state styling
 *
 * @example
 * ```tsx
 * <AISessionCard
 *   sessionId="session-123"
 *   title="React Development"
 *   userId="user-456"
 *   showSummary
 *   showTopics
 *   onClick={(id) => setActiveSession(id)}
 *   isActive={activeSession === "session-123"}
 * />
 * ```
 */
export function AISessionCard({
  sessionId,
  title,
  userId,
  showSummary = false,
  showTopics = false,
  timestamp,
  onClick,
  isActive = false,
  enableAI = true,
}: AISessionCardProps): React.ReactElement {
  // Only fetch AI data when AI is enabled and we need it
  const shouldFetchAI = enableAI && (showSummary || showTopics);

  const { summary, keyTopics, isLoading, error } = useSessionSummary({
    userId,
    sessionId,
    enabled: shouldFetchAI,
  });

  const handleClick = () => {
    if (onClick) {
      onClick(sessionId);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleClick();
    }
  };

  // Format timestamp if provided
  const formattedTimestamp = timestamp
    ? new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(timestamp)
    : null;

  return (
    <div
      data-testid="session-card"
      className={`session-card ${isActive ? "active" : ""}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
    >
      {/* Session Title */}
      <div className="session-card-header">
        <h4 className="session-card-title">{title}</h4>
        {formattedTimestamp && (
          <span className="session-card-timestamp">{formattedTimestamp}</span>
        )}
      </div>

      {/* AI Loading State */}
      {shouldFetchAI && isLoading && (
        <div data-testid="ai-loading" className="session-card-loading">
          <div className="skeleton skeleton-text" />
        </div>
      )}

      {/* AI Summary */}
      {showSummary && enableAI && !isLoading && !error && summary && (
        <p className="session-card-summary">{summary}</p>
      )}

      {/* Key Topics */}
      {showTopics && enableAI && !isLoading && !error && keyTopics.length > 0 && (
        <div className="session-card-topics">
          {keyTopics.map((topic, index) => (
            <span key={`${topic}-${index}`} className="session-card-topic-tag">
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Error State - show gracefully without breaking the card */}
      {error && enableAI && (
        <div className="session-card-error" data-testid="ai-error">
          <span className="sr-only">AI insights unavailable</span>
        </div>
      )}
    </div>
  );
}

export default AISessionCard;
