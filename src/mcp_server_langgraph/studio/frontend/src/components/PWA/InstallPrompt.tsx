/**
 * PWA Install Prompt Component
 *
 * Shows a toast notification when the PWA can be installed.
 * Allows users to install the app or dismiss for later.
 */

import { Download, X } from "lucide-react";

import { Button } from "@/components/UI";

export interface InstallPromptProps {
  /** Whether the app can be installed */
  canInstall: boolean;
  /** Whether installation is in progress */
  isInstalling: boolean;
  /** Callback when user clicks install */
  onInstall: () => void;
  /** Callback when user dismisses the prompt */
  onDismiss: () => void;
}

/**
 * Toast notification for PWA installation.
 *
 * @example
 * ```tsx
 * const { canInstall, isInstalling, installApp, dismissInstall } = usePWAInstall();
 *
 * return (
 *   <InstallPrompt
 *     canInstall={canInstall}
 *     isInstalling={isInstalling}
 *     onInstall={installApp}
 *     onDismiss={dismissInstall}
 *   />
 * );
 * ```
 */
export function InstallPrompt({
  canInstall,
  isInstalling,
  onInstall,
  onDismiss,
}: InstallPromptProps) {
  if (!canInstall) {
    return null;
  }

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[70] bg-emerald-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-md"
    >
      <Download
        className={`h-5 w-5 flex-shrink-0 ${isInstalling ? "animate-bounce" : ""}`}
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">
          {isInstalling ? "Installing app..." : "Install this app"}
        </p>
        {!isInstalling && (
          <p className="text-xs text-emerald-100 mt-0.5">
            Get faster access and offline support
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          variant="secondary"
          className="px-3 py-1.5 text-sm bg-white text-emerald-600 rounded hover:bg-emerald-50"
          type="button"
          onClick={onInstall}
          disabled={isInstalling}
          aria-label="Install app now"
        >
          Install
        </Button>
        <Button
          className="p-1.5 text-emerald-100 hover:text-white hover:bg-emerald-700 rounded"
          type="button"
          onClick={onDismiss}
          disabled={isInstalling}
          aria-label="No thanks, maybe later"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          <span className="sr-only">No thanks</span>
        </Button>
      </div>
    </div>
  );
}

export default InstallPrompt;
