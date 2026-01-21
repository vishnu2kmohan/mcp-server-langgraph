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
  forwardRef,
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
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { devLogger } from "../utils/devLogger";
import { sessionTelemetry } from "../utils/sessionTelemetry";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { useAISuggestionsFetch } from "../hooks/useAISuggestionsFetch";
import {
  CanvasShortcutsMenu,
  type CanvasShortcutAction,
} from "./CanvasShortcutsMenu";
import { SuggestionsFooterBar } from "./SuggestionsFooterBar";

// AI Components (Phase 4) - lazy-loaded for reduced bundle size
import { LazySuggestionsPanel, type Suggestion } from "../ai/lazy";
import type { AISuggestion } from "../types/artifacts";

import { Button } from "@/components/UI";

// Save operation status for optimistic UI feedback
type SaveStatus = "idle" | "saving" | "saved" | "error";

const logger = devLogger.withPrefix("[ConnectedCanvasPanel]");

// =============================================================================
// Types
// =============================================================================

export interface ConnectedCanvasPanelProps {
  /** Additional class name */
  className?: string;
  /** User ID for AI features (format: "user:username") */
  userId?: string;
  /** Current persona for RBAC-aware AI responses */
  persona?: string;
}

// =============================================================================
// Component
// =============================================================================

export const ConnectedCanvasPanel = forwardRef<
  HTMLDivElement,
  ConnectedCanvasPanelProps
