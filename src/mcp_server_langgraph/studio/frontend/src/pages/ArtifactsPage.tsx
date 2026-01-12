/**
 * ArtifactsPage
 *
 * Artifact browser for session artifacts and uploaded files.
 * Provides artifact listing, preview, and management capabilities.
 * Wired to the artifacts API via React Router loader.
 */
import { useState, useMemo, useCallback } from "react";
import { useRouteLoaderData, useRevalidator, useNavigate } from "react-router";
import {
  FileText,
  FileCode,
  FileImage,
  File,
  FolderOpen,
  Search,
  Grid,
  List,
  Download,
  Trash2,
  Eye,
  AlertCircle,
  X,
} from "lucide-react";
import { cn } from "../utils/cn";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";
import { devLogger } from "../utils/devLogger";
import { sessionTelemetry } from "../utils/sessionTelemetry";
import type { ArtifactsLoaderData } from "../router/loaders";
import type { CanvasArtifact } from "../types/artifacts";
import { AIEmptyState } from "../components/EmptyState/AIEmptyState";

import { Button, Input } from "@/components/UI";

const logger = devLogger.withPrefix("[ArtifactsPage]");

// =============================================================================
// Types
// =============================================================================

interface FileItem {
  id: string;
  name: string;
  type: "code" | "document" | "image" | "other";
  size: number;
  createdAt: string;
  updatedAt: string;
  sessionId?: string;
  mimeType?: string;
}

type ViewMode = "grid" | "list";

// =============================================================================
// Artifact to File Mapping
// =============================================================================

/**
 * Convert CanvasArtifact to FileItem for display
 */
function artifactToFileItem(artifact: CanvasArtifact): FileItem {
  // Map contentType to file type
  const typeMap: Record<CanvasArtifact["contentType"], FileItem["type"]> = {
    code: "code",
    markdown: "document",
    json: "code",
    jsx: "code",
    mermaid: "code",
    html: "code",
  };

  // Estimate size from content length (approximate bytes)
  const size = artifact.content?.length ?? 0;

  // Get file extension based on content type
  const extensionMap: Record<CanvasArtifact["contentType"], string> = {
    code: artifact.editMetadata?.language ?? "txt",
    markdown: "md",
    json: "json",
    jsx: "jsx",
    mermaid: "mmd",
    html: "html",
  };

  const extension = extensionMap[artifact.contentType] ?? "txt";
  const baseName = artifact.title ?? `artifact-${artifact.id.slice(0, 8)}`;
  const name = baseName.includes(".") ? baseName : `${baseName}.${extension}`;

  return {
    id: artifact.id,
    name,
    type: typeMap[artifact.contentType] ?? "other",
    size,
    createdAt: artifact.createdAt,
    updatedAt: artifact.updatedAt,
    sessionId: artifact.sessionId,
    mimeType: getMimeType(
      artifact.contentType,
      artifact.editMetadata?.language,
    ),
  };
}

/**
 * Get MIME type for artifact
 */
function getMimeType(
  contentType: CanvasArtifact["contentType"],
  language?: string,
): string {
  const mimeMap: Record<string, string> = {
    code: language === "python" ? "text/x-python" : "text/plain",
    markdown: "text/markdown",
    json: "application/json",
    jsx: "text/javascript",
    mermaid: "text/plain",
    html: "text/html",
  };
  return mimeMap[contentType] ?? "text/plain";
}

// =============================================================================
// Helper Functions
// =============================================================================

