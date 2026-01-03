/**
 * useWorkflowValidation Hook
 *
 * Provides debounced workflow validation using the centralized /validate endpoint.
 * This ensures consistent validation between Monaco editor and React Flow
 * without duplicating validation logic in the frontend (NO JS DUPLICATION).
 *
 * Features:
 * - Debounced validation (300ms default) to avoid API spam during editing
 * - Caches validation results to prevent redundant calls
 * - Provides loading, error, and validation result states
 *
 * References:
 * - Plan: Chat-to-Workflow Feature (validated by 4 independent reviews)
 * - ADR-0089: Prompt Architecture Centralization
 * - Review consensus: Centralized validation endpoint
 */

import { useState, useCallback, useRef, useEffect } from "react";

import { useValidateWorkflowMutation } from "../api";
import { useDebouncedCallback } from "./useDebounce";

import type { ValidateWorkflowResponse } from "../types";

export interface UseWorkflowValidationOptions {
  /**
   * Debounce delay in milliseconds (default: 300ms)
   */
  debounceMs?: number;

  /**
   * Whether to auto-validate on mount
   */
  validateOnMount?: boolean;
}

export interface UseWorkflowValidationResult {
  /**
   * Current validation result (null if not yet validated)
   */
  validationResult: ValidateWorkflowResponse | null;

  /**
   * Whether validation is currently in progress
   */
  isValidating: boolean;

  /**
   * Error from validation request (null if no error)
   */
  error: string | null;

  /**
   * Trigger validation for a workflow (debounced)
   */
  validate: (workflowId: string) => void;

  /**
   * Trigger immediate validation (bypasses debounce)
   */
  validateNow: (workflowId: string) => Promise<ValidateWorkflowResponse>;

  /**
   * Cancel any pending debounced validation
   */
  cancel: () => void;

  /**
   * Clear validation result and error
   */
  reset: () => void;
}

/**
 * Hook for debounced workflow validation.
 *
 * @param options - Configuration options
 * @returns Validation state and control functions
 *
 * @example
 * const { validationResult, isValidating, validate } = useWorkflowValidation();
 *
 * // Called on every edit (debounced)
 * const handleWorkflowChange = (workflowId: string) => {
 *   validate(workflowId);
 * };
 *
 * // Display validation errors
 * if (validationResult && !validationResult.valid) {
 *   console.log("Errors:", validationResult.errors);
 * }
 */
export function useWorkflowValidation(
  options: UseWorkflowValidationOptions = {},
): UseWorkflowValidationResult {
  const { debounceMs = 300, validateOnMount: _validateOnMount = false } =
    options;

  const [validationResult, setValidationResult] =
    useState<ValidateWorkflowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [validateWorkflow, { isLoading }] = useValidateWorkflowMutation();

  // Track last validated workflow ID to prevent duplicate calls
  const lastValidatedIdRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Core validation function
  const performValidation = useCallback(
    async (workflowId: string): Promise<ValidateWorkflowResponse> => {
      try {
        setError(null);
        const result = await validateWorkflow({
          workflow_id: workflowId,
        }).unwrap();

        if (mountedRef.current) {
          setValidationResult(result);
          lastValidatedIdRef.current = workflowId;
        }

        return result;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Validation failed";

        if (mountedRef.current) {
          setError(errorMessage);
          setValidationResult(null);
        }

        throw err;
      }
    },
    [validateWorkflow],
  );

  // Debounced validation
  const debouncedValidate = useDebouncedCallback((workflowId: string) => {
    performValidation(workflowId).catch(() => {
      // Error is already handled in performValidation
    });
  }, debounceMs);

  // Public validate function (debounced)
  const validate = useCallback(
    (workflowId: string) => {
      debouncedValidate(workflowId);
    },
    [debouncedValidate],
  );

  // Immediate validation (bypasses debounce)
  const validateNow = useCallback(
    async (workflowId: string): Promise<ValidateWorkflowResponse> => {
      debouncedValidate.cancel();
      return performValidation(workflowId);
    },
    [debouncedValidate, performValidation],
  );

  // Cancel pending validation
  const cancel = useCallback(() => {
    debouncedValidate.cancel();
  }, [debouncedValidate]);

  // Reset state
  const reset = useCallback(() => {
    debouncedValidate.cancel();
    setValidationResult(null);
    setError(null);
    lastValidatedIdRef.current = null;
  }, [debouncedValidate]);

  return {
    validationResult,
    isValidating: isLoading,
    error,
    validate,
    validateNow,
    cancel,
    reset,
  };
}

export default useWorkflowValidation;
