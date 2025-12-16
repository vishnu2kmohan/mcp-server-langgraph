/**
 * NotificationBell Component
 *
 * Bell icon with dropdown panel for notifications.
 * Features:
 * - Bell icon with unread count badge
 * - Dropdown panel with notification list
 * - Mark as read / Mark all as read
 * - Remove individual notifications
 * - Navigate to notification action
 * - Type-specific icons (info, success, warning, error)
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import {
  Bell,
  Info,
  CheckCircle,
  AlertTriangle,
  XCircle,
  X,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectNotifications,
  selectUnreadCount,
  markAsRead,
  markAllAsRead,
  removeNotification,
  type Notification,
  type NotificationType,
} from "../../store/slices/notificationSlice";

/**
 * Get icon for notification type
 */
function getNotificationIcon(type: NotificationType) {
  const iconProps = { size: 16 };

  switch (type) {
    case "info":
      return (
        <Info
          {...iconProps}
          className="text-blue-500"
          data-testid="notification-icon-info"
        />
      );
    case "success":
      return (
        <CheckCircle
          {...iconProps}
          className="text-green-500"
          data-testid="notification-icon-success"
        />
      );
    case "warning":
      return (
        <AlertTriangle
          {...iconProps}
          className="text-yellow-500"
          data-testid="notification-icon-warning"
        />
      );
    case "error":
      return (
        <XCircle
          {...iconProps}
          className="text-red-500"
          data-testid="notification-icon-error"
        />
      );
    default:
      return <Info {...iconProps} className="text-gray-500" />;
  }
}

/**
 * Format relative time (e.g., "2 minutes ago")
 */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

/**
 * NotificationBell component
 */
export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const notifications = useAppSelector(selectNotifications);
  const unreadCount = useAppSelector(selectUnreadCount);

  // Format badge text (9+ for more than 9)
  const badgeText = unreadCount > 9 ? "9+" : unreadCount.toString();

  // Handle click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        isOpen &&
        panelRef.current &&
        buttonRef.current &&
        !panelRef.current.contains(event.target as Node) &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Handle notification click (mark as read)
  const handleNotificationClick = useCallback(
    (notification: Notification) => {
      if (!notification.read) {
        dispatch(markAsRead(notification.id));
      }
    },
    [dispatch],
  );

  // Handle action button click
  const handleActionClick = useCallback(
    (notification: Notification, e: React.MouseEvent) => {
      e.stopPropagation();
      if (notification.action?.href) {
        navigate(notification.action.href);
        setIsOpen(false);
      }
      if (notification.action?.onClick) {
        notification.action.onClick();
      }
    },
    [navigate],
  );

  // Handle remove notification
  const handleRemove = useCallback(
    (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      dispatch(removeNotification(id));
    },
    [dispatch],
  );

  // Handle mark all as read
  const handleMarkAllAsRead = useCallback(() => {
    dispatch(markAllAsRead());
  }, [dispatch]);

  return (
    <div className="relative">
      {/* Bell Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        aria-label="Notifications"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Bell size={20} />

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 text-xs font-bold text-white bg-red-500 rounded-full">
            {badgeText}
          </span>
        )}
      </button>

      {/* Dropdown Panel - positioned above the bell to avoid occlusion in sidebar */}
      {isOpen && (
        <div
          ref={panelRef}
          role="menu"
          className="absolute left-0 bottom-full mb-2 w-80 max-h-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden z-[60]"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllAsRead}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                aria-label="Mark all as read"
              >
                Mark all as read
              </button>
            )}
          </div>

          {/* Notification List */}
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                No notifications
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  role="menuitem"
                  tabIndex={0}
                  onClick={() => handleNotificationClick(notification)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      handleNotificationClick(notification);
                    }
                  }}
                  className={`w-full text-left px-4 py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer ${
                    !notification.read
                      ? "bg-blue-50/50 dark:bg-blue-900/10"
                      : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Icon */}
                    <div className="flex-shrink-0 mt-0.5">
                      {getNotificationIcon(notification.type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {notification.title}
                          </span>
                          {!notification.read && (
                            <span
                              data-testid="unread-indicator"
                              className="w-2 h-2 rounded-full bg-blue-500"
                            />
                          )}
                        </div>

                        {/* Remove button */}
                        <button
                          onClick={(e) => handleRemove(notification.id, e)}
                          className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                          aria-label="Remove notification"
                        >
                          <X size={14} />
                        </button>
                      </div>

                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-2">
                        {notification.message}
                      </p>

                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs text-gray-400">
                          {formatRelativeTime(notification.createdAt)}
                        </span>

                        {notification.action && (
                          <button
                            onClick={(e) => handleActionClick(notification, e)}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            {notification.action.label}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
