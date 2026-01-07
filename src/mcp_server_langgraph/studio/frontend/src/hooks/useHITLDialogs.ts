/**
 * useHITLDialogs Hook
 *
 * Encapsulates all Human-in-the-Loop (HITL) dialog state management:
 * - Approval and clarification dialog state
 * - Loading states (approving, rejecting, submitting)
 * - Dismissed request IDs tracking (prevents auto-reopening)
 * - WebSocket integration for real-time requests
 * - Auto-show dialogs when pending requests arrive
 * - Handlers for approve, reject, respond, close
 *
 * Extracted from StudioShellLayout to reduce component complexity.
 */
import { useState, useCallback, useEffect } from "react";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { useAgentRequestWebSocket } from "./useAgentRequestWebSocket";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { updateAgentStatus } from "../store/slices/backgroundAgentSlice";
import { selectUsername } from "../store/slices/personaSlice";
// RTK Query mutations for Agent HITL requests
import {
  useApproveAgentRequestMutation,
  useRejectAgentRequestMutation,
  useRespondToAgentRequestMutation,
} from "../api";
// Use consolidated HITL types (camelCase per ADR-0091)
import {
  type ApprovalRequiredPayloadCamelCase,
  type ClarificationRequiredPayloadCamelCase,
  type ClarificationAPIResponse,
} from "../types/hitl";

/**
 * Response type for clarification dialog (API format)
 * Re-exported from types/hitl.ts for backwards compatibility
 */
export type ClarificationResponse = ClarificationAPIResponse;

/**
 * Return type for the useHITLDialogs hook
 *
 * All payload types use camelCase per ADR-0091 API Response Transformation Strategy.
 */
export interface UseHITLDialogsReturn {
  // Feature flag state
  enabled: boolean;

  // Dialog visibility state
  showApprovalDialog: boolean;
  showClarificationDialog: boolean;

  // Active dialog content (camelCase per ADR-0091)
  activeApproval: ApprovalRequiredPayloadCamelCase | null;
  activeClarification: ClarificationRequiredPayloadCamelCase | null;

  // Loading states
  isApproving: boolean;
  isRejecting: boolean;
  isClarificationSubmitting: boolean;

  // Pending requests from WebSocket (camelCase per ADR-0091)
  pendingApprovals: ApprovalRequiredPayloadCamelCase[];
  pendingClarifications: ClarificationRequiredPayloadCamelCase[];

  // Dialog control functions
  openApprovalDialog: (approval: ApprovalRequiredPayloadCamelCase) => void;
  closeApprovalDialog: () => void;
  openClarificationDialog: (
    clarification: ClarificationRequiredPayloadCamelCase,
  ) => void;
  closeClarificationDialog: () => void;

  // Action handlers
  handleApprove: (
    requestId: string,
    reason?: string,
    modifications?: Record<string, unknown>,
  ) => Promise<void>;
  handleReject: (requestId: string, reason?: string) => Promise<void>;
  handleClarificationRespond: (
    response: ClarificationResponse,
  ) => Promise<void>;

  // Dismissed tracking
  isDismissed: (requestId: string) => boolean;
}

/**
 * Hook for managing HITL dialog state
 *
 * Handles:
 * - Feature flag awareness (agent_hitl)
 * - WebSocket connection for real-time requests
 * - Auto-showing dialogs when pending requests arrive
 * - API calls for approve, reject, respond
 * - Redux dispatch for agent status updates
 * - Dismissed request tracking to prevent auto-reopening
 *
 * @example
 * ```tsx
 * const {
 *   showApprovalDialog,
 *   activeApproval,
 *   handleApprove,
 *   handleReject,
 *   closeApprovalDialog,
 * } = useHITLDialogs();
 *
 * // In JSX:
 * {showApprovalDialog && activeApproval && (
 *   <AgentApprovalDialog
 *     request={activeApproval}
 *     onApprove={handleApprove}
 *     onReject={handleReject}
 *     onClose={closeApprovalDialog}
 *   />
 * )}
 * ```
 */
