/**
 * useSessionSync Hook
 *
 * Synchronizes React Router loader data to Redux session state.
 *
 * Purpose:
 * - Studio uses React Router loaders (fetch-before-render)
 * - Legacy components (sendMessage) expect currentSession in Redux
 * - This hook bridges the gap by syncing loader data to Redux
 *
 * Usage:
 * ```tsx
 * function ChatPage() {
 *   const loaderData = useRouteLoaderData("chat-session") as ChatLoaderData;
 *   useSessionSync(loaderData);
 *   // Now currentSession is available in Redux
 * }
 * ```
 */
import { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  setCurrentSession,
  selectHasPendingMutation,
} from "../store/slices/sessionSlice";
import type { AppDispatch, RootState } from "../store";
import type { ChatLoaderData } from "../router/loaders";
import { useSessionTelemetry } from "../contexts/TelemetryContext";
import {
  isApiSession,
  transformApiSessionToClient,
} from "../utils/apiTransforms";
import { devLogger } from "../utils/devLogger";

const logger = devLogger.withPrefix("[useSessionSync]");

// =============================================================================
// Hook
// =============================================================================

/**
 * Sync React Router loader data to Redux session state.
 *
 * Important: This hook only syncs when loaderData is defined.
 * It does NOT clear sessions when loaderData is undefined, to support
 * components that work in both studio (with loaders) and legacy (without loaders) contexts.
 *
 * Race condition guard: If there are pending mutations (optimistic updates),
 * the hook skips syncing to prevent stale loader data from overwriting
 * the optimistic updates.
 *
 * For studio routes:
 * - When navigating TO a session: loaderData has session, sync to Redux
 * - When navigating AWAY: component unmounts, no action needed
 *
 * For legacy routes:
 * - loaderData is always undefined, hook does nothing
 * - Session management continues via Redux thunks
 *
 * @param loaderData - ChatLoaderData from useRouteLoaderData, or undefined
 */
export function useSessionSync(loaderData: ChatLoaderData | undefined): void {
  const dispatch = useDispatch<AppDispatch>();
  const hasPendingMutation = useSelector((state: RootState) =>
    selectHasPendingMutation(state),
  );
  const sessionTelemetry = useSessionTelemetry();
  const syncStartTime = useRef<number>(0);

  useEffect(() => {
    syncStartTime.current = Date.now();

    // Only sync when we have loader data (studio context)
    // If undefined (legacy context or no data router), do nothing
    if (!loaderData) {
      return;
    }

    // Race condition guard: Skip sync if there are pending mutations
    // This prevents stale loader data from overwriting optimistic updates
    if (hasPendingMutation) {
      sessionTelemetry.trackSync({
        sessionId: loaderData.sessionId || "unknown",
        messageCount: loaderData.messages?.length || 0,
        durationMs: 0,
        skipped: true,
        skipReason: "pending_mutation",
      });
      return;
    }

    // No sessionId means index route (/studio/chat without session param)
    if (!loaderData.sessionId) {
      dispatch(setCurrentSession(null));
      sessionTelemetry.trackSync({
        sessionId: "null",
        messageCount: 0,
        durationMs: Date.now() - syncStartTime.current,
        skipped: false,
      });
      return;
    }

    // If we have a session, validate and transform to Redux
    if (loaderData.session && isApiSession(loaderData.session)) {
      const clientSession = transformApiSessionToClient(
        loaderData.session,
        loaderData.messages,
      );
      dispatch(setCurrentSession(clientSession));

      sessionTelemetry.trackSync({
        sessionId: loaderData.sessionId,
        messageCount: loaderData.messages?.length || 0,
        durationMs: Date.now() - syncStartTime.current,
        skipped: false,
      });
    } else if (loaderData.session) {
      // Session data exists but failed validation - log warning
      logger.warn(
        "Received invalid session data, skipping sync",
        loaderData.session,
      );
      dispatch(setCurrentSession(null));
      sessionTelemetry.trackSync({
        sessionId: loaderData.sessionId,
        messageCount: 0,
        durationMs: Date.now() - syncStartTime.current,
        skipped: true,
        skipReason: "invalid_session_data",
      });
    } else {
      // Session ID present but no session data (error case)
      dispatch(setCurrentSession(null));
      sessionTelemetry.trackSync({
        sessionId: loaderData.sessionId,
        messageCount: 0,
        durationMs: Date.now() - syncStartTime.current,
        skipped: false,
      });
    }
  }, [dispatch, loaderData, hasPendingMutation, sessionTelemetry]);
}
