/**
 * FormErrorSummary Component
 *
 * Displays all form validation errors at the top of complex forms.
 * Each error links to its corresponding field for easy navigation.
 *
 * @example
 * <FormErrorSummary
 *   errors={{
 *     email: "Invalid email address",
 *     password: "Password must be 8+ characters"
 *   }}
 * />
 */

import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/utils/cn";
import { Icon } from "./Icon";

// =============================================================================
// Types
// =============================================================================

export interface FormErrorSummaryProps {
  /** Record of field names to error messages */
  errors: Record<string, string>;
  /** Optional custom heading text */
  heading?: string;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function FormErrorSummary({
  errors,
  heading = "Please fix the following errors:",
  className,
}: FormErrorSummaryProps) {
  // Respect user's reduced motion preference for WCAG 2.2 AA compliance
  const prefersReducedMotion = useReducedMotion();
  const errorEntries = Object.entries(errors);

  if (errorEntries.length === 0) return null;

  const handleClick = (
    e: React.MouseEvent<HTMLAnchorElement>,
    fieldName: string,
  ) => {
    e.preventDefault();
    const element = document.getElementById(fieldName);
    if (element) {
      element.focus();
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        role="alert"
        aria-live="polite"
        initial={prefersReducedMotion ? undefined : { opacity: 0 }}
        animate={prefersReducedMotion ? undefined : { opacity: 1 }}
        exit={prefersReducedMotion ? undefined : { opacity: 0 }}
        transition={prefersReducedMotion ? undefined : { duration: 0.15 }}
        className={cn(
          "rounded-md bg-error-2 border border-error-6 p-4",
          className,
        )}
      >
        <div className="flex items-start gap-3">
          <Icon
            icon={AlertCircle}
            className="text-error-9 mt-0.5 shrink-0"
            aria-hidden
          />
          <div>
            <h3 className="text-sm font-medium text-error-11">{heading}</h3>
            <ul className="mt-2 text-sm text-error-11 list-disc pl-5 space-y-1">
              {errorEntries.map(([field, message]) => (
                <li key={field}>
                  <a
                    href={`#${field}`}
                    onClick={(e) => handleClick(e, field)}
                    className="underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-error-7 focus:ring-offset-1 rounded"
                  >
                    {message}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

FormErrorSummary.displayName = "FormErrorSummary";

export default FormErrorSummary;
