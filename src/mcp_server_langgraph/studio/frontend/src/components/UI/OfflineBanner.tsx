/**
 * OfflineBanner Component
 *
 * Displays a warning banner when the user is offline.
 * Used for PWA offline support to provide feedback about connectivity status.
 */

import { WifiOff } from "lucide-react";
import { useOffline } from "../../hooks/useOffline";

export function OfflineBanner() {
  const isOffline = useOffline();

  if (!isOffline) {
    return null;
  }

  return (
    <div
      data-testid="offline-banner"
      role="alert"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 w-full z-[70] bg-yellow-500 text-yellow-900 px-4 py-2 flex items-center justify-center gap-2 shadow-md"
    >
      <WifiOff size={18} data-testid="wifi-off-icon" />
      <span className="font-medium">
        You are currently offline. Some features may be unavailable.
      </span>
    </div>
  );
}

export default OfflineBanner;
