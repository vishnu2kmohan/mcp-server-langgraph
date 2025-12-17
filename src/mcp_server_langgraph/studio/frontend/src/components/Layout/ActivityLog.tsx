/**
 * ActivityLog Component
 *
 * Displays a real-time activity feed of notifications and events.
 * Used in the BottomPanel's Activity tab.
 *
 * Features:
 * - Renders notifications from Redux store
 * - Type-based icons and styling (success, error, warning, info)
 * - Timestamp formatting
 * - Configurable max items display
 */

import { CheckCircle, AlertCircle, Info } from "lucide-react";
import { useAppSelector } from "../../store/hooks";
import {
  selectNotifications,
  type Notification,
} from "../../store/slices/notificationSlice";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface ActivityLogProps {
  /** Maximum number of items to display */
  maxItems?: number;
  /** Compact mode with reduced spacing */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Activity Item Component
// =============================================================================

interface ActivityItemRowProps {
  notification: Notification;
  compact?: boolean;
}

function ActivityItemRow({ notification, compact }: ActivityItemRowProps) {
  // Get icon and color based on notification type
  const getIcon = () => {
    switch (notification.type) {
      case "success":
        return (
          <CheckCircle size={compact ? 12 : 14} className="text-green-500" />
        );
      case "warning":
        return (
          <AlertCircle size={compact ? 12 : 14} className="text-yellow-500" />
        );
      case "error":
        return (
          <AlertCircle size={compact ? 12 : 14} className="text-red-500" />
        );
      default:
        return <Info size={compact ? 12 : 14} className="text-blue-500" />;
    }
  };

  // Format timestamp
  const formatTime = (createdAt: string) => {
    const date = new Date(createdAt);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div
      data-testid={`activity-item-${notification.id}`}
      className={cn(
        "flex items-start gap-2 rounded-md",
        compact ? "p-1.5" : "p-2",
        "hover:bg-gray-100 dark:hover:bg-gray-700/50",
        "transition-colors",
      )}
    >
      <span className="flex-shrink-0 mt-0.5">{getIcon()}</span>
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "font-medium text-gray-700 dark:text-gray-200",
            compact ? "text-xs" : "text-sm",
          )}
        >
          {notification.title}
        </p>
        <p
          className={cn(
            "text-gray-500 dark:text-gray-400 truncate",
            compact ? "text-[10px]" : "text-xs",
          )}
        >
          {notification.message}
        </p>
      </div>
      <span
        className={cn(
          "text-gray-400 dark:text-gray-500 flex-shrink-0",
          compact ? "text-[10px]" : "text-xs",
        )}
      >
        {formatTime(notification.createdAt)}
      </span>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ActivityLog({
  maxItems = 10,
  compact = false,
  className,
}: ActivityLogProps) {
  const notifications = useAppSelector(selectNotifications);

  // Limit to maxItems
  const displayedNotifications = notifications.slice(0, maxItems);

  return (
    <div
      data-testid="activity-log"
      className={cn(
        "text-sm text-gray-500 dark:text-gray-400",
        compact ? "p-2" : "p-4",
        className,
      )}
    >
      {displayedNotifications.length === 0 ? (
        <div className="space-y-2">
          <p className="text-xs text-gray-400">No recent activity</p>
        </div>
      ) : (
        <div className={cn("space-y-1", compact && "space-y-0.5")}>
          {displayedNotifications.map((notification) => (
            <ActivityItemRow
              key={notification.id}
              notification={notification}
              compact={compact}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default ActivityLog;
