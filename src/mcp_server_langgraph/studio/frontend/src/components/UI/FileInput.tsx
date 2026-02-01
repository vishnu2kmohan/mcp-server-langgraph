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
    "border-neutral-5",
    "hover:border-primary-7 dark:hover:border-primary-9",
    "focus-within:border-primary-9 focus-within:ring-2 focus-within:ring-primary-a3",
  ],
  {
    variants: {
      size: {
        sm: "p-3",
        md: "p-4",
        lg: "p-6",
      },
      disabled: {
        true: "opacity-50 cursor-not-allowed hover:border-neutral-5 dark:hover:border-neutral-6",
        false: "cursor-pointer",
      },
      error: {
        true: "border-error-9 dark:border-error-9 hover:border-error-9",
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
              "block text-sm font-medium text-neutral-11 mb-2",
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
                  error ? "text-error-9" : "text-neutral-9",
                )}
              />
              <p className="text-sm text-neutral-11">
                <span className="font-medium text-primary-10 dark:text-primary-7">
                  Click to upload
                </span>{" "}
                or drag and drop
              </p>
              {accept && (
                <p className="text-xs text-neutral-10 mt-1">{accept}</p>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Upload className="w-4 h-4 text-neutral-10" />
              <span className="text-sm text-neutral-11">
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
                className="flex items-center justify-between p-2 bg-neutral-1 rounded-md"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <File className="w-4 h-4 text-neutral-10 flex-shrink-0" />
                  <span className="text-sm text-neutral-11 truncate">
                    {file.name}
                  </span>
                  {showFileSize && (
                    <span className="text-xs text-neutral-10 flex-shrink-0">
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
                    className="p-1 text-neutral-9 hover:text-neutral-11 rounded"
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
          <p className="mt-1 text-sm text-neutral-10">{helperText}</p>
        )}

        {/* Error message */}
        {error && (
          <p className="mt-1 text-sm text-error-10 dark:text-error-7">
            {error}
          </p>
        )}
      </div>
    );
  },
);

FileInput.displayName = "FileInput";
