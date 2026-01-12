/**
 * Dialog Component
 *
 * Reusable base dialog component with:
 * - Accessible modal behavior (role, aria attributes)
 * - Backdrop click to close
 * - Escape key to close
 * - Customizable sizes via CVA
 * - Optional footer section
 *
 * Uses CVA (class-variance-authority) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "../../utils/cn";

import { Button } from "@/components/UI";

/**
 * Dialog variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const dialogVariants = cva(
  // Base styles
  [
    "relative bg-white dark:bg-neutral-800 rounded-lg shadow-xl",
    "w-full mx-4 max-h-[90vh] overflow-y-auto",
  ],
  {
    variants: {
      size: {
        sm: "max-w-sm",
        md: "max-w-md",
        lg: "max-w-lg",
        xl: "max-w-xl",
        "2xl": "max-w-2xl",
        full: "max-w-full",
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
);

export type DialogSize = NonNullable<
  VariantProps<typeof dialogVariants>["size"]
>;

export interface DialogProps extends VariantProps<typeof dialogVariants> {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog should close */
  onClose: () => void;
  /** Dialog title */
  title: string;
  /** Dialog content */
  children: ReactNode;
  /** Optional footer content */
  footer?: ReactNode;
  /** Additional classes for content area */
  contentClassName?: string;
}

/**
 * Dialog component with consistent styling
 */
export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  size,
  contentClassName,
}: DialogProps) {
  // Handle Escape key
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      className="fixed inset-0 z-[60] flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        data-testid="dialog-backdrop"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      {/* Dialog Panel */}
      <div className={cn(dialogVariants({ size }))}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2
            id="dialog-title"
            className="text-lg font-semibold text-neutral-900 dark:text-neutral-100"
          >
            {title}
          </h2>
          <Button
            onClick={onClose}
            aria-label="Close"
            className={cn(
              "p-1 rounded-full",
              "text-neutral-500 dark:text-neutral-400",
              "hover:text-neutral-700 dark:hover:text-neutral-200",
              "hover:bg-neutral-100 dark:hover:bg-neutral-700",
            )}
          >
            <X size={20} />
          </Button>
        </div>

        {/* Content */}
        <div
          data-testid="dialog-content"
          className={cn("p-4", contentClassName)}
        >
          {children}
        </div>

        {/* Footer (optional) */}
        {footer && (
          <div
            data-testid="dialog-footer"
            className="flex justify-end gap-2 p-4 border-t border-neutral-200 dark:border-neutral-700"
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dialog;
