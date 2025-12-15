/**
 * Dialog Component
 *
 * Reusable base dialog component with:
 * - Accessible modal behavior (role, aria attributes)
 * - Backdrop click to close
 * - Escape key to close
 * - Customizable sizes
 * - Optional footer section
 */

import { useEffect, ReactNode } from "react";
import { X } from "lucide-react";

export type DialogSize = "sm" | "md" | "lg" | "xl";

export interface DialogProps {
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
  /** Dialog size (default: md) */
  size?: DialogSize;
  /** Additional classes for content area */
  contentClassName?: string;
}

const sizeClasses: Record<DialogSize, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
};

export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  size = "md",
  contentClassName = "",
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
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        data-testid="dialog-backdrop"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Dialog Panel */}
      <div
        className={`relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full ${sizeClasses[size]} mx-4 max-h-[90vh] overflow-y-auto`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2
            id="dialog-title"
            className="text-lg font-semibold text-gray-900 dark:text-gray-100"
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div data-testid="dialog-content" className={`p-4 ${contentClassName}`}>
          {children}
        </div>

        {/* Footer (optional) */}
        {footer && (
          <div
            data-testid="dialog-footer"
            className="flex justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700"
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dialog;
