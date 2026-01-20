/**
 * Toggle Component
 *
 * A switch/toggle component with consistent styling and accessibility.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes, useId } from "react";
import { cn } from "../../utils/cn";

/**
 * Toggle track styles using CVA
 */
export const toggleVariants = cva(
  // Base styles for the toggle track
  [
    "relative inline-flex shrink-0 cursor-pointer rounded-full",
    "border-2 border-transparent",
    "transition-colors duration-200 ease-in-out",
    "focus:outline-none focus:ring-2 focus:ring-primary-7 focus:ring-offset-2",
    "dark:focus:ring-offset-neutral-12",
  ],
  {
    variants: {
      size: {
        sm: "h-5 w-9",
        md: "h-6 w-11",
        lg: "h-7 w-14",
      },
      checked: {
        true: "bg-primary-9 dark:bg-primary-10",
        false: "bg-neutral-3",
      },
      disabled: {
        true: "cursor-not-allowed opacity-50",
        false: "",
      },
    },
    defaultVariants: {
      size: "md",
      checked: false,
      disabled: false,
    },
  },
);

/**
 * Toggle thumb (knob) styles
 */
const thumbVariants = cva(
  [
    "pointer-events-none inline-block rounded-full bg-neutral-1 shadow-lg",
    "ring-0 transition-transform duration-200 ease-in-out",
  ],
  {
    variants: {
      size: {
        sm: "h-4 w-4",
        md: "h-5 w-5",
        lg: "h-6 w-6",
      },
      checked: {
        true: "",
        false: "translate-x-0",
      },
    },
    compoundVariants: [
      { size: "sm", checked: true, class: "translate-x-4" },
      { size: "md", checked: true, class: "translate-x-5" },
      { size: "lg", checked: true, class: "translate-x-7" },
    ],
    defaultVariants: {
      size: "md",
      checked: false,
    },
  },
);

export type ToggleSize = NonNullable<
  VariantProps<typeof toggleVariants>["size"]
>;

export interface ToggleProps extends Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "onChange"
> {
  /** Whether the toggle is checked */
  checked: boolean;
  /** Called when the toggle state changes */
  onChange: (checked: boolean) => void;
  /** Toggle size */
  size?: ToggleSize;
  /** Optional label text */
  label?: string;
  /** Optional description text */
  description?: string;
}

/**
 * Toggle switch component with accessible controls
 */
export const Toggle = forwardRef<HTMLButtonElement, ToggleProps>(
  (
    {
      checked,
      onChange,
      size = "md",
      label,
      description,
      disabled = false,
      className,
      id: propId,
      ...props
    },
    ref,
  ) => {
    const generatedId = useId();
    const id = propId ?? generatedId;
    const descriptionId = description ? `${id}-description` : undefined;

    const handleClick = () => {
      if (!disabled) {
        onChange(!checked);
      }
    };

    const handleKeyDown = (event: React.KeyboardEvent) => {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        if (!disabled) {
          onChange(!checked);
        }
      }
    };

    const toggle = (
      <button
        ref={ref}
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        aria-disabled={disabled}
        aria-describedby={descriptionId}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        className={cn(toggleVariants({ size, checked, disabled }))}
        {...props}
      >
        <span
          aria-hidden="true"
          className={cn(thumbVariants({ size, checked }))}
        />
      </button>
    );

    // If no label, just return the toggle with optional wrapper for className
    if (!label && !description) {
      return <span className={className}>{toggle}</span>;
    }

    // With label and/or description
    return (
      <div className={cn("flex items-start gap-3", className)}>
        {toggle}
        <div className="flex flex-col">
          {label && (
            <label
              htmlFor={id}
              className={cn(
                "text-sm font-medium text-neutral-12",
                disabled && "opacity-50",
              )}
            >
              {label}
            </label>
          )}
          {description && (
            <span
              id={descriptionId}
              className={cn(
                "text-xs text-neutral-10",
                disabled && "opacity-50",
              )}
            >
              {description}
            </span>
          )}
        </div>
      </div>
    );
  },
);

Toggle.displayName = "Toggle";
