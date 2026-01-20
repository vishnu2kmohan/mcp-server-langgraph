/**
 * RadioGroup Component
 *
 * A consistent, accessible radio group component with label support.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import {
  createContext,
  forwardRef,
  useContext,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "../../utils/cn";

/**
 * Radio input styles using CVA
 */
export const radioVariants = cva(
  // Base styles
  [
    "shrink-0 rounded-full border cursor-pointer",
    "appearance-none",
    "transition-colors duration-fast",
    "focus:outline-none focus:ring-2 focus:ring-primary-7 focus:ring-offset-2",
    "dark:focus:ring-offset-neutral-12",
    // Checked state - uses radial gradient for inner dot
    "checked:bg-primary-9 checked:border-primary-9",
    "checked:dark:bg-primary-10 checked:dark:border-primary-10",
    // Inner dot via background
    "checked:bg-[radial-gradient(circle,white_40%,transparent_40%)]",
    // Unchecked state
    "bg-neutral-1",
    "border-neutral-5",
    // Hover
    "hover:border-primary-7 dark:hover:border-primary-9",
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

export type RadioSize = NonNullable<VariantProps<typeof radioVariants>["size"]>;

export type RadioGroupVariant = "default" | "card" | "rating";

// Context for RadioGroup
interface RadioGroupContextValue {
  name: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  size?: RadioSize;
  variant?: RadioGroupVariant;
}

const RadioGroupContext = createContext<RadioGroupContextValue | null>(null);

function useRadioGroup() {
  const context = useContext(RadioGroupContext);
  if (!context) {
    throw new Error("Radio must be used within a RadioGroup");
  }
  return context;
}

// RadioGroup Props
export interface RadioGroupProps {
  /** Unique name for the radio group (for form submission) */
  name: string;
  /** Currently selected value */
  value: string;
  /** Called when selection changes */
  onChange: (value: string) => void;
  /** Radio options as children */
  children: ReactNode;
  /** Optional legend/label for the group */
  legend?: string;
  /** Whether all radios are disabled */
  disabled?: boolean;
  /** Size of all radio buttons */
  size?: RadioSize;
  /** Layout orientation */
  orientation?: "vertical" | "horizontal";
  /** Visual variant: default, card (bordered cards), rating (compact horizontal scale) */
  variant?: RadioGroupVariant;
  /** Additional CSS class */
  className?: string;
  /** Aria label for the group */
  "aria-label"?: string;
}

/**
 * RadioGroup component - container for Radio options
 */
export function RadioGroup({
  name,
  value,
  onChange,
  children,
  legend,
  disabled = false,
  size = "md",
  orientation = "vertical",
  variant = "default",
  className,
  "aria-label": ariaLabel,
}: RadioGroupProps) {
  // Rating variant forces horizontal orientation
  const effectiveOrientation =
    variant === "rating" ? "horizontal" : orientation;

  return (
    <RadioGroupContext.Provider
      value={{ name, value, onChange, disabled, size, variant }}
    >
      <fieldset
        role="radiogroup"
        aria-label={ariaLabel}
        className={cn(
          "flex",
          variant === "rating" ? "gap-4 justify-center" : "gap-3",
          effectiveOrientation === "vertical"
            ? "flex-col"
            : "flex-row flex-wrap",
          className,
        )}
      >
        {legend && (
          <legend className="text-sm font-medium text-neutral-12 mb-2">
            {legend}
          </legend>
        )}
        {children}
      </fieldset>
    </RadioGroupContext.Provider>
  );
}

// Radio Props
export interface RadioProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "onChange" | "size" | "type"
> {
  /** Value of this radio option */
  value: string;
  /** Label text */
  label: string;
  /** Optional description text */
  description?: string;
  /** Whether this specific radio is disabled */
  disabled?: boolean;
}

/**
 * Radio component - individual radio button option
 */
export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  (
    {
      value,
      label,
      description,
      disabled: optionDisabled = false,
      className,
      id: propId,
      ...props
    },
    ref,
  ) => {
    const {
      name,
      value: selectedValue,
      onChange,
      disabled: groupDisabled,
      size,
      variant,
    } = useRadioGroup();
    const generatedId = useId();
    const id = propId ?? generatedId;
    const descriptionId = description ? `${id}-description` : undefined;
    const isDisabled = groupDisabled || optionDisabled;
    const isChecked = selectedValue === value;

    const handleChange = () => {
      if (!isDisabled) {
        onChange(value);
      }
    };

    // Variant-specific label styles
    const getLabelClassName = () => {
      const baseClasses = "cursor-pointer";
      const disabledClasses = isDisabled ? "cursor-not-allowed" : "";

      switch (variant) {
        case "card":
          return cn(
            baseClasses,
            disabledClasses,
            "flex items-start gap-3 p-3 border rounded-lg transition-colors",
            isChecked
              ? "border-primary-9 bg-primary-1 dark:bg-primary-a3"
              : "border-neutral-5 hover:border-neutral-5 dark:hover:border-neutral-6",
            className,
          );
        case "rating":
          return cn(
            baseClasses,
            disabledClasses,
            "flex flex-col items-center",
            className,
          );
        default:
          return cn(
            "inline-flex items-start gap-3",
            baseClasses,
            disabledClasses,
            className,
          );
      }
    };

    // For rating variant, render label below radio
    if (variant === "rating") {
      return (
        <label htmlFor={id} className={getLabelClassName()}>
          <input
            ref={ref}
            id={id}
            type="radio"
            name={name}
            value={value}
            checked={isChecked}
            disabled={isDisabled}
            onChange={handleChange}
            className={cn(radioVariants({ size, disabled: isDisabled }))}
            {...props}
          />
          <span
            className={cn(
              "text-xs text-neutral-10 mt-1",
              isDisabled && "opacity-50",
            )}
          >
            {label}
          </span>
        </label>
      );
    }

    return (
      <label htmlFor={id} className={getLabelClassName()}>
        <input
          ref={ref}
          id={id}
          type="radio"
          name={name}
          value={value}
          checked={isChecked}
          disabled={isDisabled}
          onChange={handleChange}
          aria-describedby={descriptionId}
          className={cn(
            radioVariants({ size, disabled: isDisabled }),
            variant === "card" && "mt-1",
          )}
          {...props}
        />
        <div className="flex flex-col">
          <span
            className={cn(
              "text-sm font-medium text-neutral-12",
              isDisabled && "opacity-50",
            )}
          >
            {label}
          </span>
          {description && (
            <span
              id={descriptionId}
              className={cn(
                "text-xs text-neutral-10",
                isDisabled && "opacity-50",
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

Radio.displayName = "Radio";
