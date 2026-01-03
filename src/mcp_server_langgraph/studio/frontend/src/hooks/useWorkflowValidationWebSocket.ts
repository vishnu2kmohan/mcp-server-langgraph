/**
 * useWorkflowValidationWebSocket Hook
 *
 * WebSocket hook for real-time workflow validation events.
 * Listens to orchestrator_status for workflow_validation_* events
 * broadcasted by the backend during workflow editing.
 *
 * Event Types:
 * - workflow_validation_started: Validation has begun
 * - workflow_validation_passed: Workflow is valid (may have warnings)
 * - workflow_validation_failed: Workflow has errors
 * - workflow_draft_saved: Draft was saved
 * - workflow_published: Workflow was published
 *
 * Based on backend: websocket/handlers/orchestrator_status.py
 */

import { useState, useCallback, useRef, useMemo } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logout, selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";
import { buildWebSocketUrl, WS_ENDPOINTS } from "../utils/websocket";

// =============================================================================
// Types
// =============================================================================

export type ValidationState = "idle" | "validating" | "valid" | "invalid";

/**
 * Workflow validation event from WebSocket
 */
export interface WorkflowValidationEvent {
  type:
    | "workflow_validation_started"
    | "workflow_validation_passed"
    | "workflow_validation_failed"
    | "workflow_draft_saved"
    | "workflow_published";
  workflow_id: string;
  user_id?: string;
  errors?: string[];
  warnings?: string[];
  timestamp?: string;
}

/**
 * Options for useWorkflowValidationWebSocket hook
 */
export interface UseWorkflowValidationWebSocketOptions {
  /** Workflow ID to filter events (optional - receives all if not set) */
  workflowId?: string;
  /** Callback when validation starts */
  onValidationStarted?: (workflowId: string) => void;
  /** Callback when validation passes */
  onValidationPassed?: (warnings: string[]) => void;
  /** Callback when validation fails */
  onValidationFailed?: (errors: string[], warnings: string[]) => void;
  /** Callback when draft is saved */
  onDraftSaved?: (workflowId: string) => void;
  /** Callback when workflow is published */
  onPublished?: (workflowId: string) => void;
}

/**
 * Return type for useWorkflowValidationWebSocket hook
 */
export interface UseWorkflowValidationWebSocketReturn {
  /** Current connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** Whether connected to the WebSocket */
  isConnected: boolean;
  /** Current validation state */
  validationState: ValidationState | null;
  /** Current validation errors */
  errors: string[];
  /** Current validation warnings */
  warnings: string[];
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Reconnect to WebSocket */
  reconnect: () => void;
  /** Reset validation state */
  resetState: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useWorkflowValidationWebSocket(
  options: UseWorkflowValidationWebSocketOptions = {},
): UseWorkflowValidationWebSocketReturn {
  const {
    workflowId,
    onValidationStarted,
    onValidationPassed,
    onValidationFailed,
    onDraftSaved,
    onPublished,
  } = options;

  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();

  // Get auth state and token for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL - only generate URL when authenticated
  const url = useMemo(
    () =>
      isAuthenticated
        ? buildWebSocketUrl(WS_ENDPOINTS.ORCHESTRATOR_STATUS, {}, true)
        : "",
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [authToken, isAuthenticated],
  );

  // State
  const [validationState, setValidationState] =
    useState<ValidationState | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);

  // Refs for callbacks to avoid stale closures
  const callbacksRef = useRef({
    onValidationStarted,
    onValidationPassed,
    onValidationFailed,
    onDraftSaved,
    onPublished,
  });
  callbacksRef.current = {
    onValidationStarted,
    onValidationPassed,
    onValidationFailed,
    onDraftSaved,
    onPublished,
  };

  const workflowIdRef = useRef(workflowId);
  workflowIdRef.current = workflowId;

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const event = data as WorkflowValidationEvent;

    // Only process workflow validation events
    if (!event.type?.startsWith("workflow_")) {
      return;
    }

    // Filter by workflowId if specified
    if (workflowIdRef.current && event.workflow_id !== workflowIdRef.current) {
      return;
    }

    switch (event.type) {
      case "workflow_validation_started":
        setValidationState("validating");
        setErrors([]);
        setWarnings([]);
        callbacksRef.current.onValidationStarted?.(event.workflow_id);
        break;

      case "workflow_validation_passed":
        setValidationState("valid");
        setErrors([]);
        setWarnings(event.warnings ?? []);
        callbacksRef.current.onValidationPassed?.(event.warnings ?? []);
        break;

      case "workflow_validation_failed":
        setValidationState("invalid");
        setErrors(event.errors ?? []);
        setWarnings(event.warnings ?? []);
        callbacksRef.current.onValidationFailed?.(
          event.errors ?? [],
          event.warnings ?? [],
        );
        break;

      case "workflow_draft_saved":
        callbacksRef.current.onDraftSaved?.(event.workflow_id);
        break;

      case "workflow_published":
        callbacksRef.current.onPublished?.(event.workflow_id);
        break;
    }
  }, []);

  // Use the realtime sync hook for WebSocket management
  const { status, disconnect, reconnect } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    exponentialBackoff: true,
    reconnectInterval: 1000,
    maxDelayMs: 30000,
    maxReconnectAttempts: 10,
    onTokenExpired: () => dispatch(logout()),
  });

  // Derived state
  const isConnected = status === "connected";

  // Reset validation state
  const resetState = useCallback(() => {
    setValidationState(null);
    setErrors([]);
    setWarnings([]);
  }, []);

  return {
    status,
    isConnected,
    validationState,
    errors,
    warnings,
    disconnect,
    reconnect,
    resetState,
  };
}

export default useWorkflowValidationWebSocket;
