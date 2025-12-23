/**
 * useBatchApprovals Hook
 *
 * Hook for batch approving or rejecting multiple agent HITL requests.
 *
 * Features:
 * - Batch approve multiple requests
 * - Batch reject multiple requests
 * - Loading states for each operation
 * - Error handling
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { useState, useCallback } from "react";
import { getAuthToken } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

export interface BatchApprovalResult {
  request_id: string;
  success: boolean;
  message: string;
  status?: string;
  error_code?: string;
}

export interface BatchApprovalResponse {
  results: BatchApprovalResult[];
  succeeded: number;
  failed: number;
}

export interface UseBatchApprovalsReturn {
  /** Batch approve multiple requests */
  batchApprove: (
    requestIds: string[],
    reason?: string,
  ) => Promise<BatchApprovalResponse | null>;
  /** Batch reject multiple requests */
  batchReject: (
    requestIds: string[],
    reason?: string,
  ) => Promise<BatchApprovalResponse | null>;
  /** Whether approval request is in progress */
  isApproving: boolean;
  /** Whether rejection request is in progress */
  isRejecting: boolean;
  /** Error message if last operation failed */
  error: string | null;
}

// =============================================================================
// Constants
// =============================================================================

const API_BASE =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.host}/api/v1`
    : "/api/v1";

// =============================================================================
// Hook
// =============================================================================

export function useBatchApprovals(): UseBatchApprovalsReturn {
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Make a batch operation request
   */
  const makeBatchRequest = useCallback(
    async (
      endpoint: string,
      requestIds: string[],
      reason?: string,
      setLoading: (v: boolean) => void = () => {},
    ): Promise<BatchApprovalResponse | null> => {
      setLoading(true);
      setError(null);

      try {
        const token = getAuthToken();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            request_ids: requestIds,
            reason: reason,
          }),
        });

        if (!response.ok) {
          const errorMessage = `Batch operation failed: ${response.status} ${response.statusText}`;
          setError(errorMessage);
          return null;
        }

        const data = await response.json();
        return data as BatchApprovalResponse;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Batch operation failed";
        setError(errorMessage);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  /**
   * Batch approve multiple requests
   */
  const batchApprove = useCallback(
    async (
      requestIds: string[],
      reason?: string,
    ): Promise<BatchApprovalResponse | null> => {
      return makeBatchRequest(
        "/agents/requests/batch/approve",
        requestIds,
        reason,
        setIsApproving,
      );
    },
    [makeBatchRequest],
  );

  /**
   * Batch reject multiple requests
   */
  const batchReject = useCallback(
    async (
      requestIds: string[],
      reason?: string,
    ): Promise<BatchApprovalResponse | null> => {
      return makeBatchRequest(
        "/agents/requests/batch/reject",
        requestIds,
        reason,
        setIsRejecting,
      );
    },
    [makeBatchRequest],
  );

  return {
    batchApprove,
    batchReject,
    isApproving,
    isRejecting,
    error,
  };
}
