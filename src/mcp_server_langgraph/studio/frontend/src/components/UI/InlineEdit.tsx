/**
 * InlineEdit Component
 *
 * A click-to-edit text component with Enter/Escape handling.
 * Used for inline editing of session names, artifact titles, etc.
 */

import {
  forwardRef,
  useState,
  useRef,
  useEffect,
  useCallback,
  type HTMLAttributes,
  type KeyboardEvent,
  type FocusEvent,
} from "react";

import { Button } from "@/components/UI";
import { cn } from "../../utils/cn";

export interface InlineEditProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  "onSave"
> {
  /** Current value to display/edit */
  value: string;
  /** Callback when value is saved */
  onSave: (value: string) => void | Promise<void>;
  /** Callback when editing is cancelled */
  onCancel?: () => void;
  /** Placeholder text when value is empty */
  placeholder?: string;
  /** Validation function - returns true if valid */
  validate?: (value: string) => boolean;
  /** Disable editing */
  disabled?: boolean;
  /** Input class name for styling */
  inputClassName?: string;
  /** Start in edit mode immediately (useful for programmatic edit triggers) */
  startInEditMode?: boolean;
}

/**
 * InlineEdit component for click-to-edit functionality
 */
export const InlineEdit = forwardRef<HTMLDivElement, InlineEditProps>(
  (
    {
      value,
      onSave,
      onCancel,
      placeholder = "Click to edit",
      validate,
      disabled = false,
      className,
      inputClassName,
      "aria-label": ariaLabel,
      startInEditMode = false,
      ...props
    },
    ref,
  ) => {
    const [isEditing, setIsEditing] = useState(startInEditMode);
    const [editValue, setEditValue] = useState(value);
    const [isLoading, setIsLoading] = useState(false);
    const [hasError, setHasError] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // Sync editValue when value prop changes
    useEffect(() => {
      if (!isEditing) {
        setEditValue(value);
      }
    }, [value, isEditing]);

    // Focus and select all text when entering edit mode
    useEffect(() => {
      if (isEditing && inputRef.current) {
        inputRef.current.focus();
        inputRef.current.select();
      }
    }, [isEditing]);

    const enterEditMode = useCallback(() => {
      if (!disabled) {
        setEditValue(value);
        setHasError(false);
        setIsEditing(true);
      }
    }, [disabled, value]);

    const exitEditMode = useCallback(() => {
      setIsEditing(false);
      setHasError(false);
    }, []);

    const handleSave = useCallback(async () => {
      // Don't save if value unchanged
      if (editValue === value) {
        exitEditMode();
        return;
      }

      // Validate if provided
      if (validate && !validate(editValue)) {
        setHasError(true);
        return;
      }

      setIsLoading(true);
      try {
        await onSave(editValue);
        exitEditMode();
      } catch {
        setHasError(true);
      } finally {
        setIsLoading(false);
      }
    }, [editValue, value, validate, onSave, exitEditMode]);

    const handleCancel = useCallback(() => {
      setEditValue(value);
      exitEditMode();
      onCancel?.();
    }, [value, exitEditMode, onCancel]);

    const handleKeyDown = useCallback(
      (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
          e.preventDefault();
          handleSave();
        } else if (e.key === "Escape") {
          e.preventDefault();
          handleCancel();
        }
      },
      [handleSave, handleCancel],
    );

    const handleBlur = useCallback(
      (_e: FocusEvent<HTMLInputElement>) => {
        // Don't save on blur if there's an error - user might want to fix it
        if (!hasError) {
          handleSave();
        }
      },
      [hasError, handleSave],
    );

    if (isEditing) {
      return (
        <div
          ref={ref}
          className={cn("relative inline-flex items-center", className)}
          {...props}
        >
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={(e) => {
              setEditValue(e.target.value);
              setHasError(false);
            }}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            disabled={isLoading}
            aria-label={ariaLabel}
            className={cn(
              "w-full px-2 py-1 text-sm rounded border",
              "focus:outline-none focus:ring-2 focus:ring-brand-primary",
              "dark:bg-neutral-800 dark:text-neutral-100",
              hasError
                ? "border-error-500 focus:ring-error-500"
                : "border-neutral-300 dark:border-neutral-600",
              isLoading && "opacity-50",
              inputClassName,
            )}
          />
          {isLoading && (
            <span
              data-testid="inline-edit-loading"
              className="absolute right-2 flex items-center"
            >
              <svg
                className="animate-spin h-4 w-4 text-neutral-500 dark:text-neutral-400"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </span>
          )}
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center",
          disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
          className,
        )}
        {...props}
      >
        <Button
          type="button"
          onClick={enterEditMode}
          disabled={disabled}
          aria-label={ariaLabel}
          className={cn(
            "text-left px-1 py-0.5 rounded",
            "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800",
            "focus:outline-none focus:ring-2 focus:ring-brand-primary",
            "transition-colors duration-fast",
            disabled && "pointer-events-none",
          )}
        >
          {value || (
            <span className="text-neutral-400 dark:text-neutral-400 italic">
              {placeholder}
            </span>
          )}
        </Button>
      </div>
    );
  },
);

InlineEdit.displayName = "InlineEdit";
