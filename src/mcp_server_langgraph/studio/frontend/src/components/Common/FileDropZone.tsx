/**
 * FileDropZone Component
 *
 * Drag-and-drop file upload zone.
 * Features:
 * - Drag state visual feedback
 * - Click to browse
 * - File type filtering
 * - Multiple file support
 * - Disabled state
 * - WCAG 2.1 AA accessibility
 */

import { useState, useRef, useCallback, ReactNode } from "react";
import { Upload, FileUp } from "lucide-react";

import { Button } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export interface FileDropZoneProps {
  /** Callback when files are selected */
  onFilesSelected: (files: File[]) => void;
  /** Accepted file types (e.g., "image/*", ".pdf,.doc") */
  accept?: string;
  /** Allow multiple files */
  multiple?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Custom content */
  children?: ReactNode;
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Component
// ==============================================================================

export function FileDropZone({
  onFilesSelected,
  accept,
  multiple = true,
  disabled = false,
  children,
  className = "",
}: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCountRef = useRef(0);

  // Handle drag enter
  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;

      dragCountRef.current++;
      if (dragCountRef.current === 1) {
        setIsDragging(true);
      }
    },
    [disabled],
  );

  // Handle drag leave
  const handleDragLeave = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;

      dragCountRef.current--;
      if (dragCountRef.current === 0) {
        setIsDragging(false);
      }
    },
    [disabled],
  );

  // Handle drag over
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  // Handle drop
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCountRef.current = 0;
      setIsDragging(false);

      if (disabled) return;

      const files = Array.from(e.dataTransfer.files);
      const firstFile = files[0];
      if (files.length > 0 && firstFile) {
        onFilesSelected(multiple ? files : [firstFile]);
      }
    },
    [disabled, multiple, onFilesSelected],
  );

  // Handle file input change
  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) {
        onFilesSelected(files);
      }
      // Reset input value to allow selecting the same file again
      e.target.value = "";
    },
    [onFilesSelected],
  );

  // Handle browse button click
  const handleBrowseClick = useCallback(() => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [disabled]);

  return (
    <div
      data-testid="file-drop-zone"
      data-dragging={isDragging ? "true" : "false"}
      role="region"
      aria-label="File drop zone. Drop files here or click the browse button."
      aria-disabled={disabled}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className={`
        relative flex flex-col items-center justify-center
        min-h-[200px] p-6
        border-2 border-dashed rounded-lg
        transition-colors duration-200
        focus:outline-none focus:ring-2 focus:ring-primary-500
        ${
          isDragging
            ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
            : "border-neutral-300 dark:border-neutral-600 hover:border-neutral-400 dark:border-neutral-500 dark:hover:border-neutral-500"
        }
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        ${className}
      `}
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleFileInputChange}
        className="hidden"
        aria-hidden="true"
        disabled={disabled}
      />
      {/* Default content or custom children */}
      {children || (
        <>
          <div
            className={`
              mb-4 p-4 rounded-full
              ${isDragging ? "bg-primary-100 dark:bg-primary-800" : "bg-neutral-100 dark:bg-neutral-700"}
            `}
          >
            {isDragging ? (
              <FileUp className="w-8 h-8 text-primary-500" aria-hidden="true" />
            ) : (
              <Upload
                className="w-8 h-8 text-neutral-400 dark:text-neutral-400"
                aria-hidden="true"
              />
            )}
          </div>

          <p className="text-sm text-neutral-600 dark:text-neutral-400 text-center mb-2">
            {isDragging ? "Drop files here" : "Drag and drop files here, or"}
          </p>

          {!isDragging && (
            <Button
              className="px-4 py-2 text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 focus:underline"
              type="button"
              onClick={handleBrowseClick}
              disabled={disabled}
            >
              Browse files
            </Button>
          )}

          {accept && (
            <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
              Accepted: {accept}
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default FileDropZone;