>(function ConnectedCanvasPanel({ className, userId, persona }, ref) {
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
  // Phase 4: New footer bar for suggestions (replaces floating panel)
  const suggestionsFooterEnabled = useFeatureFlag("suggestions_footer_bar");

  // Track loading state for canvas shortcut actions
  const [shortcutActionLoading, setShortcutActionLoading] = useState(false);

  // Suggestions panel state (opt-in mode - user must click sparkles to show)
  const [suggestionsPanelVisible, setSuggestionsPanelVisible] = useState(false);
  const [suggestionsPanelExpanded, setSuggestionsPanelExpanded] =
    useState(true);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // Clear selected artifact when session changes to prevent stale selection
  // This fixes the "sticky canvas selection" bug where artifacts from previous
  // sessions would remain selected when switching to a new session.
  const prevSessionIdRef = useRef(sessionId);
  useEffect(() => {
    if (prevSessionIdRef.current !== sessionId) {
      logger.debug("Session changed, clearing artifact selection", {
        previousSession: prevSessionIdRef.current,
        newSession: sessionId,
      });
      dispatch(setSelectedArtifactId(null));
      prevSessionIdRef.current = sessionId;
    }
  }, [sessionId, dispatch]);

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

  // Reset selected artifact when switching sessions to avoid stale selection IDs
  const previousSessionId = useRef<string | null>(null);
  useEffect(() => {
    const activeSessionId = loaderData?.sessionId ?? null;
    if (
      previousSessionId.current &&
      activeSessionId &&
      previousSessionId.current !== activeSessionId
    ) {
      dispatch(setSelectedArtifactId(null));
    }
    previousSessionId.current = activeSessionId;
  }, [dispatch, loaderData?.sessionId]);

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
  // autoFetch: false for opt-in mode - user must click sparkles to fetch
  const {
    suggestions,
    isLoading: suggestionsLoading,
    acceptSuggestion,
    dismissSuggestion,
    refresh: refreshSuggestions,
  } = useAISuggestionsFetch({
    artifactId: shouldFetchSuggestions ? selectedArtifactId : null,
    sessionId,
    enabled: shouldFetchSuggestions,
    debounceMs: 500,
    autoFetch: false, // Opt-in: don't auto-fetch, wait for user to click sparkles
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
        const response = await authenticatedFetch(
          `/api/v1/artifacts/${artifactId}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              content,
              edit_metadata: { edited_by: "user" },
            }),
          },
        );

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

  // Sparkles trigger handler - opens panel and fetches suggestions (opt-in)
  const handleSparklesTrigger = useCallback(() => {
    logger.debug("Sparkles trigger clicked, showing suggestions panel");
    setSuggestionsPanelVisible(true);
    setSuggestionsPanelExpanded(true);
    // Fetch suggestions on demand
    refreshSuggestions();
  }, [refreshSuggestions]);

  // Handle suggestions panel toggle
  const handleSuggestionsPanelToggle = useCallback(() => {
    setSuggestionsPanelExpanded((prev) => !prev);
  }, []);

  // Handle suggestions panel refresh
  const handleSuggestionsPanelRefresh = useCallback(() => {
    refreshSuggestions();
  }, [refreshSuggestions]);

  // Convert hook suggestions to AISuggestion format for footer bar
  // Suggestion type has: id, type, content, confidence
  // AISuggestion needs: id, type, label, description, confidence
  const footerSuggestions: AISuggestion[] = useMemo(
    () =>
      suggestions.map((s) => ({
        id: s.id,
        type: s.type,
        label: s.type.charAt(0).toUpperCase() + s.type.slice(1), // Capitalize type as label
        description: s.content?.slice(0, 100) ?? "", // Use content preview as description
        confidence: s.confidence ?? 0.8,
      })),
    [suggestions],
  );

  // Footer bar handlers
  const handleFooterAccept = useCallback(
    (suggestion: AISuggestion) => {
      const original = suggestions.find((s) => s.id === suggestion.id);
      if (original) {
        handleAcceptSuggestion(original);
      }
    },
    [suggestions, handleAcceptSuggestion],
  );

  const handleFooterDismiss = useCallback(
    (suggestion: AISuggestion) => {
      const original = suggestions.find((s) => s.id === suggestion.id);
      if (original) {
        handleDismissSuggestion(original);
      }
    },
    [suggestions, handleDismissSuggestion],
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
        const response = await authenticatedFetch(
          `/api/v1/ai/canvas/${action}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              artifact_id: selectedArtifactId,
              content: selectedArtifact.content,
              content_type: selectedArtifact.contentType,
              language: selectedArtifact.editMetadata?.language,
              session_id: sessionId,
            }),
          },
        );

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
      ref={ref}
      data-testid="canvas-panel"
      className={cn(
        "flex flex-col h-full relative",
        "bg-neutral-1",
        "border-l border-neutral-5",
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
              "bg-primary-3 dark:bg-primary-a6 text-primary-11 dark:text-primary-11",
            saveStatus === "saved" &&
              "bg-success-3 dark:bg-success-a6 text-success-11 dark:text-success-11",
            saveStatus === "error" &&
              "bg-error-3 dark:bg-error-a6 text-error-11 dark:text-error-11",
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
      {/* AI Suggestions Sparkles Trigger (Phase 4) - opt-in mode */}
      {/* Shows a sparkles button that users click to fetch and view suggestions */}
      {/* Hidden when footer bar is enabled (Phase 4 cleanup) */}
      {!suggestionsFooterEnabled &&
        aiSuggestionsEnabled &&
        selectedArtifactId &&
        !suggestionsPanelVisible && (
          <Button
            variant="primary"
            type="button"
            onClick={handleSparklesTrigger}
            data-testid="sparkles-trigger"
            aria-label="Get AI suggestions"
            className={cn(
              "absolute top-12 right-2 z-10",
              "p-2 rounded-lg shadow-md",
              "bg-neutral-1",
              "border border-neutral-5",
              "text-primary-11 hover:text-primary-11 dark:hover:text-primary-7",
              "hover:bg-primary-1 dark:hover:bg-primary-a3",
              "transition-colors",
            )}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="lucide lucide-sparkles"
            >
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
              <path d="M5 3v4" />
              <path d="M19 17v4" />
              <path d="M3 5h4" />
              <path d="M17 19h4" />
            </svg>
          </Button>
        )}
      {/* AI Suggestions Panel (Phase 4) - table view for reviewing suggestions */}
      {/* Lazy-loaded to reduce initial bundle size */}
      {/* Hidden when footer bar is enabled (Phase 4 cleanup) */}
      {!suggestionsFooterEnabled &&
        aiSuggestionsEnabled &&
        selectedArtifactId &&
        suggestionsPanelVisible && (
          <div className="absolute top-12 right-2 z-10 w-96">
            <Suspense fallback={null}>
              <LazySuggestionsPanel
                suggestions={suggestions}
                onAccept={handleAcceptSuggestion}
                onDismiss={handleDismissSuggestion}
                onRefresh={handleSuggestionsPanelRefresh}
                isLoading={suggestionsLoading}
                isExpanded={suggestionsPanelExpanded}
                onToggleExpand={handleSuggestionsPanelToggle}
              />
            </Suspense>
          </div>
        )}
      {/* Canvas Shortcuts Menu (Sprint 6) - gated by canvas_ai_palette feature flag */}
      {/* @deprecated: Hidden when suggestions_footer_bar is enabled (Phase 4) */}
      {!suggestionsFooterEnabled &&
        canvasAIPaletteEnabled &&
        selectedArtifactId && (
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
            "absolute bottom-16 right-4 z-notification",
            "max-w-sm px-4 py-3 rounded-lg shadow-lg",
            "bg-error-1 dark:bg-error-a9 border border-error-4 dark:border-error-7",
            "text-error-11 dark:text-error-11 text-sm",
            "animate-in fade-in slide-in-from-bottom-4 duration-200",
          )}
        >
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 flex-shrink-0 mt-0.5 text-error-11"
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
              <p className="mt-1 text-error-11 dark:text-error-11">
                {shortcutError}
              </p>
            </div>
            <Button
              variant="danger"
              className="ml-auto -mr-1 p-1 rounded hover:bg-error-3 dark:hover:bg-error-11"
              type="button"
              onClick={() => setShortcutError(null)}
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
            </Button>
          </div>
        </div>
      )}
      <CanvasWorkspace
        artifacts={artifacts}
        onArtifactSelect={handleArtifactSelect}
        onContentChange={handleContentChange}
        onSave={handleSave}
        enableArtifactHover
        className="flex-1 min-h-0"
        userId={userId}
        sessionId={sessionId}
        persona={persona}
        enableAI={aiSuggestionsEnabled}
      />
      {/* Suggestions Footer Bar (Phase 4) - replaces floating panel when enabled */}
      {suggestionsFooterEnabled && aiSuggestionsEnabled && selectedArtifactId && (
        <SuggestionsFooterBar
          suggestions={footerSuggestions}
          onAccept={handleFooterAccept}
          onDismiss={handleFooterDismiss}
          onRefresh={handleSuggestionsPanelRefresh}
          isLoading={suggestionsLoading}
          isExpanded={suggestionsPanelExpanded}
          onToggle={handleSuggestionsPanelToggle}
        />
      )}
      {/* Note: No <Outlet /> needed - chat routes don't render components.
          StudioShellLayout provides the full 3-panel UI for chat routes.
          The chatLoader provides data, but UI comes from SessionNav + ConversationPanel + CanvasPanel. */}
    </div>
  );
});

// Display name for DevTools
ConnectedCanvasPanel.displayName = "ConnectedCanvasPanel";