function getFileIcon(type: FileItem["type"]) {
  switch (type) {
    case "code":
      return <FileCode size={24} className="text-primary-500" />;
    case "document":
      return <FileText size={24} className="text-success-500" />;
    case "image":
      return <FileImage size={24} className="text-insight-500" />;
    default:
      return (
        <File size={24} className="text-neutral-500 dark:text-neutral-400" />
      );
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// =============================================================================
// File Card Component
// =============================================================================

interface FileCardProps {
  file: FileItem;
  viewMode: ViewMode;
  onPreview: (file: FileItem) => void;
  onDownload: (file: FileItem) => void;
  onDelete: (file: FileItem) => void;
}

function FileCard({
  file,
  viewMode,
  onPreview,
  onDownload,
  onDelete,
}: FileCardProps) {
  if (viewMode === "grid") {
    return (
      <div
        data-testid={`file-card-${file.id}`}
        className={cn(
          "flex flex-col items-center p-4 rounded-lg",
          "bg-white dark:bg-neutral-800",
          "border border-neutral-200 dark:border-neutral-700",
          "hover:border-primary-300 dark:hover:border-primary-600",
          "transition-colors cursor-pointer",
          "group",
        )}
        onClick={() => onPreview(file)}
      >
        <div className="mb-3">{getFileIcon(file.type)}</div>
        <p className="text-sm font-medium text-neutral-900 dark:text-white truncate w-full text-center">
          {file.name}
        </p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
          {formatFileSize(file.size)}
        </p>
        <div className="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="secondary"
            className="p-1 rounded hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDownload(file);
            }}
            aria-label="Download"
          >
            <Download size={14} />
          </Button>
          <Button
            variant="danger"
            className="p-1 rounded hover:bg-error-100 dark:hover:bg-error-900/30 text-error-500"
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(file);
            }}
            aria-label="Delete"
          >
            <Trash2 size={14} />
          </Button>
        </div>
      </div>
    );
  }

  // List view
  return (
    <div
      data-testid={`file-row-${file.id}`}
      className={cn(
        "flex items-center gap-4 px-4 py-3",
        "bg-white dark:bg-neutral-800",
        "border-b border-neutral-200 dark:border-neutral-700",
        "hover:bg-neutral-50 dark:hover:bg-neutral-700/50",
        "transition-colors cursor-pointer",
        "group",
      )}
      onClick={() => onPreview(file)}
    >
      {getFileIcon(file.type)}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-900 dark:text-white truncate">
          {file.name}
        </p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          {formatFileSize(file.size)} • {formatDate(file.updatedAt)}
        </p>
      </div>
      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="secondary"
          className="p-2 rounded hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onPreview(file);
          }}
          aria-label="Preview"
        >
          <Eye size={16} />
        </Button>
        <Button
          variant="secondary"
          className="p-2 rounded hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDownload(file);
          }}
          aria-label="Download"
        >
          <Download size={16} />
        </Button>
        <Button
          variant="danger"
          className="p-2 rounded hover:bg-error-100 dark:hover:bg-error-900/30 text-error-500"
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(file);
          }}
          aria-label="Delete"
        >
          <Trash2 size={16} />
        </Button>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ArtifactsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [previewArtifact, setPreviewArtifact] = useState<CanvasArtifact | null>(
    null,
  );
  const [deleteConfirmFile, setDeleteConfirmFile] = useState<FileItem | null>(
    null,
  );
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteStatus, setDeleteStatus] = useState<
    "idle" | "pending" | "success" | "error"
  >("idle");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Optimistic delete: Track files being deleted for immediate UI update
  const [optimisticDeletedIds, setOptimisticDeletedIds] = useState<Set<string>>(
    new Set(),
  );

  // Get artifacts from the router loader
  const loaderData = useRouteLoaderData("artifacts") as
    | ArtifactsLoaderData
    | undefined;
  const revalidator = useRevalidator();
  const navigate = useNavigate();

  // Auth failure handler for authenticatedFetch
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // Keep track of artifacts for preview lookup
  const artifactsMap = useMemo(() => {
    const map = new Map<string, CanvasArtifact>();
    loaderData?.artifacts?.forEach((a) => map.set(a.id, a));
    return map;
  }, [loaderData?.artifacts]);

  // Convert artifacts to FileItem format
  const files = useMemo(() => {
    if (!loaderData?.artifacts) return [];
    return loaderData.artifacts.map(artifactToFileItem);
  }, [loaderData?.artifacts]);

  // Filter files based on search query and optimistic deletes
  const filteredFiles = useMemo(() => {
    // First filter out optimistically deleted files
    let result = files.filter((file) => !optimisticDeletedIds.has(file.id));

    // Then apply search query filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (file) =>
          file.name.toLowerCase().includes(query) ||
          file.type.toLowerCase().includes(query),
      );
    }

    return result;
  }, [searchQuery, files, optimisticDeletedIds]);

  // Open preview modal with artifact content
  const handlePreview = useCallback(
    (file: FileItem) => {
      setSelectedFile(file);
      const artifact = artifactsMap.get(file.id);
      if (artifact) {
        setPreviewArtifact(artifact);
      }
    },
    [artifactsMap],
  );

  // Close preview modal
  const handleClosePreview = useCallback(() => {
    setSelectedFile(null);
    setPreviewArtifact(null);
  }, []);

  // Download file as blob
  const handleDownload = useCallback(
    (file: FileItem) => {
      const artifact = artifactsMap.get(file.id);
      if (!artifact?.content) {
        logger.warn("Cannot download file: no content", file.id);
        return;
      }

      // Create a blob from the artifact content
      const blob = new Blob([artifact.content], {
        type: file.mimeType ?? "text/plain",
      });
      const url = URL.createObjectURL(blob);

      // Create a temporary link and trigger download
      const link = document.createElement("a");
      link.href = url;
      link.download = file.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up the blob URL
      URL.revokeObjectURL(url);
      logger.debug("Downloaded file:", file.name);
    },
    [artifactsMap],
  );

  // Show delete confirmation
  const handleDeleteClick = useCallback((file: FileItem) => {
    setDeleteConfirmFile(file);
  }, []);

  // Cancel delete confirmation
  const handleCancelDelete = useCallback(() => {
    setDeleteConfirmFile(null);
  }, []);

  // Confirm and execute delete with optimistic update
  const handleConfirmDelete = useCallback(async () => {
    if (!deleteConfirmFile) return;

    const fileToDelete = deleteConfirmFile;
    const startTime = Date.now();

    // Optimistic update: Immediately hide the file from UI
    setOptimisticDeletedIds((prev) => new Set([...prev, fileToDelete.id]));
    setDeleteStatus("pending");
    setDeleteError(null);
    setIsDeleting(true);
    setDeleteConfirmFile(null); // Close dialog immediately

    try {
      const response = await authenticatedFetch(
        `/api/v1/artifacts/${fileToDelete.id}`,
        {
          method: "DELETE",
          onAuthFailure: handleAuthFailure,
        },
      );

      if (response.ok) {
        logger.debug("Deleted file:", fileToDelete.name);
        sessionTelemetry.trackArtifactDelete({
          artifactId: fileToDelete.id,
          success: true,
          durationMs: Date.now() - startTime,
        });
        setDeleteStatus("success");

        // Clear optimistic state and revalidate
        setOptimisticDeletedIds((prev) => {
          const next = new Set(prev);
          next.delete(fileToDelete.id);
          return next;
        });
        revalidator.revalidate();

        // Auto-dismiss success after 2 seconds
        setTimeout(() => setDeleteStatus("idle"), 2000);
      } else {
        const errorMsg = `HTTP ${response.status}: ${response.statusText}`;
        logger.error("Failed to delete file:", response.status);
        sessionTelemetry.trackArtifactDelete({
          artifactId: fileToDelete.id,
          success: false,
          durationMs: Date.now() - startTime,
          error: errorMsg,
        });

        // Rollback: Restore the file in the UI
        setOptimisticDeletedIds((prev) => {
          const next = new Set(prev);
          next.delete(fileToDelete.id);
          return next;
        });
        setDeleteStatus("error");
        setDeleteError(errorMsg);

        // Auto-dismiss error after 5 seconds
        setTimeout(() => {
          setDeleteStatus("idle");
          setDeleteError(null);
        }, 5000);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Unknown error";
      logger.error("Delete request failed:", error);
      sessionTelemetry.trackArtifactDelete({
        artifactId: fileToDelete.id,
        success: false,
        durationMs: Date.now() - startTime,
        error: errorMsg,
      });

      // Rollback: Restore the file in the UI
      setOptimisticDeletedIds((prev) => {
        const next = new Set(prev);
        next.delete(fileToDelete.id);
        return next;
      });
      setDeleteStatus("error");
      setDeleteError(errorMsg);

      // Auto-dismiss error after 5 seconds
      setTimeout(() => {
        setDeleteStatus("idle");
        setDeleteError(null);
      }, 5000);
    } finally {
      setIsDeleting(false);
    }
  }, [deleteConfirmFile, revalidator, handleAuthFailure]);

  // Show error state if loader failed
  if (loaderData?.error) {
    return (
      <div
        data-testid="artifacts-page-error"
        className="flex flex-col items-center justify-center h-full bg-neutral-50 dark:bg-neutral-900 text-neutral-500 dark:text-neutral-400"
      >
        <AlertCircle size={48} className="mb-4 text-error-500" />
        <p className="text-lg font-medium text-neutral-900 dark:text-white">
          Failed to load artifacts
        </p>
        <p className="text-sm mt-1">{loaderData.error}</p>
      </div>
    );
  }

  return (
    <div
      data-testid="artifacts-page"
      className="flex flex-col h-full bg-neutral-50 dark:bg-neutral-900 relative"
    >
      {/* Delete status indicator - optimistic feedback */}
      {deleteStatus !== "idle" && (
        <div
          data-testid="delete-status-indicator"
          className={cn(
            "absolute top-2 right-2 z-20 px-3 py-1.5 rounded-lg text-sm font-medium",
            "transition-all duration-200 shadow-lg",
            deleteStatus === "pending" &&
              "bg-warning-100 dark:bg-warning-900/50 text-warning-700 dark:text-warning-300",
            deleteStatus === "success" &&
              "bg-success-100 dark:bg-success-900/50 text-success-700 dark:text-success-300",
            deleteStatus === "error" &&
              "bg-error-100 dark:bg-error-900/50 text-error-700 dark:text-error-300",
          )}
        >
          {deleteStatus === "pending" && (
            <span className="flex items-center gap-1.5">
              <span className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
              Deleting...
            </span>
          )}
          {deleteStatus === "success" && "Deleted!"}
          {deleteStatus === "error" && (deleteError || "Delete failed")}
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800">
        <div className="flex items-center gap-3">
          <FolderOpen size={24} className="text-primary-500" />
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-white">
            Artifacts
          </h1>
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {filteredFiles.length} artifacts
          </span>
        </div>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
            />
            <Input
              data-testid="file-search"
              placeholder="Search artifacts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                "pl-9 pr-4 py-2 rounded-lg text-sm w-64",
                "bg-neutral-100 dark:bg-neutral-700",
                "border border-neutral-200 dark:border-neutral-700 dark:border-neutral-600",
                "focus:outline-none focus:ring-2 focus:ring-primary-500",
                "placeholder-neutral-400",
              )}
            />
          </div>

          {/* View toggle */}
          <div className="flex items-center gap-1 p-1 bg-neutral-100 dark:bg-neutral-700 rounded-lg">
            <Button
              type="button"
              data-testid="view-grid"
              onClick={() => setViewMode("grid")}
              className={cn(
                "p-1.5 rounded",
                viewMode === "grid"
                  ? "bg-white dark:bg-neutral-600 shadow-sm"
                  : "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:hover:text-neutral-300",
              )}
              aria-label="Grid view"
            >
              <Grid size={16} />
            </Button>
            <Button
              type="button"
              data-testid="view-list"
              onClick={() => setViewMode("list")}
              className={cn(
                "p-1.5 rounded",
                viewMode === "list"
                  ? "bg-white dark:bg-neutral-600 shadow-sm"
                  : "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:hover:text-neutral-300",
              )}
              aria-label="List view"
            >
              <List size={16} />
            </Button>
          </div>
        </div>
      </div>
      {/* File list */}
      <div className="flex-1 overflow-auto p-6">
        {filteredFiles.length === 0 ? (
          // Empty state - AI-enhanced (Sprint 3 Migration)
          <AIEmptyState
            context="artifacts"
            emptyType={searchQuery ? "no-matches" : "empty"}
            searchQuery={searchQuery || undefined}
            variant="compact"
            enableAI={!searchQuery}
          />
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {filteredFiles.map((file) => (
              <FileCard
                key={file.id}
                file={file}
                viewMode={viewMode}
                onPreview={handlePreview}
                onDownload={handleDownload}
                onDelete={handleDeleteClick}
              />
            ))}
          </div>
        ) : (
          <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
            {filteredFiles.map((file) => (
              <FileCard
                key={file.id}
                file={file}
                viewMode={viewMode}
                onPreview={handlePreview}
                onDownload={handleDownload}
                onDelete={handleDeleteClick}
              />
            ))}
          </div>
        )}
      </div>
      {/* Preview Modal */}
      {previewArtifact && selectedFile && (
        <div
          data-testid="preview-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={handleClosePreview}
        >
          <div
            className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden m-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center gap-3">
                {getFileIcon(selectedFile.type)}
                <div>
                  <h3 className="font-medium text-neutral-900 dark:text-white">
                    {selectedFile.name}
                  </h3>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">
                    {formatFileSize(selectedFile.size)} •{" "}
                    {formatDate(selectedFile.updatedAt)}
                  </p>
                </div>
              </div>
              <Button
                variant="secondary"
                className="p-2 rounded hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
                type="button"
                onClick={handleClosePreview}
                aria-label="Close preview"
              >
                <X size={20} />
              </Button>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              <pre className="text-sm font-mono whitespace-pre-wrap text-neutral-800 dark:text-neutral-200 bg-neutral-50 dark:bg-neutral-900 p-4 rounded">
                {previewArtifact.content}
              </pre>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-neutral-200 dark:border-neutral-700">
              <Button
                variant="primary"
                className="flex px-4 py-2 text-sm rounded-lg bg-primary-500 text-white hover:bg-primary-600"
                type="button"
                onClick={() => handleDownload(selectedFile)}
              >
                <Download size={16} />
                Download
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* Delete Confirmation Modal */}
      {deleteConfirmFile && (
        <div
          data-testid="delete-confirm-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={handleCancelDelete}
        >
          <div
            className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full m-4 p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-medium text-neutral-900 dark:text-white mb-2">
              Delete File
            </h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
              Are you sure you want to delete{" "}
              <span className="font-medium">{deleteConfirmFile.name}</span>?
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                className="px-4 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700"
                type="button"
                onClick={handleCancelDelete}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                className="px-4 py-2 text-sm rounded-lg bg-error-500 text-white hover:bg-error-600"
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
