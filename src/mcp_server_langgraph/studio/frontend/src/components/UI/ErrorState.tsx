/**
 * ErrorState Component
 *
 * Standardized error state component with CVA-based type-safe variants.
 * Provides consistent error display across pages with customizable styling,
 * retry functionality, and accessible design.
 *
 * Uses class-variance-authority (CVA) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "../../utils/cn";

import { Button } from "@/components/UI";

/**
 * ErrorState variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const errorStateVariants = cva(
  // Base styles
  "flex flex-col items-center justify-center text-center",
  {
    variants: {
      variant: {
        default: "h-64",
        compact: "py-8",
        fullscreen: "h-full",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export type ErrorStateVariant = NonNullable<
  VariantProps<typeof errorStateVariants>["variant"]
>;

export interface ErrorStateProps extends VariantProps<
  typeof errorStateVariants
> {
  /** Error title */
  title?: string;
  /** Error message to display */
  message?: string;
  /** Callback when retry button is clicked. If not provided, retry button is hidden */
  onRetry?: () => void;
  /** Custom retry button text */
  retryText?: string;
  /** Optional className for additional styling */
  className?: string;
}

/**
 * ErrorState component with semantic error display
 */
export function ErrorState({
  title = "Error",
  message = "Something went wrong",
  onRetry,
  retryText = "Retry",
  variant,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(errorStateVariants({ variant }), className)}
    >
      <AlertCircle size={48} className="text-error-9 mb-4" />
      <h3 className="text-lg font-medium text-neutral-12 mb-2">
        {title}
      </h3>
      <p className="text-neutral-10 mb-4 max-w-md">
        {message}
      </p>
      {onRetry && (
        <Button
          variant="primary"
          onClick={onRetry}
          leftIcon={<RefreshCw size={16} />}
        >
          {retryText}
        </Button>
      )}
    </div>
  );
}

export default ErrorState;
