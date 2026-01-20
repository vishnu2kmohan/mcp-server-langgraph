/**
 * Select Component
 *
 * A consistent, accessible select component with multiple variants and sizes.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 * Aligned with the shared design system tokens.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "../../utils/cn";

/**
 * Select variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const selectVariants = cva(
  // Base styles
  [
    "block rounded-lg border bg-neutral-1 transition-colors duration-fast",
    "appearance-none cursor-pointer",
    "bg-no-repeat bg-right",
    // Chevron icon as background
    "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')]",
    "bg-[length:1.5rem_1.5rem]",
    "bg-[position:right_0.5rem_center]",
    "focus:outline-none focus:ring-2 focus:ring-offset-0",
  ],
  {
    variants: {
      variant: {
        default: [
          "border-neutral-5",
          "text-neutral-12",
          "focus:border-primary-9 focus:ring-primary-a3",
          "dark:focus:border-primary-7 dark:focus:ring-primary-a3",
        ],
        error: [
          "border-error-9 dark:border-error-7",
          "text-neutral-12",
          "focus:border-error-9 focus:ring-error-a3",
          "dark:focus:border-error-7 dark:focus:ring-error-a3",
        ],
        success: [
          "border-success-9 dark:border-success-7",
          "text-neutral-12",
          "focus:border-success-9 focus:ring-success-a3",
          "dark:focus:border-success-7 dark:focus:ring-success-a3",
        ],
      },
      size: {
        sm: "px-3 py-1.5 pr-8 text-xs",
        md: "px-4 py-2 pr-10 text-sm",
        lg: "px-4 py-2.5 pr-10 text-base",
      },
      disabled: {
        true: "cursor-not-allowed opacity-50 bg-neutral-2",
        false: "",
      },
      fullWidth: {
        true: "w-full",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      disabled: false,
      fullWidth: true,
    },
  },
);

export type SelectVariant = NonNullable<
  VariantProps<typeof selectVariants>["variant"]
>;
export type SelectSize = NonNullable<
  VariantProps<typeof selectVariants>["size"]
>;

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps
  extends
    Omit<SelectHTMLAttributes<HTMLSelectElement>, "size">,
    Omit<VariantProps<typeof selectVariants>, "disabled" | "fullWidth"> {
  /** Array of options to display (alternative to children) */
  options?: SelectOption[];
  /** Placeholder text shown as first option */
  placeholder?: string;
  /** Make the select take full width of its container */
  fullWidth?: boolean;
}

/**
 * Select component with consistent styling
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      variant,
      size,
      options,
      placeholder,
      fullWidth = true,
      disabled,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <select
        ref={ref}
        disabled={disabled}
        className={cn(
          selectVariants({
            variant,
            size,
            disabled: !!disabled,
            fullWidth,
          }),
          className,
        )}
        {...props}
      >
        {placeholder && (
          <option value="" disabled={props.required}>
            {placeholder}
          </option>
        )}
        {options
          ? options.map((option) => (
              <option
                key={option.value}
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </option>
            ))
          : children}
      </select>
    );
  },
);

Select.displayName = "Select";
