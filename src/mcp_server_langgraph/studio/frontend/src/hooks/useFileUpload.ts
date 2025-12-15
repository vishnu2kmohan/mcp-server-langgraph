/**
 * useFileUpload Hook
 *
 * Custom hook for file upload functionality.
 * Features:
 * - File selection (click or drag & drop)
 * - Upload progress tracking
 * - Multiple file support
 * - File type validation
 * - Size limit enforcement
 * - Upload cancellation
 */

import { useState, useCallback, useRef, useMemo } from "react";
import { nanoid } from "@reduxjs/toolkit";

/**
 * File status during upload lifecycle
 */
export type FileStatus = "pending" | "uploading" | "complete" | "error";

/**
 * Uploaded file with metadata
 */
export interface UploadFile {
  id: string;
  file: File;
  status: FileStatus;
  progress: number;
  error?: string;
  response?: unknown;
}

/**
 * Upload options
 */
export interface UseFileUploadOptions {
  /** Maximum file size in MB */
  maxSizeMB?: number;
  /** Accepted MIME types (e.g., ['image/png', 'image/jpeg']) */
  acceptedTypes?: string[];
  /** Maximum number of files */
  maxFiles?: number;
  /** Upload URL endpoint */
  uploadUrl?: string;
  /** Callback when all uploads complete */
  onUploadComplete?: (files: UploadFile[]) => void;
  /** Callback on upload error */
  onError?: (error: string, file: UploadFile) => void;
}

/**
 * Drag event handlers for drop zone
 */
export interface DragHandlers {
  onDragEnter: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}

/**
 * useFileUpload return type
 */
export interface UseFileUploadReturn {
  /** List of selected files */
  files: UploadFile[];
  /** Whether upload is in progress */
  isUploading: boolean;
  /** Whether drag is over drop zone */
  isDragging: boolean;
  /** Overall upload progress (0-100) */
  progress: number;
  /** Current error message */
  error: string | null;
  /** Add files to the list */
  selectFiles: (files: File[]) => void;
  /** Remove a file by ID */
  removeFile: (id: string) => void;
  /** Clear all files */
  clearFiles: () => void;
  /** Start uploading files */
  uploadFiles: () => void;
  /** Cancel current upload */
  cancelUpload: () => void;
  /** Drag event handlers */
  dragHandlers: DragHandlers;
}

/**
 * File upload hook
 */
