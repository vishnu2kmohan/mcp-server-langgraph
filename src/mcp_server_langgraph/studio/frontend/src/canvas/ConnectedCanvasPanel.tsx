/**
 * ConnectedCanvasPanel
 *
 * Redux-connected wrapper for CanvasWorkspace that integrates with:
 * - React Router loaders (artifacts)
 * - Redux actions (setSelectedArtifactId)
 * - Nested route outlets
 * - API calls for saving artifact content
 *
 * Use this in StudioShellLayout instead of inline CanvasPanel.
 */
import {
  useCallback,
  useMemo,
  useState,
  useEffect,
  useRef,
  Suspense,
} from "react";
import { useRouteLoaderData, useRevalidator } from "react-router";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  setSelectedArtifactId,
  selectSelectedArtifactId,
} from "../store/slices/canvasSlice";
import { selectCurrentSession } from "../store/slices/sessionSlice";
import { CanvasWorkspace } from "./CanvasWorkspace";
import type { ChatLoaderData } from "../router/loaders";
import type { CanvasArtifact } from "../types/artifacts";
import { cn } from "../utils/cn";
import { getAuthToken } from "../utils/storage";
import { devLogger } from "../utils/devLogger";
import { sessionTelemetry } from "../utils/sessionTelemetry";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { useAISuggestionsFetch } from "../hooks/useAISuggestionsFetch";
import {
  CanvasShortcutsMenu,
  type CanvasShortcutAction,
} from "./CanvasShortcutsMenu";

// AI Components (Phase 4) - lazy-loaded for reduced bundle size
import { LazyInlineSuggestions, type Suggestion } from "../ai/lazy";

// Save operation status for optimistic UI feedback
type SaveStatus = "idle" | "saving" | "saved" | "error";

const logger = devLogger.withPrefix("[ConnectedCanvasPanel]");

// =============================================================================
// Types
// =============================================================================

export interface ConnectedCanvasPanelProps {
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ConnectedCanvasPanel({ className }: ConnectedCanvasPanelProps) {
  const dispatch = useAppDispatch();
  const revalidator = useRevalidator();

  // Track draft content for unsaved changes
  const [_draftContent, setDraftContent] = useState<Record<string, string>>({});
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Redux selectors
  const selectedArtifactId = useAppSelector(selectSelectedArtifactId);
  // Use optional chaining for session state (may not exist in tests)
  const currentSession = useAppSelector((state) =>
    state.session
      ? selectCurrentSession(state as { session: typeof state.session })
      : null,
  );
  const sessionId = currentSession?.id ?? "default-session";

  // Feature flags for AI features
  const aiSuggestionsEnabled = useFeatureFlag("ai_suggestions");
  const canvasAIPaletteEnabled = useFeatureFlag("canvas_ai_palette");

  // Track loading state for canvas shortcut actions
  const [shortcutActionLoading, setShortcutActionLoading] = useState(false);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // Derived state for backwards compatibility
  const isSaving = saveStatus === "saving";

  // Get artifacts from the chat loader (try both session and index routes)
  const sessionLoaderData = useRouteLoaderData("chat-session") as
    | ChatLoaderData
    | undefined;
  const indexLoaderData = useRouteLoaderData("chat-index") as
    | ChatLoaderData
    | undefined;
  const loaderData = sessionLoaderData ?? indexLoaderData;

  const artifacts = useMemo(
    () => loaderData?.artifacts ?? [],
    [loaderData?.artifacts],
  );

  // Find the currently selected artifact
  const selectedArtifact = useMemo(
    () => artifacts.find((a) => a.id === selectedArtifactId),
    [artifacts, selectedArtifactId],
  );

  // Only fetch suggestions for code content when enabled
  const shouldFetchSuggestions =
    aiSuggestionsEnabled &&
    !!selectedArtifact &&
    selectedArtifact.contentType === "code";

  // AI Suggestions - using useAISuggestionsFetch hook (Phase 4)
  const {
    suggestions,
    isLoading: suggestionsLoading,
    acceptSuggestion,
    dismissSuggestion,
  } = useAISuggestionsFetch({
    artifactId: shouldFetchSuggestions ? selectedArtifactId : null,
    sessionId,
    enabled: shouldFetchSuggestions,
    debounceMs: 500,
  });

  // Handlers for CanvasWorkspace callbacks
  const handleArtifactSelect = useCallback(
    (artifact: CanvasArtifact) => {
      dispatch(setSelectedArtifactId(artifact.id));
    },
    [dispatch],
  );

  // Track content changes in local state (draft)
  const handleContentChange = useCallback(
    (artifactId: string, content: string) => {
      setDraftContent((prev) => ({
        ...prev,
        [artifactId]: content,
      }));
      logger.debug("Content changed:", artifactId, content.length);
    },
    [],
  );

  // Save artifact content to the API with optimistic updates
  const handleSave = useCallback(
    async (artifactId: string, content: string) => {
      if (isSaving) return;

      // Clear any existing timeout
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      const startTime = Date.now();
      setSaveStatus("saving");
      setSaveError(null);

      try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/artifacts/${artifactId}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...(token && { Authorization: `Bearer ${token}` }),
          },
          credentials: "include",
          body: JSON.stringify({
            content,
            editedBy: "user",
          }),
        });

