/**
 * useSessionAutoName Hook
 *
 * Automatically generates and applies AI-powered session titles
 * based on the first user message, similar to ChatGPT/Claude behavior.
 *
 * Features:
 * - Triggers after first user message for sessions with default names
 * - Uses AI to generate contextual, descriptive titles
 * - Only triggers once per session to avoid repeated renames
 * - Respects user's custom session names
 */

import { useEffect, useRef, useMemo } from "react";
import { useGenerateSessionTitleMutation } from "../api";
import { useAppDispatch } from "../store/hooks";
import { renameSession } from "../store/slices/sessionSlice";

/** Default session names that trigger auto-naming */
const DEFAULT_SESSION_NAMES = [
  "new chat",
  "untitled session",
  "untitled",
  "new session",
];

export interface UseSessionAutoNameOptions {
  /** The current session ID */
  sessionId?: string;
  /** Messages in the current session */
  messages: Array<{ role: string; content: string }>;
  /** Current session name */
  currentName?: string;
  /** Whether auto-naming is enabled */
  enabled?: boolean;
}

export interface UseSessionAutoNameResult {
  /** Whether title generation is in progress */
  isGenerating: boolean;
  /** Whether generation was successful */
  isSuccess: boolean;
  /** The generated title (if available) */
  generatedTitle?: string;
  /** Confidence score of the generated title */
  confidence?: number;
  /** Whether the session has a default name */
  hasDefaultName: boolean;
  /** Error message if generation failed */
  error?: string;
}

/**
 * Hook for automatic AI-powered session naming
 *
 * @example
 * ```tsx
 * const { isGenerating, generatedTitle } = useSessionAutoName({
 *   sessionId: currentSession?.id,
 *   messages: messages.map((m) => ({ role: m.role, content: m.content })),
 *   currentName: currentSession?.name,
 *   enabled: true,
 * });
 * ```
 */
export function useSessionAutoName({
  sessionId,
  messages,
  currentName,
  enabled = true,
}: UseSessionAutoNameOptions): UseSessionAutoNameResult {
  const dispatch = useAppDispatch();
  const [generateTitle, { isLoading, isSuccess, data, error }] =
    useGenerateSessionTitleMutation();

  // Track if we've already attempted to generate a title for this session
  const hasAttemptedRef = useRef<Set<string>>(new Set());

  // Check if the session has a default name
  const hasDefaultName = useMemo(() => {
    if (!currentName) return true;
    const normalizedName = currentName.toLowerCase().trim();
    return DEFAULT_SESSION_NAMES.some((defaultName) =>
      normalizedName.includes(defaultName),
    );
  }, [currentName]);

  // Get the first user message
  const firstUserMessage = useMemo(() => {
    return messages.find((m) => m.role === "user");
  }, [messages]);

  // Determine if we should trigger generation
  const shouldGenerate = useMemo(() => {
    if (!enabled) return false;
    if (!sessionId) return false;
    if (!hasDefaultName) return false;
    if (!firstUserMessage) return false;
    if (hasAttemptedRef.current.has(sessionId)) return false;
    return true;
  }, [enabled, sessionId, hasDefaultName, firstUserMessage]);

  // Trigger title generation
  useEffect(() => {
    if (!shouldGenerate || !sessionId || !firstUserMessage) return;

    // Mark as attempted immediately to prevent re-triggering
    hasAttemptedRef.current.add(sessionId);

    // Generate title from first few messages (up to 3)
    const messagesToSend = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(0, 3);

    generateTitle({
      messages: messagesToSend,
      session_id: sessionId,
    });
  }, [shouldGenerate, sessionId, firstUserMessage, messages, generateTitle]);

  // Handle successful title generation
  useEffect(() => {
    if (isSuccess && data?.title && data?.confidence > 0.5 && sessionId) {
      dispatch(renameSession({ sessionId, name: data.title }));
    }
  }, [isSuccess, data, sessionId, dispatch]);

  return {
    isGenerating: isLoading,
    isSuccess,
    generatedTitle: data?.title,
    confidence: data?.confidence,
    hasDefaultName,
    error: error ? String(error) : undefined,
  };
}

export default useSessionAutoName;