export function useHITLDialogs(): UseHITLDialogsReturn {
  const dispatch = useAppDispatch();
  const username = useAppSelector(selectUsername);

  // Feature flag for HITL
  const enabled = useFeatureFlag("agent_hitl");

  // RTK Query mutations for Agent HITL requests
  const [approveRequest, { isLoading: isApproving }] =
    useApproveAgentRequestMutation();
  const [rejectRequest, { isLoading: isRejecting }] =
    useRejectAgentRequestMutation();
  const [respondRequest, { isLoading: isClarificationSubmitting }] =
    useRespondToAgentRequestMutation();

  // Dialog state (camelCase types per ADR-0091)
  const [activeApproval, setActiveApproval] =
    useState<ApprovalRequiredPayloadCamelCase | null>(null);
  const [activeClarification, setActiveClarification] =
    useState<ClarificationRequiredPayloadCamelCase | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [showClarificationDialog, setShowClarificationDialog] = useState(false);

  // Track dismissed request IDs to prevent auto-reopening after user closes dialog
  const [dismissedRequestIds, setDismissedRequestIds] = useState<Set<string>>(
    new Set(),
  );

  // Handle approval required messages from WebSocket (camelCase per ADR-0091)
  const handleApprovalRequired = useCallback(
    (payload: ApprovalRequiredPayloadCamelCase) => {
      setActiveApproval(payload);
      setShowApprovalDialog(true);

      // Update agent status in Redux
      dispatch(
        updateAgentStatus({
          id: payload.taskId,
          status: "awaiting_approval",
        }),
      );
    },
    [dispatch],
  );

  // Handle clarification required messages from WebSocket (camelCase per ADR-0091)
  const handleClarificationRequired = useCallback(
    (payload: ClarificationRequiredPayloadCamelCase) => {
      setActiveClarification(payload);
      setShowClarificationDialog(true);

      // Update agent status in Redux
      dispatch(
        updateAgentStatus({
          id: payload.taskId,
          status: "awaiting_clarification",
        }),
      );
    },
    [dispatch],
  );

  // Get HITL agent request WebSocket connection
  const { pendingApprovals, pendingClarifications } = useAgentRequestWebSocket({
    enabled,
    onApprovalRequired: handleApprovalRequired,
    onClarificationRequired: handleClarificationRequired,
  });

  // Auto-show dialogs when pending requests arrive
  useEffect(() => {
    if (!enabled) return;

    // Prioritize approvals over clarifications
    // Filter out dismissed requests so they don't auto-reopen (camelCase per ADR-0091)
    const undismissedApprovals = pendingApprovals.filter(
      (a) => !dismissedRequestIds.has(a.requestId),
    );
    const undismissedClarifications = pendingClarifications.filter(
      (c) => !dismissedRequestIds.has(c.requestId),
    );

    if (
      undismissedApprovals.length > 0 &&
      !showApprovalDialog &&
      !activeApproval
    ) {
      const firstApproval = undismissedApprovals[0];
      if (firstApproval) {
        setActiveApproval(firstApproval);
        setShowApprovalDialog(true);
      }
    } else if (
      undismissedClarifications.length > 0 &&
      !showClarificationDialog &&
      !activeClarification &&
      !showApprovalDialog
    ) {
      const firstClarification = undismissedClarifications[0];
      if (firstClarification) {
        setActiveClarification(firstClarification);
        setShowClarificationDialog(true);
      }
    }
  }, [
    enabled,
    pendingApprovals,
    pendingClarifications,
    showApprovalDialog,
    showClarificationDialog,
    activeApproval,
    activeClarification,
    dismissedRequestIds,
  ]);

  // Open approval dialog with specific request (camelCase per ADR-0091)
  const openApprovalDialog = useCallback(
    (approval: ApprovalRequiredPayloadCamelCase) => {
      setActiveApproval(approval);
      setShowApprovalDialog(true);
    },
    [],
  );

  // Close approval dialog and track as dismissed (camelCase per ADR-0091)
  const closeApprovalDialog = useCallback(() => {
    if (activeApproval) {
      setDismissedRequestIds((prev) =>
        new Set(prev).add(activeApproval.requestId),
      );
    }
    setShowApprovalDialog(false);
    setActiveApproval(null);
  }, [activeApproval]);

  // Open clarification dialog with specific request (camelCase per ADR-0091)
  const openClarificationDialog = useCallback(
    (clarification: ClarificationRequiredPayloadCamelCase) => {
      setActiveClarification(clarification);
      setShowClarificationDialog(true);
    },
    [],
  );

  // Close clarification dialog and track as dismissed (camelCase per ADR-0091)
  const closeClarificationDialog = useCallback(() => {
    if (activeClarification) {
      setDismissedRequestIds((prev) =>
        new Set(prev).add(activeClarification.requestId),
      );
    }
    setShowClarificationDialog(false);
    setActiveClarification(null);
  }, [activeClarification]);

  // Handle approval action using RTK Query mutation (camelCase per ADR-0091)
  const handleApprove = useCallback(
    async (
      requestId: string,
      reason?: string,
      modifications?: Record<string, unknown>,
    ) => {
      if (!activeApproval) return;

      try {
        await approveRequest({
          requestId,
          approved_by: username || "unknown",
          reason,
          modifications,
        }).unwrap();

        // Success: Update agent status back to running
        dispatch(
          updateAgentStatus({
            id: activeApproval.taskId,
            status: "running",
          }),
        );
        setShowApprovalDialog(false);
        setActiveApproval(null);
      } catch {
        // On error, keep dialog open for retry (RTK Query handles the error state)
      }
    },
    [activeApproval, username, dispatch, approveRequest],
  );

  // Handle rejection action using RTK Query mutation (camelCase per ADR-0091)
  const handleReject = useCallback(
    async (requestId: string, reason?: string) => {
      if (!activeApproval) return;

      try {
        await rejectRequest({
          requestId,
          rejected_by: username || "unknown",
          reason,
        }).unwrap();

        // Success: Update agent status to failed
        dispatch(
          updateAgentStatus({
            id: activeApproval.taskId,
            status: "failed",
            error: reason || "Rejected by user",
          }),
        );
        setShowApprovalDialog(false);
        setActiveApproval(null);
      } catch {
        // On error, keep dialog open for retry (RTK Query handles the error state)
      }
    },
    [activeApproval, username, dispatch, rejectRequest],
  );

  // Handle clarification response using RTK Query mutation (camelCase per ADR-0091)
  const handleClarificationRespond = useCallback(
    async (response: ClarificationResponse) => {
      if (!activeClarification) return;

      try {
        await respondRequest({
          request_id: response.request_id,
          responded_by: response.responded_by,
          response_type: response.response_type,
          value: response.value,
          selected_option_id: response.selected_option_id,
          confirmed: response.confirmed,
        }).unwrap();

        // Success: Update agent status back to running
        dispatch(
          updateAgentStatus({
            id: activeClarification.taskId,
            status: "running",
          }),
        );
        setShowClarificationDialog(false);
        setActiveClarification(null);
      } catch {
        // On error, keep dialog open for retry (RTK Query handles the error state)
      }
    },
    [activeClarification, dispatch, respondRequest],
  );

  // Check if a request has been dismissed
  const isDismissed = useCallback(
    (requestId: string) => dismissedRequestIds.has(requestId),
    [dismissedRequestIds],
  );

  return {
    enabled,
    showApprovalDialog,
    showClarificationDialog,
    activeApproval,
    activeClarification,
    isApproving,
    isRejecting,
    isClarificationSubmitting,
    pendingApprovals,
    pendingClarifications,
    openApprovalDialog,
    closeApprovalDialog,
    openClarificationDialog,
    closeClarificationDialog,
    handleApprove,
    handleReject,
    handleClarificationRespond,
    isDismissed,
  };
}

export default useHITLDialogs;
