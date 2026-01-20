/**
 * SimilarSessionsPanel Component
 *
 * Panel for displaying sessions similar to the currently selected session.
 * Uses AI-powered similarity detection via useSessionSimilarity hook.
 *
 * Features:
 * - Similar sessions list with similarity scores
 * - Common topic badges
 * - Click to navigate to similar session
 * - Loading and error states
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 */

import { useSessionSimilarity } from "../../hooks/useSessionIntelligence";
import { AlertCircle, RefreshCw, Sparkles } from "lucide-react";

import { Button } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export interface SimilarSessionsPanelProps {
  /** Current session ID to find similar sessions for */
  sessionId: string;
  /** User ID for the similarity query */
  userId: string;
  /** Optional mapping of session IDs to session names */
  sessionNames?: Record<string, string>;
  /** Maximum number of similar sessions to show */
  limit?: number;
  /** Additional CSS classes */
  className?: string;
  /** Callback when a similar session is selected */
  onSessionSelect?: (sessionId: string) => void;
}

// ==============================================================================
// Component
// ==============================================================================

export function SimilarSessionsPanel({
  sessionId,
  userId,
  sessionNames = {},
  limit = 5,
  className = "",
  onSessionSelect,
}: SimilarSessionsPanelProps) {
  const { similarSessions, isLoading, error, refetch } = useSessionSimilarity({
    userId,
    sessionId,
    limit,
    enabled: !!sessionId && !!userId,
  });

  // ---------------------------------------------------------------------------
  // Render loading state
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div
        data-testid="similar-sessions-loading"
        className={`similar-sessions-panel p-4 ${className}`}
      >
        <h3 className="text-sm font-medium text-neutral-12 mb-3 flex items-center gap-2">
          <Sparkles size={16} className="text-insight-9" />
          Similar Sessions
        </h3>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-neutral-3 rounded w-3/4 mb-2" />
              <div className="h-3 bg-neutral-3 rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render error state
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div
        data-testid="similar-sessions-error"
        className={`similar-sessions-panel p-4 ${className}`}
        role="alert"
      >
        <h3 className="text-sm font-medium text-neutral-12 mb-3 flex items-center gap-2">
          <Sparkles size={16} className="text-insight-9" />
          Similar Sessions
        </h3>
        <div className="text-center py-4">
          <AlertCircle
            className="mx-auto h-8 w-8 text-warning-9 mb-2"
            aria-hidden="true"
          />
          <p className="text-sm text-neutral-11 mb-3">
            Failed to load similar sessions
          </p>
          <Button
            variant="secondary"
            className=".5 px-3 py-1.5 text-sm text-neutral-11 bg-neutral-2 rounded-md hover:bg-neutral-3 focus:ring-insight-7"
            onClick={refetch}
          >
            <RefreshCw size={14} />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Hide panel when no similar sessions found
  // ---------------------------------------------------------------------------
  if (similarSessions.length === 0) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // Render similar sessions
  // ---------------------------------------------------------------------------
  return (
    <div className={`similar-sessions-panel p-4 ${className}`}>
      <h3 className="text-sm font-medium text-neutral-12 mb-3 flex items-center gap-2">
        <Sparkles size={16} className="text-insight-9" />
        Similar Sessions
      </h3>
      <div className="space-y-2" aria-label="Similar sessions">
        {similarSessions.map((session) => {
          const sessionName =
            sessionNames[session.sessionId] || session.sessionId;
          const scorePercent = Math.round(session.similarityScore * 100);

          return (
            <Button
              className="w-full text-left group p-2 rounded-md border border-neutral-5 hover:border-insight-5 dark:hover:border-insight-10 hover:bg-insight-1 dark:hover:bg-insight-a2 focus:ring-insight-7"
              key={session.sessionId}
              type="button"
              onClick={() => onSessionSelect?.(session.sessionId)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-neutral-12 truncate flex-1">
                  {sessionName}
                </span>
                <span className="text-xs font-medium text-insight-10 dark:text-insight-9 ml-2">
                  {scorePercent}%
                </span>
              </div>
              {session.commonTopics.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {session.commonTopics.map((topic) => (
                    <span
                      key={topic}
                      className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium bg-neutral-2 text-neutral-11 rounded"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              )}
            </Button>
          );
        })}
      </div>
    </div>
  );
}

export default SimilarSessionsPanel;