export function useFileUpload(
  options: UseFileUploadOptions = {},
): UseFileUploadReturn {
  const {
    maxSizeMB = 10,
    acceptedTypes,
    maxFiles,
    uploadUrl = "/api/upload",
    onUploadComplete,
    onError,
  } = options;

  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Store XHR references for cancellation
  const xhrRefs = useRef<XMLHttpRequest[]>([]);

  /**
   * Validate a file against constraints
   */
  const validateFile = useCallback(
    (file: File): { valid: boolean; error?: string } => {
      // Check size
      const maxBytes = maxSizeMB * 1024 * 1024;
      if (file.size > maxBytes) {
        return {
          valid: false,
          error: `File size exceeds ${maxSizeMB}MB limit`,
        };
      }

      // Check type
      if (acceptedTypes && acceptedTypes.length > 0) {
        if (!acceptedTypes.includes(file.type)) {
          return {
            valid: false,
            error: `File type ${file.type} is not accepted`,
          };
        }
      }

      return { valid: true };
    },
    [maxSizeMB, acceptedTypes],
  );

  /**
   * Add files to the list
   */
  const selectFiles = useCallback(
    (newFiles: File[]) => {
      setError(null);

      // Limit number of files if maxFiles is set
      const filesToAdd = maxFiles ? newFiles.slice(0, maxFiles) : newFiles;

      const uploadFiles: UploadFile[] = filesToAdd.map((file) => {
        const validation = validateFile(file);

        return {
          id: nanoid(),
          file,
          status: validation.valid ? "pending" : "error",
          progress: 0,
          error: validation.error,
        };
      });

      setFiles((prev) => {
        const combined = [...prev, ...uploadFiles];
        // Enforce maxFiles limit on combined list
        return maxFiles ? combined.slice(0, maxFiles) : combined;
      });
    },
    [validateFile, maxFiles],
  );

  /**
   * Remove a file by ID
   */
  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  /**
   * Clear all files
   */
  const clearFiles = useCallback(() => {
    setFiles([]);
    setProgress(0);
    setError(null);
  }, []);

  /**
   * Upload a single file
   */
  const uploadSingleFile = useCallback(
    (uploadFile: UploadFile): Promise<void> => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhrRefs.current.push(xhr);

        xhr.open("POST", uploadUrl, true);

        // Track progress
        xhr.upload.addEventListener("progress", (event) => {
          if (event.lengthComputable) {
            const fileProgress = Math.round((event.loaded / event.total) * 100);
            setFiles((prev) =>
              prev.map((f) =>
                f.id === uploadFile.id
                  ? { ...f, progress: fileProgress, status: "uploading" }
                  : f,
              ),
            );
          }
        });

        // Handle completion
        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            let response;
            try {
              response = JSON.parse(xhr.response);
            } catch {
              response = xhr.response;
            }

            setFiles((prev) =>
              prev.map((f) =>
                f.id === uploadFile.id
                  ? { ...f, status: "complete", progress: 100, response }
                  : f,
              ),
            );
            resolve();
          } else {
            const errorMsg = `Upload failed with status ${xhr.status}`;
            setFiles((prev) =>
              prev.map((f) =>
                f.id === uploadFile.id
                  ? { ...f, status: "error", error: errorMsg }
                  : f,
              ),
            );
            onError?.(errorMsg, uploadFile);
            reject(new Error(errorMsg));
          }
        });

        // Handle error
        xhr.addEventListener("error", () => {
          const errorMsg = "Network error during upload";
          setFiles((prev) =>
            prev.map((f) =>
              f.id === uploadFile.id
                ? { ...f, status: "error", error: errorMsg }
                : f,
            ),
          );
          onError?.(errorMsg, uploadFile);
          reject(new Error(errorMsg));
        });

        // Send the file
        const formData = new FormData();
        formData.append("file", uploadFile.file);
        xhr.send(formData);
      });
    },
    [uploadUrl, onError],
  );

  /**
   * Upload all pending files
   */
  const uploadFiles = useCallback(async () => {
    const pendingFiles = files.filter((f) => f.status === "pending");
    if (pendingFiles.length === 0) return;

    setIsUploading(true);
    setError(null);
    xhrRefs.current = [];

    try {
      // Upload files in parallel (could be sequential if needed)
      await Promise.allSettled(pendingFiles.map(uploadSingleFile));

      // Calculate overall progress
      setProgress(100);

      // Check if all completed successfully
      const currentFiles = files;
      const allComplete = currentFiles.every(
        (f) => f.status === "complete" || f.status === "error",
      );

      if (allComplete) {
        onUploadComplete?.(currentFiles);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }, [files, uploadSingleFile, onUploadComplete]);

  /**
   * Cancel all uploads
   */
  const cancelUpload = useCallback(() => {
    xhrRefs.current.forEach((xhr) => xhr.abort());
    xhrRefs.current = [];
    setIsUploading(false);

    // Reset uploading files to pending
    setFiles((prev) =>
      prev.map((f) =>
        f.status === "uploading" ? { ...f, status: "pending", progress: 0 } : f,
      ),
    );
  }, []);

  /**
   * Drag event handlers
   */
  const dragHandlers: DragHandlers = useMemo(
    () => ({
      onDragEnter: (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
      },
      onDragLeave: (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
      },
      onDragOver: (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
      },
      onDrop: (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const droppedFiles = Array.from(e.dataTransfer.files);
        if (droppedFiles.length > 0) {
          selectFiles(droppedFiles);
        }
      },
    }),
    [selectFiles],
  );

  return {
    files,
    isUploading,
    isDragging,
    progress,
    error,
    selectFiles,
    removeFile,
    clearFiles,
    uploadFiles,
    cancelUpload,
    dragHandlers,
  };
}