        if (response.ok) {
          logger.debug("Saved artifact:", artifactId);
          sessionTelemetry.trackArtifactSave({
            artifactId,
            success: true,
            durationMs: Date.now() - startTime,
            contentLength: content.length,
          });

          // Optimistic: Show "saved" status immediately
          setSaveStatus("saved");

          // Clear draft content for this artifact
          setDraftContent((prev) => {
            const next = { ...prev };
            delete next[artifactId];
            return next;
          });

          // Auto-dismiss "saved" indicator after 2 seconds
          saveTimeoutRef.current = setTimeout(() => {
            setSaveStatus("idle");
          }, 2000);

          // Revalidate to get the updated artifact from server
          revalidator.revalidate();
        } else {
          const errorMsg = `HTTP ${response.status}: ${response.statusText}`;
          logger.error("Failed to save artifact:", response.status);
          sessionTelemetry.trackArtifactSave({
            artifactId,
            success: false,
            durationMs: Date.now() - startTime,
            contentLength: content.length,
            error: errorMsg,
          });
          setSaveStatus("error");
          setSaveError(errorMsg);

          // Auto-dismiss error after 5 seconds
          saveTimeoutRef.current = setTimeout(() => {
            setSaveStatus("idle");
            setSaveError(null);
          }, 5000);
        }
      } catch (error) {
        const errorMsg =
          error instanceof Error ? error.message : "Unknown error";
        logger.error("Save request failed:", error);
        sessionTelemetry.trackArtifactSave({
          artifactId,
          success: false,
          durationMs: Date.now() - startTime,
          contentLength: content.length,
          error: errorMsg,
        });
        setSaveStatus("error");
        setSaveError(errorMsg);

        // Auto-dismiss error after 5 seconds
        saveTimeoutRef.current = setTimeout(() => {
          setSaveStatus("idle");
          setSaveError(null);
        }, 5000);
      }
    },
    [isSaving, revalidator],
  );

  // AI Suggestion handlers (Phase 4) - using hook methods for cache management
  const handleAcceptSuggestion = useCallback(
    (suggestion: Suggestion) => {
      logger.debug("Accepting suggestion:", suggestion.id, {
        suggestionType: suggestion.type,
        artifactId: selectedArtifactId,
      });

      // Remove the accepted suggestion from cache via hook
      acceptSuggestion(suggestion.id);

      // Apply suggestion content to the artifact
      if (selectedArtifactId && suggestion.content) {
        // Find current artifact to get existing content
        const currentArtifact = artifacts.find(
          (a) => a.id === selectedArtifactId,
        );
        if (currentArtifact) {
          let newContent: string;

          // Apply based on suggestion type
          switch (suggestion.type) {
            case "completion":
              // Append completion to existing content
              newContent = currentArtifact.content + suggestion.content;
              break;
            case "refactor":
            case "fix":
              // Replace entire content with suggestion
              newContent = suggestion.content;
              break;
            case "explain":
              // For explain, add as comment at top
              newContent = `/* AI Explanation:\n${suggestion.content}\n*/\n\n${currentArtifact.content}`;
              break;
            default:
              newContent = suggestion.content;
          }

          // Save the updated content
          handleSave(selectedArtifactId, newContent);
          logger.debug("Applied suggestion to artifact:", {
            artifactId: selectedArtifactId,
            suggestionType: suggestion.type,
            contentLength: newContent.length,
          });
        }
      }
    },
    [selectedArtifactId, artifacts, handleSave, acceptSuggestion],
  );

  const handleDismissSuggestion = useCallback(
    (suggestion: Suggestion) => {
      logger.debug("Dismissing suggestion:", suggestion.id, {
        suggestionType: suggestion.type,
        artifactId: selectedArtifactId,
      });
      // Remove the dismissed suggestion from cache via hook
      dismissSuggestion(suggestion.id);
    },
    [selectedArtifactId, dismissSuggestion],
  );

  // Track shortcut action error state for user feedback
  const [shortcutError, setShortcutError] = useState<string | null>(null);

  // Canvas Shortcuts Menu handler (Sprint 6)
  const handleShortcutAction = useCallback(
    async (action: CanvasShortcutAction) => {
      // Clear any previous error
      setShortcutError(null);

      if (!selectedArtifactId || !selectedArtifact) {
        logger.warn("No artifact selected for shortcut action:", action);
        setShortcutError("Please select an artifact first");
        return;
      }

      const startTime = Date.now();
      logger.debug("Shortcut action requested:", action, {
        artifactId: selectedArtifactId,
        contentType: selectedArtifact.contentType,
        language: selectedArtifact.editMetadata?.language,
      });

      setShortcutActionLoading(true);

      try {
        const token = getAuthToken();
        const response = await fetch(`/api/v1/ai/canvas/${action}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token && { Authorization: `Bearer ${token}` }),
          },
          credentials: "include",
          body: JSON.stringify({
            artifact_id: selectedArtifactId,
            content: selectedArtifact.content,
            content_type: selectedArtifact.contentType,
            language: selectedArtifact.editMetadata?.language,
            session_id: sessionId,
          }),
        });

        if (response.ok) {
          const result = await response.json();
          logger.debug("Shortcut action completed:", action, {
            resultLength: result.content?.length,
            durationMs: Date.now() - startTime,
          });

          // Apply the AI-generated content to the artifact
          if (result.content) {
            await handleSave(selectedArtifactId, result.content);
          }

          // Track successful canvas action
          sessionTelemetry.trackCanvasAction({
            artifactId: selectedArtifactId,
            action,
            contentType: selectedArtifact.contentType,
            language: selectedArtifact.editMetadata?.language,
            sessionId,
            success: true,
            durationMs: Date.now() - startTime,
          });
        } else {
          // Handle specific error codes
          let errorMessage: string;

          switch (response.status) {
            case 404:
              // Endpoint doesn't exist - feature not available
              errorMessage = `"${action}" is not yet available. This feature requires backend support.`;
              logger.warn("Canvas shortcut endpoint not found:", action);
              break;
            case 401:
            case 403:
              errorMessage = "Authentication required. Please sign in again.";
              break;
            case 429:
              errorMessage = "Too many requests. Please try again in a moment.";
              break;
            case 500:
            case 502:
            case 503:
              errorMessage =
                "AI service temporarily unavailable. Please try again.";
              break;
            default:
              errorMessage = `Failed to execute "${action}" (${response.status})`;
          }

          logger.error(
            "Shortcut action failed:",
            response.status,
            response.statusText,
          );
          setShortcutError(errorMessage);

          // Track failed canvas action
          sessionTelemetry.trackCanvasAction({
            artifactId: selectedArtifactId,
            action,
            contentType: selectedArtifact.contentType,
            language: selectedArtifact.editMetadata?.language,
            sessionId,
            success: false,
            durationMs: Date.now() - startTime,
            error: errorMessage,
          });

          // Auto-dismiss error after 5 seconds
          setTimeout(() => setShortcutError(null), 5000);
        }
      } catch (error) {
        // Network error or other exception
        const errorMessage =
          error instanceof Error && error.name === "AbortError"
            ? "Request timed out. Please try again."
            : "Network error. Please check your connection.";

        logger.error("Shortcut action error:", error);
        setShortcutError(errorMessage);

        // Track failed canvas action (network error)
        sessionTelemetry.trackCanvasAction({
          artifactId: selectedArtifactId,
          action,
          contentType: selectedArtifact.contentType,
          language: selectedArtifact.editMetadata?.language,
          sessionId,
          success: false,
          durationMs: Date.now() - startTime,
          error: errorMessage,
        });

        // Auto-dismiss error after 5 seconds
        setTimeout(() => setShortcutError(null), 5000);
      } finally {
        setShortcutActionLoading(false);
      }
    },
    [selectedArtifactId, selectedArtifact, sessionId, handleSave],
  );

  return (
    <div
      data-testid="canvas-panel"
      className={cn(
        "flex flex-col h-full relative",
        "bg-gray-50 dark:bg-gray-800",
        "border-l border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Save status indicator - optimistic feedback */}
      {saveStatus !== "idle" && (
        <div
          data-testid="save-status-indicator"
          className={cn(
            "absolute top-2 right-2 z-10 px-3 py-1.5 rounded-lg text-sm font-medium",
            "transition-all duration-200 shadow-lg",
            saveStatus === "saving" &&
              "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300",
            saveStatus === "saved" &&
              "bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300",
            saveStatus === "error" &&
              "bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300",
          )}
        >
          {saveStatus === "saving" && (
            <span className="flex items-center gap-1.5">
              <span className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
              Saving...
            </span>
          )}
          {saveStatus === "saved" && "Saved!"}
          {saveStatus === "error" && (saveError || "Save failed")}
        </div>
      )}

      {/* AI Inline Suggestions (Phase 4) - gated by ai_suggestions feature flag */}
      {/* Lazy-loaded to reduce initial bundle size */}
      {aiSuggestionsEnabled &&
        selectedArtifactId &&
        (suggestions.length > 0 || suggestionsLoading) && (
          <div className="absolute top-12 right-2 z-10 w-80">
            <Suspense fallback={null}>
              <LazyInlineSuggestions
                suggestions={suggestions}
                onAccept={handleAcceptSuggestion}
                onDismiss={handleDismissSuggestion}
                isLoading={suggestionsLoading}
              />
            </Suspense>
          </div>
        )}

      {/* Canvas Shortcuts Menu (Sprint 6) - gated by canvas_ai_palette feature flag */}
      {canvasAIPaletteEnabled && selectedArtifactId && (
        <div className="absolute bottom-4 right-4 z-10">
          <CanvasShortcutsMenu
            onAction={handleShortcutAction}
            isLoading={shortcutActionLoading}
            language={
              selectedArtifact?.editMetadata?.language ??
              selectedArtifact?.contentType
            }
          />
        </div>
      )}

      {/* Shortcut action error toast */}
      {shortcutError && (
        <div
          data-testid="shortcut-error-toast"
          role="alert"
          className={cn(
            "absolute bottom-16 right-4 z-20",
            "max-w-sm px-4 py-3 rounded-lg shadow-lg",
            "bg-red-50 dark:bg-red-900/80 border border-red-200 dark:border-red-700",
            "text-red-800 dark:text-red-200 text-sm",
            "animate-in fade-in slide-in-from-bottom-4 duration-200",
          )}
        >
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <div>
              <p className="font-medium">Action Failed</p>
              <p className="mt-1 text-red-600 dark:text-red-300">
                {shortcutError}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShortcutError(null)}
              className="ml-auto -mr-1 p-1 rounded hover:bg-red-100 dark:hover:bg-red-800 transition-colors"
              aria-label="Dismiss error"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      <CanvasWorkspace
        artifacts={artifacts}
        onArtifactSelect={handleArtifactSelect}
        onContentChange={handleContentChange}
        onSave={handleSave}
        className="h-full"
      />
      {/* Note: No <Outlet /> needed - chat routes don't render components.
          StudioShellLayout provides the full 3-panel UI for chat routes.
          The chatLoader provides data, but UI comes from SessionNav + ConversationPanel + CanvasPanel. */}
    </div>
  );
}
