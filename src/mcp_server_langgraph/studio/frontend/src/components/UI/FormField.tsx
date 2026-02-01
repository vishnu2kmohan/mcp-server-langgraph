/**
 * FormField Component
 *
 * Accessible form field wrapper that provides consistent labeling,
 * error handling, and hint text for form inputs.
 *
 * WCAG 2.2 Compliance:
 * - 3.3.1: Error Identification - Text description + aria-invalid
 * - 3.3.2: Labels or Instructions - Visible labels + placeholder hints
 * - 3.3.3: Error Suggestion - Specific error messages
 * - 1.4.1: Use of Color - Error icon + text, not just red
 *
 * @example
 * // Basic usage
 * <FormField label="Email" name="email">
 *   <Input />
 * </FormField>
 *
 * @example
 * // With hint
 * <FormField label="Password" name="password" hint="Must be 8+ characters">
 *   <Input type="password" />
 * </FormField>
 *
 * @example
 * // With error
 * <FormField label="Email" name="email" error="Invalid email address" required>
 *   <Input />
 * </FormField>
 */

import React, { cloneElement, isValidElement } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/utils/cn";
import { Icon } from "./Icon";

// =============================================================================
// Types
// =============================================================================

export interface FormFieldProps {
  /** Label text for the field */
  label: string;
  /** Field name (used for id, name attributes, and aria associations) */
  name: string;
  /** Error message to display */
  error?: string;
  /** Hint text shown below label (hidden when error present) */
  hint?: string;
  /** Whether the field is required */
  required?: boolean;
  /** The form input element */
  children: React.ReactNode;
  /** Additional CSS classes for the wrapper */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function FormField({
  label,
  name,
  error,
  hint,
  required,
  children,
  className,
}: FormFieldProps) {
  // Respect user's reduced motion preference for WCAG 2.2 AA compliance
  const prefersReducedMotion = useReducedMotion();
  const errorId = `${name}-error`;
  const hintId = `${name}-hint`;

  // Determine aria-describedby value
  const ariaDescribedBy = error ? errorId : hint ? hintId : undefined;

  // Clone the child input and inject accessibility props
  const enhancedChild = isValidElement(children)
    ? cloneElement(children as React.ReactElement<Record<string, unknown>>, {
        id: name,
        name,
        "aria-invalid": error ? "true" : undefined,
        "aria-describedby": ariaDescribedBy,
        "aria-required": required ? "true" : undefined,
        className: cn(
          (children as React.ReactElement<{ className?: string }>).props
            .className,
          error && "border-error-7 focus:ring-error-7",
        ),
      })
    : children;

  return (
    <div className={cn("space-y-1.5", className)}>
      {/* Label */}
      <label
        htmlFor={name}
        className="block text-sm font-medium text-neutral-12"
      >
        {label}
        {required && (
          <>
            <span className="text-error-9 ml-1" aria-hidden="true">
              *
            </span>
            <span className="sr-only">(required)</span>
          </>
        )}
      </label>

      {/* Hint (before input for screen readers, hidden when error present) */}
      {hint && !error && (
        <p id={hintId} className="text-sm text-neutral-10">
          {hint}
        </p>
      )}

      {/* Input with injected accessibility props */}
      {enhancedChild}

      {/* Error message with icon (WCAG 1.4.1: not just color) */}
      <AnimatePresence>
        {error && (
          <motion.div
            id={errorId}
            role="alert"
            aria-live="assertive"
            initial={
              prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -4 }
            }
            animate={
              prefersReducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }
            }
            exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={
              prefersReducedMotion ? { duration: 0.1 } : { duration: 0.15 }
            }
            className="flex items-center gap-1.5 text-sm text-error-11"
          >
            <Icon icon={AlertCircle} size="sm" aria-hidden />
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

FormField.displayName = "FormField";

export default FormField;
