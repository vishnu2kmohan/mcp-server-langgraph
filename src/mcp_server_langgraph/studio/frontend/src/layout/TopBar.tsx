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
import { useReducedMotion } from "motion/react";
import { useAppSelector } from "../store/hooks";
import { selectPersona, selectUsername } from "../store/slices/personaSlice";
import { cn } from "../utils/cn";
import { UserMenuDropdown } from "./UserMenuDropdown";
import { AlertBadge } from "./AlertBadge";
import { Breadcrumb } from "./Breadcrumb";
import type { BreadcrumbItem } from "../hooks/useBreadcrumb";

import { Button, Badge } from "@/components/UI";

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
 * Get Badge variant for persona
 */
function getPersonaBadgeVariant(
  persona: string,
): "error" | "primary" | "default" {
  switch (persona) {
    case "admin":
      return "error";
    case "developer":
      return "primary";
    case "user":
    default:
      return "default";
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

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
        "bg-neutral-1",
        "border-b border-neutral-5",
        className,
      )}
    >
      {/* Left: App branding with optional section breadcrumb - flex-1 to use available space */}
      <div
        data-testid="app-branding"
        className="flex-1 min-w-0 flex items-center gap-3"
      >
        <span className="font-semibold text-neutral-12 whitespace-nowrap">
          {title}
        </span>

        {/* Prefer breadcrumbItems for deeper navigation, fallback to sectionTitle */}
        {breadcrumbItems && breadcrumbItems.length > 0 ? (
          <>
            <span
              data-testid="section-separator"
              className="text-neutral-9"
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
              className="text-neutral-9"
              aria-hidden="true"
            >
              /
            </span>
            <span
              data-testid="section-title"
              className="text-sm font-medium text-neutral-11 truncate"
            >
              {sectionTitle}
            </span>
          </nav>
        ) : null}

        {subPersonaBadge && (
          <Badge
            data-testid="sub-persona-badge"
            size="sm"
            pill
            className="ml-1 whitespace-nowrap bg-insight-2 text-insight-11"
          >
            {subPersonaBadge}
          </Badge>
        )}
      </div>
      {/* Right: User info and menu - flex-shrink-0 to prevent compression */}
      <div className="flex-shrink-0 flex items-center gap-3">
        {/* Username - hidden on small screens */}
        {username && (
          <span className="hidden sm:inline truncate max-w-24 text-sm text-neutral-11">
            {username}
          </span>
        )}

        {/* Persona badge */}
        <Badge
          data-testid="persona-badge"
          variant={getPersonaBadgeVariant(persona)}
          size="sm"
          pill
          className="capitalize"
        >
          {persona}
        </Badge>

        {/* Alert badge (Admin only) */}
        {persona === "admin" && onAlertClick && (
          <AlertBadge onClick={onAlertClick} />
        )}

        {/* Pending approvals badge (all personas) */}
        {pendingApprovals !== undefined &&
          pendingApprovals > 0 &&
          onPendingApprovalsClick && (
            <Button
              data-testid="review-approval-button"
              type="button"
              variant="ghost"
              size="sm"
              onClick={onPendingApprovalsClick}
              aria-label={`${pendingApprovals} pending agent approval${pendingApprovals === 1 ? "" : "s"}`}
              className={cn(
                "relative flex items-center gap-1",
                "bg-warning-3 hover:bg-warning-4",
                !prefersReducedMotion && "transition-colors",
              )}
            >
              <UserCheck
                size={14}
                className="text-warning-11"
                aria-hidden="true"
              />
              <span className="font-medium text-xs text-warning-11">
                {pendingApprovals}
              </span>
            </Button>
          )}

        {/* User avatar/menu trigger with dropdown */}
        <div className="relative">
          <Button
            ref={avatarRef}
            type="button"
            variant="primary"
            data-testid="user-avatar"
            aria-label={`User menu for ${username ?? "unknown user"}`}
            aria-expanded={isDropdownOpen}
            aria-haspopup="menu"
            onClick={handleAvatarClick}
            className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center",
              "font-medium text-sm",
              !prefersReducedMotion && "transition-colors",
            )}
          >
            {avatarLetter}
          </Button>

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
