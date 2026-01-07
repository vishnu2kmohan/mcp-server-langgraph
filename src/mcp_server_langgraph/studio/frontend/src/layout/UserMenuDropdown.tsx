/**
 * UserMenuDropdown Component
 *
 * Dropdown menu triggered from user avatar in TopBar.
 * Provides access to profile, settings, persona switching, and logout.
 */
import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  User,
  Settings,
  LogOut,
  Users,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectUsername,
  selectPersona,
  setSubPersona,
  resetPersona,
  type SubPersona,
} from "../store/slices/personaSlice";
import { logout } from "../store/slices/authSlice";
import { cn } from "../utils/cn";
import { storage, STORAGE_KEYS } from "../utils/storage";
import { transformSnakeToCamel } from "../api/transforms";

// =============================================================================
// Types
// =============================================================================

export interface UserMenuDropdownProps {
  /** Whether the dropdown is open */
  isOpen: boolean;
  /** Callback to close the dropdown */
  onClose: () => void;
  /** Anchor element position (for positioning) */
  anchorRef?: React.RefObject<HTMLElement>;
  /** Additional class name */
  className?: string;
}

interface MenuItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
}

// =============================================================================
// Sub-Persona Options
// =============================================================================

const SUB_PERSONA_OPTIONS: { id: SubPersona; label: string }[] = [
  { id: "admin", label: "Admin" },
  { id: "security-admin", label: "Security Admin" },
  { id: "auditor", label: "Auditor" },
  { id: "alice-builder", label: "Alice Builder" },
  { id: "alice-analyst", label: "Alice Analyst" },
  { id: "alice-devops", label: "Alice DevOps" },
  { id: "compliance-officer", label: "Compliance Officer" },
  { id: "bob", label: "Bob (User)" },
];

// =============================================================================
// Component
// =============================================================================

