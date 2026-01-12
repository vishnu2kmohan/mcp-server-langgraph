/**
 * FileInput Component
 *
 * A consistent, accessible file upload component.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { Upload, X, File } from "lucide-react";
import { cn } from "../../utils/cn";

/**
 * FileInput container styles using CVA
 */
export const fileInputVariants = cva(
  // Base styles
  [
    "relative border-2 border-dashed rounded-lg transition-colors",
    "border-neutral-300 dark:border-neutral-600",
    "hover:border-primary-400 dark:hover:border-primary-500",
    "focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20",
  ],
  {
    variants: {
      size: {
        sm: "p-3",
        md: "p-4",
        lg: "p-6",
      },
      disabled: {
        true: "opacity-50 cursor-not-allowed hover:border-neutral-300 dark:hover:border-neutral-600",
        false: "cursor-pointer",
      },
      error: {
        true: "border-error-500 dark:border-error-500 hover:border-error-500",
        false: "",
      },
    },
    defaultVariants: {
      size: "md",
      disabled: false,
      error: false,
    },
  },
);

export type FileInputSize = NonNullable<
  VariantProps<typeof fileInputVariants>["size"]
>;
export type FileInputVariant = "default" | "compact";

export interface FileInputProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "onChange" | "type" | "size"
> {
  /** Called when files are selected */
  onChange: (files: File[]) => void;
  /** Accepted file types (e.g., ".pdf,.doc") */
  accept?: string;
  /** Allow multiple file selection */
  multiple?: boolean;
  /** Label text */
  label?: string;
  /** Helper text below the input */
  helperText?: string;
  /** Error message */
  error?: string;
  /** Size variant */
  size?: FileInputSize;
  /** Display variant - default shows drag zone, compact shows button only */
  variant?: FileInputVariant;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Currently selected files (for controlled display) */
  selectedFiles?: File[];
  /** Show file size in the display */
  showFileSize?: boolean;
  /** Called when clear button is clicked */
  onClear?: () => void;
  /** Additional CSS class */
  className?: string;
}

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * FileInput component for file upload.
 */
export const FileInput = forwardRef<HTMLInputElement, FileInputProps>(
  (
    {
      onChange,
      accept,
      multiple = false,
      label,
      helperText,
      error,
      size = "md",
      variant = "default",
      disabled = false,
      selectedFiles = [],
      showFileSize = false,
      onClear,
      className,
      id: propId,
      ...props
    },
    ref,
  ) => {
    const generatedId = useId();
    const id = propId ?? generatedId;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!disabled && e.target.files) {
        onChange(Array.from(e.target.files));
      }
    };

    const hasFiles = selectedFiles.length > 0;

    return (
      <div className="w-full">
        {/* Label */}
        {label && (
          <label
            htmlFor={id}
            className={cn(
              "block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2",
              disabled && "opacity-50",
            )}
          >
            {label}
          </label>
        )}

        {/* File input container */}
        <div
          data-testid="file-input-container"
          className={cn(
            fileInputVariants({ size, disabled, error: !!error }),
            className,
          )}
        >
          {/* Hidden file input */}
          <input
            ref={ref}
            id={id}
            type="file"
            accept={accept}
            multiple={multiple}
            onChange={handleChange}
            disabled={disabled}
            data-testid="file-input"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
            {...props}
          />

          {/* Content based on variant and state */}
          {variant === "default" ? (
            <div className="flex flex-col items-center justify-center text-center">
              <Upload
                className={cn(
                  "w-8 h-8 mb-2",
                  error
                    ? "text-error-500"
                    : "text-neutral-400 dark:text-neutral-500",
                )}
              />
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                <span className="font-medium text-primary-600 dark:text-primary-400">
                  Click to upload
                </span>{" "}
                or drag and drop
              </p>
              {accept && (
                <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
                  {accept}
                </p>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Upload className="w-4 h-4 text-neutral-500" />
              <span className="text-sm text-neutral-600 dark:text-neutral-400">
                Choose file{multiple ? "s" : ""}
              </span>
            </div>
          )}
        </div>

        {/* Selected files display */}
        {hasFiles && (
          <div className="mt-2 space-y-1">
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center justify-between p-2 bg-neutral-50 dark:bg-neutral-800 rounded-md"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <File className="w-4 h-4 text-neutral-500 flex-shrink-0" />
                  <span className="text-sm text-neutral-700 dark:text-neutral-300 truncate">
                    {file.name}
                  </span>
                  {showFileSize && (
                    <span className="text-xs text-neutral-500 flex-shrink-0">
                      ({formatFileSize(file.size)})
                    </span>
                  )}
                </div>
                {onClear && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onClear();
                    }}
                    className="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 rounded"
                    aria-label="Remove file"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Helper text */}
        {helperText && !error && (
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            {helperText}
          </p>
        )}

        {/* Error message */}
        {error && (
          <p className="mt-1 text-sm text-error-600 dark:text-error-400">
            {error}
          </p>
        )}
      </div>
    );
  },
);

FileInput.displayName = "FileInput";
