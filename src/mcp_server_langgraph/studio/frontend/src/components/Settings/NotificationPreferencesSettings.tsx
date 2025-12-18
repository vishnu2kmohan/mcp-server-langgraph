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
    <label className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div>
        <p className="font-medium text-gray-900 dark:text-gray-100">{label}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      </div>
      <input
        type="checkbox"
        role="switch"
        aria-label={label}
        checked={enabled}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
      />
    </label>
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
    field:
      | "info_enabled"
      | "success_enabled"
      | "warning_enabled"
      | "error_enabled",
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
        <RefreshCw size={24} className="animate-spin text-blue-500" />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div className="flex items-center gap-3">
          <AlertCircle size={20} className="text-red-500" />
          <p className="text-sm text-red-700 dark:text-red-400">
            Failed to load notification preferences
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="mt-3 flex items-center gap-2 px-3 py-1.5 text-sm bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg hover:bg-red-200"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      </div>
    );
  }

  const isDisabled = isUpdating || isResetting;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Real-Time Notification Types
        </h3>
        <button
          onClick={handleReset}
          disabled={isDisabled}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-50"
          aria-label="Reset to defaults"
        >
          <RotateCcw size={14} className={isResetting ? "animate-spin" : ""} />
          Reset to Defaults
        </button>
      </div>

      <NotificationTypeToggle
        label="Info Notifications"
        description="General information and updates"
        enabled={preferences?.info_enabled ?? true}
        onChange={(enabled) => handleToggle("info_enabled", enabled)}
        disabled={isDisabled}
      />

      <NotificationTypeToggle
        label="Success Notifications"
        description="Confirmations when operations complete successfully"
        enabled={preferences?.success_enabled ?? true}
        onChange={(enabled) => handleToggle("success_enabled", enabled)}
        disabled={isDisabled}
      />

      <NotificationTypeToggle
        label="Warning Notifications"
        description="Alerts about potential issues or important information"
        enabled={preferences?.warning_enabled ?? true}
        onChange={(enabled) => handleToggle("warning_enabled", enabled)}
        disabled={isDisabled}
      />

      <NotificationTypeToggle
        label="Error Notifications"
        description="Critical errors that require your attention"
        enabled={preferences?.error_enabled ?? true}
        onChange={(enabled) => handleToggle("error_enabled", enabled)}
        disabled={isDisabled}
      />
    </div>
  );
}

export default NotificationPreferencesSettings;