export function UserMenuDropdown({
  isOpen,
  onClose,
  anchorRef,
  className,
}: UserMenuDropdownProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);

  const username = useAppSelector(selectUsername);
  const currentPersona = useAppSelector(selectPersona);

  const [showPersonaSwitcher, setShowPersonaSwitcher] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        anchorRef?.current &&
        !anchorRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose, anchorRef]);

  // Close on escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  const handleProfileClick = useCallback(() => {
    navigate("/studio/settings");
    onClose();
  }, [navigate, onClose]);

  const handleSettingsClick = useCallback(() => {
    navigate("/studio/settings");
    onClose();
  }, [navigate, onClose]);

  const handleLogout = useCallback(async () => {
    if (isLoggingOut) return;
    setIsLoggingOut(true);

    try {
      // Get the refresh token from storage to send to backend
      const refreshToken = storage.get<string>(STORAGE_KEYS.REFRESH_TOKEN);

      // Call the backend logout API to revoke tokens and get Keycloak logout URL
      const response = await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      });

      if (response.ok) {
        // Transform snake_case API response to camelCase (ADR-0091)
        const rawData = await response.json();
        const data = transformSnakeToCamel<{ keycloakLogoutUrl?: string }>(
          rawData,
        );
        // Redirect to Keycloak logout URL to end SSO session
        // This ensures the user can log in as a different user
        if (data.keycloakLogoutUrl) {
          // Add post_logout_redirect_uri to return to login page after Keycloak logout
          const logoutUrl = new URL(data.keycloakLogoutUrl);
          logoutUrl.searchParams.set(
            "post_logout_redirect_uri",
            `${window.location.origin}/login`,
          );
          // Clear state JUST before full-page redirect to avoid race condition
          // where AuthGuard tries to lazy-load LoginPage while we're navigating away
          dispatch(logout());
          dispatch(resetPersona());
          window.location.href = logoutUrl.toString();
          return;
        }
      }

      // Fallback: If API call fails or no Keycloak URL, clear state and use React Router
      // Dispatch logout action to clear Redux auth state and localStorage tokens
      // The logout action in authSlice calls clearAllAuthStorage() which clears all token keys
      dispatch(logout());
      // Reset persona state to initial values (also sets isPersonaLoading=true)
      dispatch(resetPersona());
      navigate("/login", { replace: true });
    } catch (error) {
      console.error("Logout error:", error);
      // Even if logout fails, clear local state and redirect
      dispatch(logout());
      dispatch(resetPersona());
      navigate("/login", { replace: true });
    } finally {
      setIsLoggingOut(false);
      onClose();
    }
  }, [dispatch, navigate, onClose, isLoggingOut]);

  const handlePersonaSwitch = useCallback(
    (subPersona: SubPersona) => {
      dispatch(setSubPersona(subPersona));
      setShowPersonaSwitcher(false);
      onClose();
      // Navigate to the new persona's default view
      const defaultViews: Record<SubPersona, string> = {
        admin: "/studio/admin",
        "security-admin": "/studio/compliance",
        auditor: "/studio/admin/audit-logs",
        "alice-builder": "/studio/chat",
        "alice-analyst": "/studio/observability",
        "alice-devops": "/studio/connections",
        "compliance-officer": "/studio/compliance",
        bob: "/studio/chat",
      };
      navigate(defaultViews[subPersona] || "/studio/chat");
    },
    [dispatch, navigate, onClose],
  );

  const menuItems: MenuItem[] = [
    {
      id: "profile",
      icon: <User size={16} />,
      label: "Profile",
      onClick: handleProfileClick,
    },
    {
      id: "settings",
      icon: <Settings size={16} />,
      label: "Settings",
      onClick: handleSettingsClick,
    },
    {
      id: "logout",
      icon: isLoggingOut ? (
        <Loader2 size={16} className="animate-spin" />
      ) : (
        <LogOut size={16} />
      ),
      label: isLoggingOut ? "Signing Out..." : "Sign Out",
      onClick: handleLogout,
      variant: "danger",
    },
  ];

  if (!isOpen) return null;

  return (
    <div
      ref={dropdownRef}
      data-testid="user-menu-dropdown"
      className={cn(
        "absolute right-0 top-full mt-2 w-56 z-50",
        "bg-white dark:bg-gray-800",
        "border border-gray-200 dark:border-gray-700",
        "rounded-lg shadow-lg",
        "py-1",
        className,
      )}
      role="menu"
      aria-label="User menu"
    >
      {/* User info header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
          {username || "Unknown User"}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
          {currentPersona}
        </p>
      </div>

      {/* Persona switcher */}
      <div className="py-1 border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          data-testid="persona-switcher-button"
          onClick={() => setShowPersonaSwitcher(!showPersonaSwitcher)}
          className={cn(
            "w-full flex items-center justify-between px-4 py-2 text-sm",
            "text-gray-700 dark:text-gray-300",
            "hover:bg-gray-100 dark:hover:bg-gray-700",
          )}
          role="menuitem"
        >
          <span className="flex items-center gap-2">
            <Users size={16} />
            Switch Persona
          </span>
          <ChevronDown
            size={14}
            className={cn(
              "transition-transform",
              showPersonaSwitcher && "rotate-180",
            )}
          />
        </button>

        {showPersonaSwitcher && (
          <div className="bg-gray-50 dark:bg-gray-900 py-1">
            {SUB_PERSONA_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                data-testid={`persona-option-${option.id}`}
                onClick={() => handlePersonaSwitch(option.id)}
                className={cn(
                  "w-full text-left px-6 py-1.5 text-sm",
                  "text-gray-600 dark:text-gray-400",
                  "hover:bg-gray-100 dark:hover:bg-gray-800",
                  option.id === currentPersona &&
                    "text-primary-600 dark:text-primary-400 font-medium",
                )}
                role="menuitem"
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Menu items */}
      <div className="py-1">
        {menuItems.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`menu-item-${item.id}`}
            onClick={item.onClick}
            className={cn(
              "w-full flex items-center gap-2 px-4 py-2 text-sm",
              item.variant === "danger"
                ? "text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700",
            )}
            role="menuitem"
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
