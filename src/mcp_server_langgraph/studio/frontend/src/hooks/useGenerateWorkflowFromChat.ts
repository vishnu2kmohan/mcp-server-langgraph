/**
 * useGenerateWorkflowFromChat Hook
 *
 * Provides functionality to generate workflows from chat session history.
 * This hook powers the "Generate workflow from this chat" button in the Chat UI.
 *
 * Features:
 * - Calls POST /api/v1/workflows/from-chat endpoint
 * - Handles loading, success, and error states
 * - Provides navigation to the generated workflow editor
 * - Includes prompt metadata for telemetry linkage
 *
 * References:
 * - Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
 * - ADR-0089: Prompt Architecture Centralization
 * - Review consensus: Centralized validation endpoint
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router";

import { useGenerateWorkflowFromChatMutation } from "../api";

import type {
  GenerateWorkflowFromChatRequest,
  GenerateWorkflowFromChatResponse,
} from "../types";

export interface UseGenerateWorkflowFromChatOptions {
  /**
   * Whether to navigate to the workflow editor after generation
   */
  navigateOnSuccess?: boolean;

  /**
   * Callback after successful generation
   */
  onSuccess?: (response: GenerateWorkflowFromChatResponse) => void;

  /**
   * Callback on error
   */
  onError?: (error: Error) => void;
}

export interface UseGenerateWorkflowFromChatResult {
  /**
   * Generated workflow response (null if not yet generated)
   */
  result: GenerateWorkflowFromChatResponse | null;

  /**
   * Whether generation is in progress
   */
  isGenerating: boolean;

  /**
   * Error message (null if no error)
   */
  error: string | null;

  /**
   * Generate workflow from a session
   */
  generate: (
    request: GenerateWorkflowFromChatRequest,
  ) => Promise<GenerateWorkflowFromChatResponse>;

  /**
   * Reset state
   */
  reset: () => void;
}

/**
 * Hook for generating workflows from chat session history.
 *
 * @param options - Configuration options
 * @returns Generation state and control functions
 *
 * @example
 * const { generate, isGenerating, result, error } = useGenerateWorkflowFromChat({
 *   navigateOnSuccess: true,
 * });
 *
 * // Called when user clicks "Generate workflow from this chat"
 * const handleGenerateClick = async () => {
 *   await generate({
 *     session_id: currentSessionId,
 *     refinement_mode: "auto",
 *   });
 * };
 */
export function useGenerateWorkflowFromChat(
  options: UseGenerateWorkflowFromChatOptions = {},
): UseGenerateWorkflowFromChatResult {
  const { navigateOnSuccess = true, onSuccess, onError } = options;

  const [result, setResult] = useState<GenerateWorkflowFromChatResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();
  const [generateWorkflow, { isLoading }] =
    useGenerateWorkflowFromChatMutation();

  const generate = useCallback(
    async (
      request: GenerateWorkflowFromChatRequest,
    ): Promise<GenerateWorkflowFromChatResponse> => {
      try {
        setError(null);
        const response = await generateWorkflow(request).unwrap();

        setResult(response);

        // Navigate to workflow editor if requested
        if (navigateOnSuccess && response.workflow?.id) {
          navigate(`/workflows/${response.workflow.id}/edit`);
        }

        // Call success callback
        onSuccess?.(response);

        return response;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to generate workflow";

        setError(errorMessage);
        setResult(null);

        // Call error callback
        if (err instanceof Error) {
          onError?.(err);
        } else {
          onError?.(new Error(errorMessage));
        }

        throw err;
      }
    },
    [generateWorkflow, navigateOnSuccess, navigate, onSuccess, onError],
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    result,
    isGenerating: isLoading,
    error,
    generate,
    reset,
  };
}

export default useGenerateWorkflowFromChat;
