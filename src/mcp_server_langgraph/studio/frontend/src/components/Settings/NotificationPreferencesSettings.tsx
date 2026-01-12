/**
 * NotificationPreferencesSettings Component
 *
 * Manages user notification preferences via the API.
 * Features:
 * - Toggle individual notification types (info, success, warning, error)
 * - Reset to defaults
 * - Real-time updates via RTK Query
 */

import { RefreshCw, AlertCircle, RotateCcw } from "lucide-react";
import {
  useGetNotificationPreferencesQuery,
  useUpdateNotificationPreferencesMutation,
  useResetNotificationPreferencesMutation,
} from "../../api";

import { Button, Toggle } from "@/components/UI";

interface NotificationTypeToggleProps {
  label: string;
  description: string;
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
}

/**
 * Toggle component for a single notification type
 */
function NotificationTypeToggle({
  label,
  description,
  enabled,
  onChange,
  disabled,
}: NotificationTypeToggleProps) {
  return (
    <div className="flex items-center justify-between p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
      <div>
        <p className="font-medium text-neutral-900 dark:text-neutral-100">
          {label}
        </p>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {description}
        </p>
      </div>
      <Toggle
        checked={enabled}
        onChange={onChange}
        disabled={disabled}
        aria-label={label}
        size="md"
      />
    </div>
  );
}

/**
 * NotificationPreferencesSettings component
 */
export function NotificationPreferencesSettings() {
  const {
    data: preferences,
    isLoading,
    isError,
    refetch,
  } = useGetNotificationPreferencesQuery();

  const [updatePreferences, { isLoading: isUpdating }] =
    useUpdateNotificationPreferencesMutation();

  const [resetPreferences, { isLoading: isResetting }] =
    useResetNotificationPreferencesMutation();

  const handleToggle = async (
    field: "infoEnabled" | "successEnabled" | "warningEnabled" | "errorEnabled",
    enabled: boolean,
  ) => {
    try {
      await updatePreferences({ [field]: enabled });
    } catch (error) {
      console.error("Failed to update preferences:", error);
    }
  };

  const handleReset = async () => {
    try {
      await resetPreferences();
    } catch (error) {
      console.error("Failed to reset preferences:", error);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="preferences-loading"
        className="flex items-center justify-center py-8"
      >
        <RefreshCw size={24} className="animate-spin text-primary-500" />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
        <div className="flex items-center gap-3">
          <AlertCircle size={20} className="text-error-500" />
          <p className="text-sm text-error-700 dark:text-error-400">
            Failed to load notification preferences
          </p>
        </div>
        <Button
          variant="danger"
          className="mt-3 flex px-3 py-1.5 text-sm bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200"
          onClick={() => refetch()}
        >
          <RefreshCw size={14} />
          Retry
        </Button>
      </div>
    );
  }

  const isDisabled = isUpdating || isResetting;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
          Real-Time Notification Types
        </h3>
        <Button
          className="flex px-3 py-1.5 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100"
          onClick={handleReset}
          disabled={isDisabled}
          aria-label="Reset to defaults"
        >
          <RotateCcw size={14} className={isResetting ? "animate-spin" : ""} />
          Reset to Defaults
        </Button>
      </div>
      <NotificationTypeToggle
        label="Info Notifications"
        description="General information and updates"
        enabled={preferences?.infoEnabled ?? true}
        onChange={(enabled) => handleToggle("infoEnabled", enabled)}
        disabled={isDisabled}
      />
      <NotificationTypeToggle
        label="Success Notifications"
        description="Confirmations when operations complete successfully"
        enabled={preferences?.successEnabled ?? true}
        onChange={(enabled) => handleToggle("successEnabled", enabled)}
        disabled={isDisabled}
      />
      <NotificationTypeToggle
        label="Warning Notifications"
        description="Alerts about potential issues or important information"
        enabled={preferences?.warningEnabled ?? true}
        onChange={(enabled) => handleToggle("warningEnabled", enabled)}
        disabled={isDisabled}
      />
      <NotificationTypeToggle
        label="Error Notifications"
        description="Critical errors that require your attention"
        enabled={preferences?.errorEnabled ?? true}
        onChange={(enabled) => handleToggle("errorEnabled", enabled)}
        disabled={isDisabled}
      />
    </div>
  );
}

export default NotificationPreferencesSettings;
