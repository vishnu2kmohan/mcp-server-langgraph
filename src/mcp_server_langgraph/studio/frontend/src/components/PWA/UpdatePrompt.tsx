/**
 * PWA Update Prompt Component
 *
 * Shows a toast notification when a new service worker version is available.
 * Allows users to update immediately or dismiss for later.
 */

import { RefreshCw, X } from "lucide-react";

import { Button } from "@/components/UI";

export interface UpdatePromptProps {
  /** Whether a new version is available */
  needsUpdate: boolean;
  /** Whether the update is in progress */
  isUpdating: boolean;
  /** Callback when user clicks update */
  onUpdate: () => void;
  /** Callback when user dismisses the prompt */
  onDismiss: () => void;
}

/**
 * Toast notification for PWA updates.
 *
 * @example
 * ```tsx
 * const { needsUpdate, isUpdating, updateApp, dismissUpdate } = usePWAUpdate();
 *
 * return (
 *   <UpdatePrompt
 *     needsUpdate={needsUpdate}
 *     isUpdating={isUpdating}
 *     onUpdate={updateApp}
 *     onDismiss={dismissUpdate}
 *   />
 * );
 * ```
 */
export function UpdatePrompt({
  needsUpdate,
  isUpdating,
  onUpdate,
  onDismiss,
}: UpdatePromptProps) {
  if (!needsUpdate) {
    return null;
  }

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[70] bg-primary-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-md"
    >
      <RefreshCw
        className={`h-5 w-5 flex-shrink-0 ${isUpdating ? "animate-spin" : ""}`}
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">
          {isUpdating ? "Updating application..." : "New version available"}
        </p>
        {!isUpdating && (
          <p className="text-xs text-primary-100 mt-0.5">
            Click update to get the latest features
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          variant="primary"
          className="px-3 py-1.5 text-sm bg-white text-primary-600 rounded hover:bg-primary-50"
          type="button"
          onClick={onUpdate}
          disabled={isUpdating}
          aria-label="Update application now"
        >
          Update
        </Button>
        <Button
          variant="primary"
          className="p-1.5 text-primary-100 hover:text-white hover:bg-primary-700 rounded"
          type="button"
          onClick={onDismiss}
          disabled={isUpdating}
          aria-label="Remind me later"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          <span className="sr-only">Later</span>
        </Button>
      </div>
    </div>
  );
}

export default UpdatePrompt;
