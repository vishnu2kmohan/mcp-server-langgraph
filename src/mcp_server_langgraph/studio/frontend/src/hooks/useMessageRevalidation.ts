/**
 * useMessageRevalidation Hook
 *
 * Provides a way to revalidate React Router loader data after sending messages.
 *
 * In v2 routes with loaders:
 * 1. Message is sent (optimistically added to Redux)
 * 2. API call completes
 * 3. This hook triggers revalidation to sync loader data from server
 *
 * Usage:
 * ```tsx
 * function ChatPanel() {
 *   const { revalidateMessages, isRevalidating } = useMessageRevalidation();
 *
 *   const handleSend = async (message: string) => {
 *     await sendMessage(message);
 *     revalidateMessages();
 *   };
 * }
 * ```
 */
import { useRef, useMemo, useContext, useEffect, useCallback } from "react";
import { UNSAFE_DataRouterContext } from "react-router";
import { useStore } from "react-redux";
import type { RootState } from "../store";
import { useSessionTelemetry } from "../contexts/TelemetryContext";
import { useDebouncedCallback } from "./useDebounce";

// =============================================================================
// Types
// =============================================================================

interface UseMessageRevalidationOptions {
  /** Debounce time in milliseconds (default: 500) */
  debounceMs?: number;
  /** Whether to auto-revalidate on sendMessage completion (default: false) */
  autoRevalidate?: boolean;
}

interface UseMessageRevalidationResult {
  /** Trigger revalidation of loader data */
  revalidateMessages: (trigger?: "message_sent" | "manual") => void;
  /** Whether revalidation is in progress */
  isRevalidating: boolean;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for revalidating message data after mutations.
 *
 * This hook safely checks if we're in a data router context before using
 * the revalidator. If not in a data router (e.g., tests, legacy routes),
 * the revalidateMessages function is a no-op.
 *
 * @param options - Configuration options
 * @returns Object with revalidateMessages function and isRevalidating state
 */
export function useMessageRevalidation(
  options: UseMessageRevalidationOptions = {},
): UseMessageRevalidationResult {
  const { debounceMs = 500, autoRevalidate = false } = options;

  // Check if we're in a data router context
  const dataRouterContext = useContext(UNSAFE_DataRouterContext);
  const router = dataRouterContext?.router;

  // Get Redux store for auto-revalidation
  const store = useStore<RootState>();

  // Get telemetry from context
  const sessionTelemetry = useSessionTelemetry();

  // Track message count for auto-revalidation
  const lastMessageCount = useRef<number>(0);

  // Track if there's a pending revalidation (for telemetry)
  const hasPendingRevalidation = useRef(false);

  // The actual revalidation logic executed after debounce
  const executeRevalidation = useCallback(
    (trigger: "message_sent" | "manual" | "auto") => {
      if (!router) return;

      const startTime = Date.now();
      router.revalidate();
      hasPendingRevalidation.current = false;

      // Track executed revalidation
      sessionTelemetry.trackRevalidation({
        sessionId: store.getState().session.currentSession?.id,
        trigger,
        durationMs: Date.now() - startTime,
        debounced: false,
      });
    },
    [router, store, sessionTelemetry],
  );

  // Debounced version using the shared hook (handles cleanup automatically)
  const debouncedRevalidate = useDebouncedCallback(
    executeRevalidation,
    debounceMs,
  );

  // Wrapper that tracks debounced events
  const revalidateMessages = useCallback(
    (trigger: "message_sent" | "manual" = "message_sent") => {
      // If not in data router context, do nothing
      if (!router) {
        return;
      }

      // Track debounced event if there was a pending revalidation
      if (hasPendingRevalidation.current) {
        sessionTelemetry.trackRevalidation({
          trigger,
          durationMs: 0,
          debounced: true,
        });
      }

      hasPendingRevalidation.current = true;
      debouncedRevalidate(trigger);
    },
    [router, debouncedRevalidate, sessionTelemetry],
  );

  // Auto-revalidate when messages change in Redux
  useEffect(() => {
    if (!autoRevalidate || !router) {
      return;
    }

    // Subscribe to store changes
    const unsubscribe = store.subscribe(() => {
      const state = store.getState();
      const currentMessages = state.session.currentSession?.messages || [];
      const currentCount = currentMessages.length;

      // If message count increased, trigger revalidation with "auto" trigger
      if (currentCount > lastMessageCount.current) {
        // Track debounced event if there was a pending revalidation
        if (hasPendingRevalidation.current) {
          sessionTelemetry.trackRevalidation({
            trigger: "auto",
            durationMs: 0,
            debounced: true,
          });
        }
        hasPendingRevalidation.current = true;
        debouncedRevalidate("auto");
      }

      lastMessageCount.current = currentCount;
    });

    // Initialize message count
    const initialState = store.getState();
    lastMessageCount.current =
      initialState.session.currentSession?.messages?.length || 0;

    return unsubscribe;
  }, [autoRevalidate, router, store, debouncedRevalidate, sessionTelemetry]);

  // Derive isRevalidating from router state
  const isRevalidating = useMemo(
    () => router?.state.revalidation === "loading",
    [router?.state.revalidation],
  );

  return {
    revalidateMessages,
    isRevalidating: isRevalidating ?? false,
  };
}
