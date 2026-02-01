/**
 * useFormValidation Hook
 *
 * Manages form validation state with configurable validation timing.
 * Provides error management, touched state tracking, and helper functions
 * for building accessible forms.
 *
 * @example
 * const { errors, setError, clearError, getFieldProps, isValid } = useFormValidation({
 *   mode: 'onBlur',
 *   revalidateOnChange: true,
 * });
 *
 * <FormField
 *   label="Email"
 *   name="email"
 *   {...getFieldProps('email')}
 * >
 *   <Input
 *     onBlur={(e) => {
 *       setTouched('email');
 *       if (!isValidEmail(e.target.value)) {
 *         setError('email', 'Please enter a valid email');
 *       } else {
 *         clearError('email');
 *       }
 *     }}
 *   />
 * </FormField>
 */

import { useState, useCallback, useMemo } from "react";

// =============================================================================
// Types
// =============================================================================

export type ValidationMode = "onBlur" | "onChange" | "onSubmit";

export interface UseFormValidationOptions {
  /** When to validate fields. Default: 'onBlur' */
  mode?: ValidationMode;
  /** Re-validate on change after first error. Default: true */
  revalidateOnChange?: boolean;
}

export interface FieldProps {
  /** Error message to display (only for touched fields) */
  error?: string;
  /** ARIA invalid attribute for accessibility */
  "aria-invalid"?: boolean;
}

export interface UseFormValidationReturn {
  /** Current validation errors by field name */
  errors: Record<string, string>;
  /** Fields that have been interacted with */
  touched: Record<string, boolean>;
  /** Whether the form is currently valid (no errors) */
  isValid: boolean;
  /** Whether any field has been touched */
  isDirty: boolean;
  /** Number of fields with errors */
  errorCount: number;
  /** Current validation mode */
  mode: ValidationMode;
  /** Whether to re-validate on change after error */
  revalidateOnChange: boolean;

  /** Set error for a single field */
  setError: (field: string, message: string) => void;
  /** Set errors for multiple fields */
  setErrors: (errors: Record<string, string>) => void;
  /** Clear error for a single field */
  clearError: (field: string) => void;
  /** Clear all errors */
  clearAllErrors: () => void;

  /** Mark a field as touched */
  setTouched: (field: string) => void;

  /** Check if a field has an error */
  hasError: (field: string) => boolean;
  /** Get error message for a field */
  getError: (field: string) => string | undefined;
  /** Get field props for FormField component (respects touched state) */
  getFieldProps: (field: string) => FieldProps;

  /** Reset all state to initial values */
  reset: () => void;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Form validation state management hook.
 *
 * @param options - Validation configuration options
 * @returns Form validation state and helpers
 */
export function useFormValidation(
  options: UseFormValidationOptions = {},
): UseFormValidationReturn {
  const { mode = "onBlur", revalidateOnChange = true } = options;

  // State
  const [errors, setErrorsState] = useState<Record<string, string>>({});
  const [touched, setTouchedState] = useState<Record<string, boolean>>({});

  // Computed values
  const isValid = useMemo(() => Object.keys(errors).length === 0, [errors]);
  const isDirty = useMemo(() => Object.keys(touched).length > 0, [touched]);
  const errorCount = useMemo(() => Object.keys(errors).length, [errors]);

  // Error management
  const setError = useCallback((field: string, message: string) => {
    setErrorsState((prev) => ({ ...prev, [field]: message }));
  }, []);

  const setErrors = useCallback((newErrors: Record<string, string>) => {
    setErrorsState((prev) => ({ ...prev, ...newErrors }));
  }, []);

  const clearError = useCallback((field: string) => {
    setErrorsState((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const clearAllErrors = useCallback(() => {
    setErrorsState({});
  }, []);

  // Touched state management
  const setTouched = useCallback((field: string) => {
    setTouchedState((prev) => ({ ...prev, [field]: true }));
  }, []);

  // Helpers
  const hasError = useCallback((field: string) => field in errors, [errors]);

  const getError = useCallback((field: string) => errors[field], [errors]);

  const getFieldProps = useCallback(
    (field: string): FieldProps => {
      const isTouched = touched[field];
      const error = errors[field];

      // Only show error if field has been touched
      if (isTouched && error) {
        return {
          error,
          "aria-invalid": true,
        };
      }

      return {};
    },
    [errors, touched],
  );

  // Reset
  const reset = useCallback(() => {
    setErrorsState({});
    setTouchedState({});
  }, []);

  return {
    errors,
    touched,
    isValid,
    isDirty,
    errorCount,
    mode,
    revalidateOnChange,

    setError,
    setErrors,
    clearError,
    clearAllErrors,

    setTouched,

    hasError,
    getError,
    getFieldProps,

    reset,
  };
}

export default useFormValidation;
