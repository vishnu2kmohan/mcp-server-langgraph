/**
 * Slider Component
 *
 * A consistent, accessible range slider component.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { cn } from "../../utils/cn";

/**
 * Slider styles using CVA
 */
export const sliderVariants = cva(
  // Base styles
  [
    "w-full appearance-none cursor-pointer rounded-full",
    "bg-neutral-200 dark:bg-neutral-700",
    "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
    "dark:focus:ring-offset-neutral-900",
    // Thumb styles (webkit)
    "[&::-webkit-slider-thumb]:appearance-none",
    "[&::-webkit-slider-thumb]:rounded-full",
    "[&::-webkit-slider-thumb]:bg-primary-500",
    "[&::-webkit-slider-thumb]:hover:bg-primary-600",
    "[&::-webkit-slider-thumb]:transition-colors",
    // Thumb styles (moz)
    "[&::-moz-range-thumb]:appearance-none",
    "[&::-moz-range-thumb]:border-none",
    "[&::-moz-range-thumb]:rounded-full",
    "[&::-moz-range-thumb]:bg-primary-500",
    "[&::-moz-range-thumb]:hover:bg-primary-600",
    "[&::-moz-range-thumb]:transition-colors",
  ],
  {
    variants: {
      size: {
        sm: [
          "h-1",
          "[&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3",
          "[&::-moz-range-thumb]:h-3 [&::-moz-range-thumb]:w-3",
        ],
        md: [
          "h-2",
          "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4",
          "[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4",
        ],
        lg: [
          "h-3",
          "[&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5",
          "[&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:w-5",
        ],
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

export type SliderSize = NonNullable<
  VariantProps<typeof sliderVariants>["size"]
>;

export interface SliderMark {
  /** Value at which to show the mark */
  value: number;
  /** Label to display at this mark */
  label: string;
}

export interface SliderProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "onChange" | "type" | "size"
> {
  /** Current value */
  value: number;
  /** Called when value changes */
  onChange: (value: number) => void;
  /** Minimum value (default: 0) */
  min?: number;
  /** Maximum value (default: 100) */
  max?: number;
  /** Step increment (default: 1) */
  step?: number;
  /** Label text */
  label?: string;
  /** Show current value */
  showValue?: boolean;
  /** Format function for value display */
  formatValue?: (value: number) => string;
  /** Size variant */
  size?: SliderSize;
  /** Whether the slider is disabled */
  disabled?: boolean;
  /** Tick marks with labels */
  marks?: SliderMark[];
  /** Additional CSS class */
  className?: string;
}

/**
 * Slider component for selecting numeric values within a range.
 */
export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  (
    {
      value,
      onChange,
      min = 0,
      max = 100,
      step = 1,
      label,
      showValue,
      formatValue,
      size = "md",
      disabled = false,
      marks,
      className,
      id: propId,
      ...props
    },
    ref,
  ) => {
    const generatedId = useId();
    const id = propId ?? generatedId;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!disabled) {
        onChange(parseFloat(e.target.value));
      }
    };

    const displayValue = formatValue ? formatValue(value) : String(value);

    return (
      <div className="w-full">
        {/* Label and value display */}
        {(label || showValue) && (
          <div className="flex justify-between items-center mb-2">
            {label && (
              <label
                htmlFor={id}
                className={cn(
                  "text-sm font-medium text-neutral-700 dark:text-neutral-300",
                  disabled && "opacity-50",
                )}
              >
                {label}
              </label>
            )}
            {showValue && (
              <span
                className={cn(
                  "text-sm font-medium text-neutral-900 dark:text-neutral-100",
                  disabled && "opacity-50",
                )}
              >
                {displayValue}
              </span>
            )}
          </div>
        )}

        {/* Slider input */}
        <input
          ref={ref}
          id={id}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={cn(sliderVariants({ size, disabled }), className)}
          {...props}
        />

        {/* Tick marks */}
        {marks && marks.length > 0 && (
          <div className="flex justify-between mt-1">
            {marks.map((mark) => (
              <span
                key={mark.value}
                className={cn(
                  "text-xs text-neutral-500 dark:text-neutral-400",
                  disabled && "opacity-50",
                )}
              >
                {mark.label}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  },
);

Slider.displayName = "Slider";
