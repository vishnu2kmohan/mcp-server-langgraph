/**
 * GenerateWorkflowButton Component
 *
 * Button that generates a workflow from the current chat session.
 * Uses the centralized /from-chat endpoint (NO JS DUPLICATION).
 *
 * Features:
 * - Feature-flagged (workflow_from_chat)
 * - Shows loading state during generation
 * - Navigates to workflow editor on success
 * - Displays error state on failure
 *
 * References:
 * - Plan: Chat-to-Workflow Feature
 * - ADR-0089: Prompt Architecture Centralization
 */

import { useCallback } from "react";
import { Workflow, Loader2 } from "lucide-react";
import { useGenerateWorkflowFromChat } from "../hooks/useGenerateWorkflowFromChat";
import { useGetFeatureFlagsQuery } from "../api";
import { cn } from "../utils/cn";

import type { GenerateWorkflowFromChatResponse } from "../types";

import { Button } from "@/components/UI";

export interface GenerateWorkflowButtonProps {
  /** Session ID to generate workflow from */
  sessionId: string;
  /** Callback on successful generation */
  onSuccess?: (response: GenerateWorkflowFromChatResponse) => void;
  /** Callback on generation error */
  onError?: (error: Error) => void;
  /** Additional class name */
  className?: string;
}

/**
 * Button that generates a workflow from the current chat session.
 *
 * @example
 * <GenerateWorkflowButton
 *   sessionId={currentSessionId}
 *   onSuccess={(response) => console.log("Generated:", response.workflow.id)}
 * />
 */
export function GenerateWorkflowButton({
  sessionId,
  onSuccess,
  onError,
  className,
}: GenerateWorkflowButtonProps) {
  // Check if feature is enabled
  const { data: featureFlags, isLoading: isFlagsLoading } =
    useGetFeatureFlagsQuery();

  // Use the generation hook
  const { generate, isGenerating, error } = useGenerateWorkflowFromChat({
    navigateOnSuccess: true,
    onSuccess,
    onError,
  });

  // Handle button click
  const handleClick = useCallback(async () => {
    if (!sessionId || isGenerating) return;

    try {
      await generate({ session_id: sessionId });
    } catch {
      // Error is handled by the hook and onError callback
    }
  }, [sessionId, isGenerating, generate]);

  // Don't render if feature is disabled or still loading flags
  if (isFlagsLoading) {
    return null;
  }

  if (!featureFlags?.workflow_from_chat) {
    return null;
  }

  const isDisabled = !sessionId || isGenerating;

  return (
    <Button
      data-testid="generate-workflow-button"
      data-error={error ? "true" : "false"}
      type="button"
      onClick={handleClick}
      disabled={isDisabled}
      className={cn(
        "p-1.5 rounded-md",
        "text-neutral-10",
        "hover:bg-neutral-2",
        "transition-colors",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        error && "text-error-9 dark:text-error-7",
        className,
      )}
      aria-label="Generate workflow from this chat"
      title="Generate workflow from this chat"
    >
      {isGenerating ? (
        <Loader2 size={14} className="animate-spin" />
      ) : (
        <Workflow size={14} />
      )}
    </Button>
  );
}

export default GenerateWorkflowButton;
