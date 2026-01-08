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
import { Breadcrumb } from "./Breadcrumb";
import type { BreadcrumbItem } from "../hooks/useBreadcrumb";

// =============================================================================
// Types
// =============================================================================

export interface TopBarProps {
  /** Custom title (default: "Agent Studio") */
  title?: string;
  /**
   * Section title derived from current route (Sprint 2.3 - Wayfinding)
   * @deprecated Use `breadcrumbItems` instead. This prop is kept for backward compatibility
   * but is no longer used by StudioShellLayout. All routes now use `handle.breadcrumb` metadata.
   */
  sectionTitle?: string;
  /** Breadcrumb items for deeper navigation hierarchy (Sprint 2.3 - Phase 2) */
  breadcrumbItems?: BreadcrumbItem[];
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
      return "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300";
    case "developer":
      return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300";
    case "user":
    default:
      return "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300";
  }
}

// =============================================================================
// Component
// =============================================================================

export function TopBar({
  title = "Agent Studio",
  sectionTitle,
  breadcrumbItems,
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
        "flex items-center gap-4 px-4 py-2",
        "bg-white dark:bg-gray-800",
        "border-b border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Left: App branding with optional section breadcrumb - flex-1 to use available space */}
      <div
        data-testid="app-branding"
        className="flex-1 min-w-0 flex items-center gap-3"
      >
        <span className="font-semibold text-gray-900 dark:text-white whitespace-nowrap">
          {title}
        </span>

        {/* Prefer breadcrumbItems for deeper navigation, fallback to sectionTitle */}
        {breadcrumbItems && breadcrumbItems.length > 0 ? (
          <>
            <span
              data-testid="section-separator"
              className="text-gray-300 dark:text-gray-600 dark:text-gray-300"
              aria-hidden="true"
            >
              /
            </span>
            <Breadcrumb items={breadcrumbItems} />
          </>
        ) : sectionTitle ? (
          <nav
            data-testid="breadcrumb-nav"
            aria-label="Breadcrumb"
            className="flex items-center gap-2"
          >
            <span
              data-testid="section-separator"
              className="text-gray-300 dark:text-gray-600 dark:text-gray-300"
              aria-hidden="true"
            >
              /
            </span>
            <span
              data-testid="section-title"
              className="text-sm font-medium text-gray-600 dark:text-gray-300 truncate"
            >
              {sectionTitle}
            </span>
          </nav>
        ) : null}

        {subPersonaBadge && (
          <span
            data-testid="sub-persona-badge"
            className={cn(
              "ml-1 px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap",
              "bg-insight-100 text-insight-700 dark:bg-insight-900/30 dark:text-insight-300",
            )}
          >
            {subPersonaBadge}
          </span>
        )}
      </div>

      {/* Right: User info and menu - flex-shrink-0 to prevent compression */}
      <div className="flex-shrink-0 flex items-center gap-3">
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
                "bg-warning-100 dark:bg-warning-900/30",
                "hover:bg-warning-200 dark:hover:bg-warning-800/50",
                "transition-colors",
              )}
            >
              <UserCheck
                size={14}
                className="text-warning-600 dark:text-warning-400"
                aria-hidden="true"
              />
              <span className="font-medium text-xs text-warning-700 dark:text-warning-300">
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
