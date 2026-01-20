/**
 * AttachmentPreviews Component
 *
 * Slack-style attachment preview chips that appear above the chat input.
 * Features:
 * - File preview chips with type-specific icons
 * - URL preview chips for fetched URLs
 * - Remove button on each chip
 * - Loading states for uploading files and fetching URLs
 * - Horizontal scroll with overflow
 * - Truncated filenames with full name on hover
 * - WCAG 2.1 AA accessibility compliance
 */

import { Paperclip, Image, FileText, Link2, X, Loader2 } from "lucide-react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { cn } from "../../utils/cn";
import { chipVariants } from "../../design-system/micro-interactions";

// =============================================================================
// Types
// =============================================================================

// Import and re-export UploadFile from useFileUpload for consistency
import type { UploadFile } from "../../hooks/useFileUpload";
export type { UploadFile };

export interface FetchedUrl {
  url: string;
  title?: string;
  content: string;
}

export interface AttachmentPreviewsProps {
  /** Uploaded files to display */
  uploadFiles: UploadFile[];
  /** Callback when a file is removed */
  onRemoveFile: (id: string) => void;
  /** Whether files are currently being uploaded */
  isUploading?: boolean;
  /** Fetched URL content to display */
  fetchedUrls?: FetchedUrl[];
  /** Callback when a fetched URL is removed */
  onRemoveFetchedUrl?: (url: string) => void;
  /** URLs currently being fetched */
  urlFetchLoading?: string[];
}

// =============================================================================
// Helper Functions
// =============================================================================

function getFileIcon(mimeType: string): React.ElementType {
  if (mimeType.startsWith("image/")) {
    return Image;
  }
  if (
    mimeType === "application/pdf" ||
    mimeType.includes("document") ||
    mimeType.includes("text/")
  ) {
    return FileText;
  }
  return Paperclip;
}

function getIconTestId(mimeType: string): string {
  if (mimeType.startsWith("image/")) {
    return "image-icon";
  }
  return "file-icon";
}

function extractDomain(url: string): string {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname;
  } catch {
    return url;
  }
}

// =============================================================================
// Component
// =============================================================================

export function AttachmentPreviews({
  uploadFiles,
  onRemoveFile,
  isUploading: _isUploading = false,
  fetchedUrls = [],
  onRemoveFetchedUrl,
  urlFetchLoading = [],
}: AttachmentPreviewsProps) {
  // Respect user's reduced motion preference for WCAG 2.2 AA compliance
  const prefersReducedMotion = useReducedMotion();

  // Note: isUploading prop reserved for future loading state UI

  // Don't render if nothing to show
  const hasContent = uploadFiles.length > 0 || fetchedUrls.length > 0 || urlFetchLoading.length > 0;

  if (!hasContent) {
    return null;
  }

  return (
    <div
      data-testid="attachment-previews"
      className={cn(
        "flex gap-2 overflow-x-auto pb-2",
        "scrollbar-thin scrollbar-thumb-neutral-5 dark:scrollbar-thumb-neutral-6"
      )}
    >
      <AnimatePresence mode="popLayout">
        {/* File chips */}
        {uploadFiles.map((uploadFile) => {
          const fileName = uploadFile.file.name;
          const fileType = uploadFile.file.type;
          const Icon = getFileIcon(fileType);
          const iconTestId = getIconTestId(fileType);
          const isUploading = uploadFile.status === "uploading";

          return (
            <motion.div
              key={uploadFile.id}
              data-testid={`file-chip-${uploadFile.id}`}
              variants={prefersReducedMotion ? undefined : chipVariants}
              initial={prefersReducedMotion ? undefined : "hidden"}
              animate={prefersReducedMotion ? undefined : "visible"}
              exit={prefersReducedMotion ? undefined : "exit"}
              layout={prefersReducedMotion ? false : true}
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1",
                "bg-neutral-3",
                "border border-neutral-6",
                "rounded-full text-sm whitespace-nowrap",
                "shrink-0"
              )}
            >
              {isUploading ? (
                <Loader2
                  className="w-3.5 h-3.5 text-neutral-10 animate-spin"
                  data-testid="uploading-indicator"
                />
              ) : (
                <Icon
                  className="w-3.5 h-3.5 text-neutral-10"
                  data-testid={iconTestId}
                />
              )}
              <span
                className="max-w-[120px] truncate text-neutral-11"
                title={fileName}
              >
                {fileName}
              </span>
              {/* eslint-disable-next-line react/forbid-elements -- Icon-only close button works best with native button */}
              <button
                type="button"
                onClick={() => onRemoveFile(uploadFile.id)}
                aria-label={`Remove ${fileName}`}
                className={cn(
                  "p-0.5 rounded-full",
                  "text-neutral-9 hover:text-neutral-11",
                  "hover:bg-neutral-5",
                  "transition-colors"
                )}
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          );
        })}

        {/* URL loading chips */}
        {urlFetchLoading.map((url) => (
          <motion.div
            key={`loading-${url}`}
            data-testid="url-loading-chip"
            variants={prefersReducedMotion ? undefined : chipVariants}
            initial={prefersReducedMotion ? undefined : "hidden"}
            animate={prefersReducedMotion ? undefined : "visible"}
            exit={prefersReducedMotion ? undefined : "exit"}
            layout={prefersReducedMotion ? false : true}
            className={cn(
              "inline-flex items-center gap-1.5 px-2.5 py-1",
              "bg-neutral-3",
              "border border-neutral-6",
              "rounded-full text-sm whitespace-nowrap",
              "shrink-0"
            )}
          >
            <Loader2 className="w-3.5 h-3.5 text-neutral-10 animate-spin" />
            <span className="max-w-[120px] truncate text-neutral-10">
              {extractDomain(url)}
            </span>
          </motion.div>
        ))}

        {/* Fetched URL chips */}
        {fetchedUrls.map((fetchedUrl) => {
          const displayName = fetchedUrl.title || extractDomain(fetchedUrl.url);

          return (
            <motion.div
              key={fetchedUrl.url}
              data-testid={`url-chip-${encodeURIComponent(fetchedUrl.url)}`}
              variants={prefersReducedMotion ? undefined : chipVariants}
              initial={prefersReducedMotion ? undefined : "hidden"}
              animate={prefersReducedMotion ? undefined : "visible"}
              exit={prefersReducedMotion ? undefined : "exit"}
              layout={prefersReducedMotion ? false : true}
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1",
                "bg-neutral-3",
                "border border-neutral-6",
                "rounded-full text-sm whitespace-nowrap",
                "shrink-0"
              )}
            >
              <Link2
                className="w-3.5 h-3.5 text-neutral-10"
                data-testid="link-icon"
              />
              <span
                className="max-w-[120px] truncate text-neutral-11"
                title={fetchedUrl.url}
              >
                {displayName}
              </span>
              {onRemoveFetchedUrl && (
                // eslint-disable-next-line react/forbid-elements -- Icon-only close button works best with native button
                <button
                  type="button"
                  onClick={() => onRemoveFetchedUrl(fetchedUrl.url)}
                  aria-label={`Remove ${displayName}`}
                  className={cn(
                    "p-0.5 rounded-full",
                    "text-neutral-9 hover:text-neutral-11",
                    "hover:bg-neutral-5",
                    "transition-colors"
                  )}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export default AttachmentPreviews;
