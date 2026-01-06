/**
 * TopBar Component
 *
 * Minimal header displaying app branding and user info.
 * Persona-aware with user menu trigger.
 *
 * Features:
 * - App branding/title
 * - User avatar with persona badge
 * - User menu dropdown for profile/settings/logout
 * - Alert badge for infrastructure alerts (Admin only)
 * - Dark mode support
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */
import { useState, useCallback, useRef } from "react";
import { UserCheck } from "lucide-react";
import { useAppSelector } from "../store/hooks";
import { selectPersona, selectUsername } from "../store/slices/personaSlice";
import { cn } from "../utils/cn";
import { UserMenuDropdown } from "./UserMenuDropdown";
import { AlertBadge } from "./AlertBadge";

// =============================================================================
// Types
// =============================================================================

export interface TopBarProps {
  /** Custom title (default: "Agent Studio") */
  title?: string;
  /** Section title derived from current route (Sprint 2.3 - Wayfinding) */
  sectionTitle?: string;
  /** Sub-persona badge for more granular role display (Sprint 2.3) */
  subPersonaBadge?: string;
  /** Callback when user menu is triggered */
  onUserMenuClick?: () => void;
  /** Callback when alert badge is clicked (navigates to admin alerts) */
  onAlertClick?: () => void;
  /** Number of pending agent approvals */
  pendingApprovals?: number;
  /** Callback when pending approvals badge is clicked */
  onPendingApprovalsClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get color class for persona badge
 */
function getPersonaBadgeColor(persona: string): string {
  switch (persona) {
    case "admin":
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
    case "developer":
      return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
    case "user":
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
  }
}

// =============================================================================
// Component
// =============================================================================

export function TopBar({
  title = "Agent Studio",
  sectionTitle,
  subPersonaBadge,
  onUserMenuClick,
  onAlertClick,
  pendingApprovals,
  onPendingApprovalsClick,
  className,
}: TopBarProps) {
  const username = useAppSelector(selectUsername);
  const persona = useAppSelector(selectPersona);

  // Dropdown state
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const avatarRef = useRef<HTMLButtonElement>(null);

  // Get first letter of username for avatar
  const avatarLetter = username ? username.charAt(0).toUpperCase() : "?";

  const handleAvatarClick = useCallback(() => {
    setIsDropdownOpen((prev) => !prev);
    onUserMenuClick?.();
  }, [onUserMenuClick]);

  const handleDropdownClose = useCallback(() => {
    setIsDropdownOpen(false);
  }, []);

  return (
    <header
      data-testid="top-bar"
      role="banner"
      className={cn(
        "flex items-center justify-between px-4 py-2",
        "bg-white dark:bg-gray-800",
        "border-b border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Left: App branding with optional section breadcrumb */}
      <div data-testid="app-branding" className="flex items-center gap-2">
        <span className="font-semibold text-gray-900 dark:text-white">
          {title}
        </span>
        {sectionTitle && (
          <>
            <span
              data-testid="section-separator"
              className="text-gray-400 dark:text-gray-500"
              aria-hidden="true"
            >
              /
            </span>
            <span
              data-testid="section-title"
              className="text-sm font-medium text-gray-600 dark:text-gray-300"
            >
              {sectionTitle}
            </span>
          </>
        )}
        {subPersonaBadge && (
          <span
            data-testid="sub-persona-badge"
            className={cn(
              "ml-2 px-2 py-0.5 rounded-full text-xs font-medium",
              "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
            )}
          >
            {subPersonaBadge}
          </span>
        )}
      </div>

      {/* Right: User info and menu */}
      <div className="flex items-center gap-3">
        {/* Username */}
        {username && (
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {username}
          </span>
        )}

        {/* Persona badge */}
        <span
          data-testid="persona-badge"
          className={cn(
            "px-2 py-0.5 rounded-full text-xs font-medium capitalize",
            getPersonaBadgeColor(persona),
          )}
        >
          {persona}
        </span>

        {/* Alert badge (Admin only) */}
        {persona === "admin" && onAlertClick && (
          <AlertBadge onClick={onAlertClick} />
        )}

        {/* Pending approvals badge (all personas) */}
        {pendingApprovals !== undefined &&
          pendingApprovals > 0 &&
          onPendingApprovalsClick && (
            <button
              data-testid="review-approval-button"
              type="button"
              onClick={onPendingApprovalsClick}
              aria-label={`${pendingApprovals} pending agent approval${pendingApprovals === 1 ? "" : "s"}`}
              className={cn(
                "relative flex items-center gap-1 px-2 py-1 rounded",
                "bg-amber-100 dark:bg-amber-900/30",
                "hover:bg-amber-200 dark:hover:bg-amber-800/50",
                "transition-colors",
              )}
            >
              <UserCheck
                size={14}
                className="text-amber-600 dark:text-amber-400"
                aria-hidden="true"
              />
              <span className="font-medium text-xs text-amber-700 dark:text-amber-300">
                {pendingApprovals}
              </span>
            </button>
          )}

        {/* User avatar/menu trigger with dropdown */}
        <div className="relative">
          <button
            ref={avatarRef}
            type="button"
            data-testid="user-avatar"
            aria-label={`User menu for ${username ?? "unknown user"}`}
            aria-expanded={isDropdownOpen}
            aria-haspopup="menu"
            onClick={handleAvatarClick}
            className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center",
              "bg-primary-500 text-white font-medium text-sm",
              "hover:bg-primary-600 transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2",
            )}
          >
            {avatarLetter}
          </button>

          {/* User menu dropdown */}
          <UserMenuDropdown
            isOpen={isDropdownOpen}
            onClose={handleDropdownClose}
            anchorRef={avatarRef}
          />
        </div>
      </div>
    </header>
  );
}
