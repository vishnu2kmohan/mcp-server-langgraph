/**
 * useAutoSessionTitle Hook
 *
 * Automatically generates a session title from the first user message
 * using AI-powered title generation.
 *
 * The hook monitors when:
 * 1. A session has a default name ("New Chat", "New Session", etc.)
 * 2. A user sends their first message
 *
 * Then it calls the title generation API and renames the session.
 */

import { useCallback, useRef } from "react";
import { useGenerateSessionTitleMutation } from "../api";
import { useAppDispatch } from "../store/hooks";
import { renameSession } from "../store/slices/sessionSlice";
import { devLogger } from "../utils/devLogger";

// Create prefixed logger for this hook
const logger = devLogger.withPrefix("[AutoSessionTitle]");

// Default names that indicate the session hasn't been named yet
const DEFAULT_SESSION_NAMES = [
  "new chat",
  "new session",
  "untitled",
  "untitled session",
  "",
];

/**
 * Check if a session name is a default/unnamed session
 */
function isDefaultSessionName(name: string | undefined | null): boolean {
  if (!name) return true;
  return DEFAULT_SESSION_NAMES.includes(name.toLowerCase().trim());
}

/**
 * Return type for useAutoSessionTitle hook
 */
export interface UseAutoSessionTitleReturn {
  /**
   * Called when a user sends a message.
   * If it's the first message in an unnamed session, generates a title.
   */
  onUserMessage: (
    sessionId: string,
    sessionName: string | undefined,
    message: string,
    messageCount: number,
  ) => void;
  /**
   * Whether title generation is in progress
   */
  isGenerating: boolean;
}

/**
 * Hook for auto-generating session titles from the first user message
 *
 * @example
 * ```tsx
 * const { onUserMessage, isGenerating } = useAutoSessionTitle();
 *
 * const handleSubmit = async () => {
 *   // Send the message first
 *   dispatch(addMessage(userMessage));
 *   startStream(sessionId, content);
 *
 *   // Trigger title generation for first message
 *   onUserMessage(sessionId, session.name, content, session.messages.length);
 * };
 * ```
 */
export function useAutoSessionTitle(): UseAutoSessionTitleReturn {
  const dispatch = useAppDispatch();
  const [generateTitle, { isLoading: isGenerating }] =
    useGenerateSessionTitleMutation();

  // Track which sessions we've already generated titles for
  const generatedSessionsRef = useRef<Set<string>>(new Set());

  const onUserMessage = useCallback(
    async (
      sessionId: string,
      sessionName: string | undefined,
      message: string,
      messageCount: number,
    ) => {
      // Only generate for first message in unnamed sessions
      if (messageCount > 0) return; // Not the first message
      if (!isDefaultSessionName(sessionName)) return; // Already has a custom name
      if (generatedSessionsRef.current.has(sessionId)) return; // Already generated

      // Mark as generating to prevent duplicate calls
      generatedSessionsRef.current.add(sessionId);

      try {
        // Call the title generation API
        const result = await generateTitle({ message }).unwrap();

        if (result.title) {
          // Rename the session with the generated title
          await dispatch(
            renameSession({
              sessionId,
              name: result.title,
            }),
          );
        }
      } catch (error) {
        // Title generation failed - remove from set so user can try again
        generatedSessionsRef.current.delete(sessionId);
        logger.warn("Failed to generate session title:", error);
      }
    },
    [dispatch, generateTitle],
  );

  return {
    onUserMessage,
    isGenerating,
  };
}

export default useAutoSessionTitle;
