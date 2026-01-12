/**
 * Checkbox Component
 *
 * A consistent, accessible checkbox component with label support.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import {
  forwardRef,
  useId,
  useEffect,
  useRef,
  type InputHTMLAttributes,
} from "react";
import { cn } from "../../utils/cn";

/**
 * Checkbox input styles using CVA
 */
export const checkboxVariants = cva(
  // Base styles
  [
    "shrink-0 rounded border cursor-pointer",
    "appearance-none",
    "transition-colors duration-fast",
    "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
    "dark:focus:ring-offset-neutral-900",
    // Checked state
    "checked:bg-primary-500 checked:border-primary-500",
    "checked:dark:bg-primary-600 checked:dark:border-primary-600",
    // Unchecked state
    "bg-white dark:bg-neutral-800",
    "border-neutral-300 dark:border-neutral-600",
    // Hover
    "hover:border-primary-400 dark:hover:border-primary-500",
    // Checkmark via background image
    "checked:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20viewBox%3D%220%200%2016%2016%22%20fill%3D%22white%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M12.207%204.793a1%201%200%20010%201.414l-5%205a1%201%200%2001-1.414%200l-2-2a1%201%200%20011.414-1.414L6.5%209.086l4.293-4.293a1%201%200%20011.414%200z%22%2F%3E%3C%2Fsvg%3E')]",
    "bg-center bg-no-repeat",
  ],
  {
    variants: {
      size: {
        sm: "h-4 w-4",
        md: "h-5 w-5",
        lg: "h-6 w-6",
      },
      disabled: {
        true: "cursor-not-allowed opacity-50",
        false: "",
      },
    },
    defaultVariants: {
      size: "md",
      disabled: false,
    },
  },
);

export type CheckboxSize = NonNullable<
  VariantProps<typeof checkboxVariants>["size"]
>;

export interface CheckboxProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "onChange" | "size" | "type"
> {
  /** Whether the checkbox is checked */
  checked: boolean;
  /** Called when the checkbox state changes */
  onChange: (checked: boolean) => void;
  /** Checkbox size */
  size?: CheckboxSize;
  /** Optional label text */
  label?: string;
  /** Optional description text */
  description?: string;
  /** Whether the checkbox is in indeterminate state */
  indeterminate?: boolean;
}

/**
 * Checkbox component with accessible controls
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  (
    {
      checked,
      onChange,
      size = "md",
      label,
      description,
      disabled = false,
      indeterminate = false,
      className,
      id: propId,
      ...props
    },
    forwardedRef,
  ) => {
    const generatedId = useId();
    const id = propId ?? generatedId;
    const descriptionId = description ? `${id}-description` : undefined;

    // Internal ref for indeterminate support (mutable ref for assignment)
    const internalRef = useRef<HTMLInputElement | null>(null);

    // Sync indeterminate state
    useEffect(() => {
      const checkbox = internalRef.current;
      if (checkbox) {
        checkbox.indeterminate = indeterminate;
      }
    }, [indeterminate]);

    const handleChange = () => {
      if (!disabled) {
        onChange(!checked);
      }
    };

    // Merge refs
    const setRefs = (element: HTMLInputElement | null) => {
      internalRef.current = element;
      if (typeof forwardedRef === "function") {
        forwardedRef(element);
      } else if (forwardedRef) {
        forwardedRef.current = element;
      }
    };

    const checkbox = (
      <input
        ref={setRefs}
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={handleChange}
        aria-describedby={descriptionId}
        className={cn(checkboxVariants({ size, disabled }))}
        {...props}
      />
    );

    // If no label, just return the checkbox wrapped for className support
    if (!label && !description) {
      return (
        <label className={cn("inline-flex items-center", className)}>
          {checkbox}
        </label>
      );
    }

    // With label and/or description
    return (
      <label
        htmlFor={id}
        className={cn(
          "inline-flex items-start gap-3 cursor-pointer",
          disabled && "cursor-not-allowed",
          className,
        )}
      >
        {checkbox}
        <div className="flex flex-col">
          {label && (
            <span
              className={cn(
                "text-sm font-medium text-neutral-900 dark:text-neutral-100",
                disabled && "opacity-50",
              )}
            >
              {label}
            </span>
          )}
          {description && (
            <span
              id={descriptionId}
              className={cn(
                "text-xs text-neutral-500 dark:text-neutral-400",
                disabled && "opacity-50",
              )}
            >
              {description}
            </span>
          )}
        </div>
      </label>
    );
  },
);

Checkbox.displayName = "Checkbox";
