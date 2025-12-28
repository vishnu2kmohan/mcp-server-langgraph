/**
 * useWorkflowAutoName Hook
 *
 * Automatically generates and applies AI-powered workflow titles
 * based on workflow context (description, originating session, etc.).
 *
 * Features:
 * - Triggers for workflows with default names ("New Workflow", "Untitled")
 * - Uses workflow description for context when available
 * - Links to originating session for chat-initiated workflows
 * - Only triggers once per workflow to avoid repeated renames
 * - Respects user's custom workflow names
 *
 * Related to: useSessionAutoName (similar pattern for sessions)
 */

import { useEffect, useRef, useMemo } from "react";
import { useAppDispatch } from "../store/hooks";
import { renameWorkflow } from "../store/slices/workflowSlice";

// Note: This would be implemented in the API when backend endpoint is available
// For now, we use a placeholder that can be replaced with actual mutation
type GenerateWorkflowTitleMutation = [
  (args: { description?: string; sessionContext?: string }) => void,
  {
    isLoading: boolean;
    isSuccess: boolean;
    data?: { title: string };
    error?: unknown;
  },
];

// Placeholder - replace with actual API mutation when available
const useGenerateWorkflowTitleMutation = (): GenerateWorkflowTitleMutation => {
  return [
    () => {},
    { isLoading: false, isSuccess: false, data: undefined, error: undefined },
  ];
};

/** Default workflow names that trigger auto-naming */
const DEFAULT_WORKFLOW_NAMES = [
  "new workflow",
  "untitled workflow",
  "untitled",
  "new",
];

export interface UseWorkflowAutoNameOptions {
  /** The current workflow ID */
  workflowId?: string;
  /** Current workflow name */
  currentName?: string;
  /** Workflow description for context */
  workflowDescription?: string;
  /** Session ID that initiated this workflow (for chat-to-workflow flow) */
  originatingSessionId?: string;
  /** Context from the originating session (e.g., first message or topic) */
  sessionContext?: string;
  /** Whether auto-naming is enabled */
  enabled?: boolean;
}

export interface UseWorkflowAutoNameResult {
  /** Whether title generation is in progress */
  isGenerating: boolean;
  /** Whether generation was successful */
  isSuccess: boolean;
  /** The generated title (if available) */
  generatedTitle?: string;
  /** Whether the workflow has a default name */
  hasDefaultName: boolean;
  /** Error message if generation failed */
  error?: string;
}

/**
 * Hook for automatic AI-powered workflow naming
 *
 * @example
 * ```tsx
 * const { isGenerating, generatedTitle } = useWorkflowAutoName({
 *   workflowId: workflow.id,
 *   currentName: workflow.name,
 *   workflowDescription: workflow.description,
 *   originatingSessionId: sessionId, // When created from chat
 *   enabled: true,
 * });
 * ```
 */
export function useWorkflowAutoName({
  workflowId,
  currentName,
  workflowDescription,
  originatingSessionId,
  sessionContext,
  enabled = true,
}: UseWorkflowAutoNameOptions): UseWorkflowAutoNameResult {
  const dispatch = useAppDispatch();
  const [generateTitle, { isLoading, isSuccess, data, error }] =
    useGenerateWorkflowTitleMutation();

  // Track if we've already attempted to generate a title for this workflow
  const hasAttemptedRef = useRef<Set<string>>(new Set());

  // Check if the workflow has a default name
  const hasDefaultName = useMemo(() => {
    if (!currentName) return true;
    const normalizedName = currentName.toLowerCase().trim();
    return DEFAULT_WORKFLOW_NAMES.some((defaultName) =>
      normalizedName.includes(defaultName),
    );
  }, [currentName]);

  // Determine if we have context for naming
  const hasNamingContext = useMemo(() => {
    return Boolean(
      workflowDescription || sessionContext || originatingSessionId,
    );
  }, [workflowDescription, sessionContext, originatingSessionId]);

  // Determine if we should trigger generation
  const shouldGenerate = useMemo(() => {
    if (!enabled) return false;
    if (!workflowId) return false;
    if (!hasDefaultName) return false;
    if (!hasNamingContext) return false;
    if (hasAttemptedRef.current.has(workflowId)) return false;
    return true;
  }, [enabled, workflowId, hasDefaultName, hasNamingContext]);

  // Trigger title generation
  useEffect(() => {
    if (!shouldGenerate || !workflowId) return;

    // Mark as attempted immediately to prevent re-triggering
    hasAttemptedRef.current.add(workflowId);

    // Generate title from available context
    generateTitle({
      description: workflowDescription,
      sessionContext: sessionContext,
    });
  }, [
    shouldGenerate,
    workflowId,
    workflowDescription,
    sessionContext,
    generateTitle,
  ]);

  // Handle successful title generation
  useEffect(() => {
    if (isSuccess && data?.title && workflowId) {
      dispatch(renameWorkflow({ workflowId, name: data.title }));
    }
  }, [isSuccess, data, workflowId, dispatch]);

  return {
    isGenerating: isLoading,
    isSuccess,
    generatedTitle: data?.title,
    hasDefaultName,
    error: error ? String(error) : undefined,
  };
}

export default useWorkflowAutoName;
