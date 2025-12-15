/**
 * Sidebar Component
 *
 * Persistent navigation sidebar for the Studio application.
 * Features:
 * - Grouped navigation by category (CONVERSATIONS, BUILD, CONNECTIONS, INSIGHTS, ADMIN)
 * - Lucide React icons for each navigation item
 * - RBAC filtering based on persona (admin, developer, user)
 * - User profile section with logout button
 * - Theme toggle
 */

import { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router";
import {
  MessageSquare,
  GitBranch,
  Puzzle,
  Cpu,
  Database,
  Activity,
  DollarSign,
  Settings,
  LayoutDashboard,
  Shield,
  LogOut,
  Sun,
  Moon,
  FolderKanban,
  Command,
  Menu,
  X,
  PanelLeftClose,
  PanelLeft,
  Loader2,
} from "lucide-react";
import { NotificationBell } from "./NotificationBell";
import { useGetFeatureFlagsQuery, useLogoutMutation } from "../../api";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  resetPersona,
  selectUsername as selectPersonaUsername,
  selectPersona as selectPersonaPersona,
} from "../../store/slices/personaSlice";
import { selectUser, logout as authLogout } from "../../store/slices/authSlice";
import {
  toggleSidebarCollapsed,
  selectSidebarCollapsed,
} from "../../store/slices/uiSlice";
import type { Persona } from "../../types/auth";

/**
 * Sidebar items by persona for RBAC filtering
 *
 * NOTE: Must stay in sync with personaSlice.ts PERSONA_CONFIGS
 */
const PERSONA_SIDEBAR_ITEMS: Record<Persona, string[]> = {
  admin: [
    "projects",
    "chat",
    "workflows",
    "mcp",
    "agents",
    "vectors",
    "observability",
    "cost",
    "settings",
    "admin",
    "audit-logs",
  ],
  developer: [
    "projects",
    "chat",
    "workflows",
    "mcp",
    "agents",
    "vectors",
    "observability",
    "cost",
    "settings",
  ],
  // Expanded access for standard users (AI-native UX - HEART Adoption improvement)
  // Users see unified Workflows page with both owned and shared workflows
  user: ["projects", "chat", "workflows", "cost"],
};

/**
 * Navigation item configuration
 */
interface NavItem {
  id: string;
  path: string;
  label: string;
  icon: React.ReactNode;
  group: NavGroup;
}

type NavGroup =
  | "workspace"
  | "conversations"
  | "build"
  | "connections"
  | "insights"
  | "admin";

const GROUP_LABELS: Record<NavGroup, string> = {
  workspace: "WORKSPACE",
  conversations: "CONVERSATIONS",
  build: "BUILD",
  connections: "CONNECTIONS",
  insights: "INSIGHTS",
  admin: "ADMIN",
};

const NAV_ITEMS: NavItem[] = [
  // WORKSPACE (Unified Workspace Paradigm)
  {
    id: "projects",
    path: "/studio/projects",
    label: "Projects",
    icon: <FolderKanban size={18} />,
    group: "workspace",
  },

  // CONVERSATIONS
  {
    id: "chat",
    path: "/studio/chat",
    label: "Chat",
    icon: <MessageSquare size={18} />,
    group: "conversations",
  },

  // BUILD
  {
    id: "workflows",
    path: "/studio/workflows",
    label: "Workflows",
    icon: <GitBranch size={18} />,
    group: "build",
  },

  // CONNECTIONS
  {
    id: "mcp",
    path: "/studio/connections/mcp",
    label: "MCP Explorer",
    icon: <Puzzle size={18} />,
    group: "connections",
  },
  {
    id: "agents",
    path: "/studio/connections/agents",
    label: "Agents",
    icon: <Cpu size={18} />,
    group: "connections",
  },
  {
    id: "vectors",
    path: "/studio/connections/vectors",
    label: "Vectors",
    icon: <Database size={18} />,
    group: "connections",
  },

  // INSIGHTS
  {
    id: "observability",
    path: "/studio/observability",
    label: "Observability",
    icon: <Activity size={18} />,
    group: "insights",
  },
  {
    id: "cost",
    path: "/studio/cost",
    label: "Cost",
    icon: <DollarSign size={18} />,
    group: "insights",
  },

  // Admin-visible settings (in insights for developers, admin for admins)
  {
    id: "settings",
    path: "/studio/settings",
    label: "Settings",
    icon: <Settings size={18} />,
    group: "insights",
  },

  // ADMIN
  {
    id: "admin",
    path: "/studio/admin/dashboard",
    label: "Dashboard",
    icon: <LayoutDashboard size={18} />,
    group: "admin",
  },
  {
    id: "audit-logs",
    path: "/studio/admin/audit-logs",
    label: "Audit Logs",
    icon: <Shield size={18} />,
    group: "admin",
  },
];

/**
 * Get CSS classes for nav links based on active state and collapsed mode
 *
 * UX Best Practices (NN/G Guidelines):
 * - Left border accent for active state (visual landmark)
 * - Focus-visible ring for keyboard navigation (accessibility)
 * - Larger touch targets (44px minimum - py-3)
 * - Smooth transitions (150ms for responsiveness)
 */
function getNavLinkClasses(isActive: boolean, isCollapsed: boolean): string {
  // Base classes with improved touch targets (py-3) and smooth transitions
  const baseClasses = isCollapsed
    ? "relative flex items-center justify-center p-3 text-sm font-medium rounded-lg transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900"
    : "relative flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900";

  // Active state with left border accent (visual landmark per NN/G)
  const activeClasses = isCollapsed
    ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-0.5 before:h-5 before:bg-blue-600 before:rounded-r"
    : "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-1 before:h-6 before:bg-blue-600 before:rounded-r";

  const inactiveClasses =
    "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800";

  return `${baseClasses} ${isActive ? activeClasses : inactiveClasses}`;
}

/**
 * Individual navigation item with aria-current support
 *
 * UX Best Practices:
 * - aria-current="page" for screen readers (WCAG 2.1)
 * - Proper focus management for keyboard navigation
 */
function SidebarNavItem({
  item,
  isCollapsed,
}: {
  item: NavItem;
  isCollapsed: boolean;
}) {
  return (
    <NavLink
      to={item.path}
      className={({ isActive }) => getNavLinkClasses(isActive, isCollapsed)}
      title={isCollapsed ? item.label : undefined}
    >
      {({ isActive }) => (
        <>
          {/* Hidden span with aria-current for screen readers */}
          {isActive && <span className="sr-only" aria-current="page" />}
          {item.icon}
          {!isCollapsed && <span>{item.label}</span>}
        </>
      )}
    </NavLink>
  );
}

/**
 * Navigation group component
 *
 * UX Best Practices:
 * - aria-current="page" for screen readers (WCAG 2.1)
 * - Group labels with proper semantic structure
 * - Consistent spacing and visual hierarchy
 */
function NavGroupComponent({
  label,
  items,
  isCollapsed,
}: {
  label: string;
  items: NavItem[];
  isCollapsed: boolean;
}) {
  if (items.length === 0) return null;

  return (
    <div className="mb-4" role="group" aria-label={label}>
      {!isCollapsed && (
        <h3 className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {label}
        </h3>
      )}
      <div className="space-y-1">
        {items.map((item) => (
          <SidebarNavItem
            key={item.path}
            item={item}
            isCollapsed={isCollapsed}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Sidebar navigation component
 */
export function Sidebar() {
  const [isDarkMode, setIsDarkMode] = useState(true); // Default to dark mode
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  // Get sidebar collapsed state from Redux
  const isCollapsed = useAppSelector(selectSidebarCollapsed);

  // Get user info from auth state (primary) or persona state (fallback)
  const authUser = useAppSelector(selectUser);
  const personaUsername = useAppSelector(selectPersonaUsername);
  const personaPersona = useAppSelector(selectPersonaPersona);

  // Prefer auth user, fall back to persona slice
  const username = authUser?.username ?? personaUsername ?? null;
  const persona: Persona = authUser?.persona ?? personaPersona ?? "user";

  // Get sidebar items based on persona (derived from auth or persona state)
  const sidebarItemIds = PERSONA_SIDEBAR_ITEMS[persona];

  // Apply dark mode on mount
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDarkMode]);

  // Get feature flags from RTK Query
  const { data: featureFlags } = useGetFeatureFlagsQuery();

  // Native logout mutation (avoids Keycloak UI redirect)
  const [logoutMutation, { isLoading: isLoggingOut }] = useLogoutMutation();

  // Filter nav items based on:
  // 1. Persona's allowed sidebar items (RBAC)
  // 2. Feature flags (enabled features)
  const filteredItems = NAV_ITEMS.filter((item) => {
    // First check RBAC (persona allows this item)
    if (!sidebarItemIds.includes(item.id)) {
      return false;
    }
    // Then check feature flags (feature is enabled)
    // If feature flags haven't loaded yet, default to showing the item
    if (!featureFlags) {
      return true;
    }
    // Check if this feature is enabled (use item.id as key)
    const flagValue = featureFlags[item.id as keyof typeof featureFlags];
    return flagValue !== false; // Default to true if flag not specified
  });

  // Group filtered items by category
  const groupedItems: Record<NavGroup, NavItem[]> = {
    workspace: filteredItems.filter((item) => item.group === "workspace"),
    conversations: filteredItems.filter(
      (item) => item.group === "conversations",
    ),
    build: filteredItems.filter((item) => item.group === "build"),
    connections: filteredItems.filter((item) => item.group === "connections"),
    insights: filteredItems.filter((item) => item.group === "insights"),
    admin: filteredItems.filter((item) => item.group === "admin"),
  };

  const handleLogout = async () => {
    try {
      // Call native logout API to revoke tokens with Keycloak
      await logoutMutation().unwrap();
    } catch {
      // Continue with local logout even if API fails
      console.warn("Token revocation failed, continuing with local logout");
    }

    // Reset auth and persona state to clear cached user data
    dispatch(authLogout());
    dispatch(resetPersona());

    // Navigate to login page (native experience, no Keycloak UI redirect)
    navigate("/login");
  };

  const handleThemeToggle = () => {
    setIsDarkMode(!isDarkMode);
    // useEffect will handle applying the class to documentElement
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      {/* Skip Link - Accessibility (WCAG 2.1 SC 2.4.1) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded-lg focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        Skip to main content
      </a>

      {/* Mobile Menu Toggle Button - Fixed position on mobile */}
      <button
        onClick={toggleMobileMenu}
        className="fixed top-4 left-4 z-50 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 md:hidden transition-transform duration-150 active:scale-95"
        aria-label="Toggle menu"
        aria-expanded={isMobileMenuOpen}
        aria-controls="sidebar-navigation"
      >
        <Menu size={20} className="text-gray-700 dark:text-gray-300" />
      </button>

      {/* Mobile Overlay */}
      {isMobileMenuOpen && (
        <div
          data-testid="sidebar-overlay"
          className="fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-150"
          onClick={closeMobileMenu}
          aria-hidden="true"
        />
      )}

      <nav
        id="sidebar-navigation"
        className={`
          ${isCollapsed ? "w-16" : "w-64"} h-screen bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col
          fixed md:relative z-50
          transform transition-all duration-200 ease-in-out
          ${isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0
        `}
        role="navigation"
        aria-label="Main navigation"
      >
        {/* Header */}
        <div className={isCollapsed ? "p-3" : "px-4 py-4"}>
          {isCollapsed ? (
            /* Collapsed: Show only expand button centered */
            <button
              onClick={() => dispatch(toggleSidebarCollapsed())}
              className="hidden md:flex w-full items-center justify-center p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors duration-150"
              aria-label="Expand sidebar"
              title="Expand sidebar (Cmd+B)"
            >
              <PanelLeft
                size={18}
                className="text-gray-500 dark:text-gray-400"
              />
            </button>
          ) : (
            /* Expanded: Logo + Title (centered) + Close/Collapse */
            <div className="flex items-center w-full">
              {/* Logo and title - centered */}
              <div className="flex items-center gap-2 flex-1 justify-center">
                <img
                  src="/icons/icon.svg"
                  alt="Agent Studio"
                  className="w-7 h-7"
                />
                <h1 className="text-lg font-bold text-gray-900 dark:text-white">
                  Agent Studio
                </h1>
              </div>
              <div className="flex items-center gap-1">
                {/* Mobile close button */}
                <button
                  onClick={closeMobileMenu}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors duration-150 md:hidden"
                  aria-label="Close menu"
                >
                  <X size={18} className="text-gray-500 dark:text-gray-400" />
                </button>
                {/* Desktop collapse toggle */}
                <button
                  onClick={() => dispatch(toggleSidebarCollapsed())}
                  className="hidden md:flex p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors duration-150"
                  aria-label="Collapse sidebar"
                  title="Collapse sidebar (Cmd+B)"
                >
                  <PanelLeftClose
                    size={18}
                    className="text-gray-500 dark:text-gray-400"
                  />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Navigation Groups */}
        <div
          className={`flex-1 ${isCollapsed ? "px-2" : "px-3"} overflow-y-auto`}
        >
          {groupedItems.workspace.length > 0 && (
            <NavGroupComponent
              label={GROUP_LABELS.workspace}
              items={groupedItems.workspace}
              isCollapsed={isCollapsed}
            />
          )}
          {groupedItems.conversations.length > 0 && (
            <NavGroupComponent
              label={GROUP_LABELS.conversations}
              items={groupedItems.conversations}
              isCollapsed={isCollapsed}
            />
          )}
          {groupedItems.build.length > 0 && (
            <NavGroupComponent
              label={GROUP_LABELS.build}
              items={groupedItems.build}
              isCollapsed={isCollapsed}
            />
          )}
          {groupedItems.connections.length > 0 && (
            <NavGroupComponent
              label={GROUP_LABELS.connections}
              items={groupedItems.connections}
              isCollapsed={isCollapsed}
            />
          )}
          {groupedItems.insights.length > 0 && (
            <NavGroupComponent
              label={GROUP_LABELS.insights}
              items={groupedItems.insights}
              isCollapsed={isCollapsed}
            />
          )}
          {groupedItems.admin.length > 0 && (
            <NavGroupComponent
              label={GROUP_LABELS.admin}
              items={groupedItems.admin}
              isCollapsed={isCollapsed}
            />
          )}
        </div>

        {/* User Profile Section - UX: Logout separated to prevent accidental clicks */}
        <div
          className={`${isCollapsed ? "p-2" : "p-4"} border-t border-gray-200 dark:border-gray-800`}
          data-testid="user-profile-section"
        >
          {isCollapsed ? (
            /* Collapsed: Vertical layout with clear separation */
            <div className="flex flex-col items-center gap-2">
              {/* User avatar - clickable to settings */}
              <button
                onClick={() => navigate("/studio/settings")}
                className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center shadow-sm hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-700 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                title={`${username || "Guest"}${persona !== "user" ? ` (${persona})` : ""} - Go to Settings`}
              >
                <span className="text-sm font-semibold text-white">
                  {username ? username.charAt(0).toUpperCase() : "?"}
                </span>
              </button>

              {/* Quick actions */}
              <div className="flex flex-col gap-1">
                {/* Command palette */}
                <button
                  onClick={() => {
                    document.dispatchEvent(
                      new KeyboardEvent("keydown", {
                        key: "k",
                        metaKey: true,
                        ctrlKey: true,
                      }),
                    );
                  }}
                  className="flex items-center justify-center w-10 h-10 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  aria-label="Open command palette"
                  title="Search (⌘K)"
                >
                  <Command size={18} />
                </button>
                {/* Notification bell */}
                <NotificationBell />
                {/* Theme toggle */}
                <button
                  onClick={handleThemeToggle}
                  className="flex items-center justify-center w-10 h-10 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  aria-label={
                    isDarkMode ? "Switch to light mode" : "Switch to dark mode"
                  }
                  title={isDarkMode ? "Light mode" : "Dark mode"}
                >
                  {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
                </button>
              </div>

              {/* Logout - visually separated */}
              <div className="w-full pt-2 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="flex items-center justify-center w-10 h-10 mx-auto text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label={isLoggingOut ? "Signing out..." : "Sign out"}
                  title={isLoggingOut ? "Signing out..." : "Sign out"}
                >
                  {isLoggingOut ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <LogOut size={18} />
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Expanded: Full user profile with clear hierarchy */
            <div className="space-y-3">
              {/* User Info - Clickable to go to settings */}
              <button
                onClick={() => navigate("/studio/settings")}
                className="w-full flex items-center gap-3 p-2 -m-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                title="Go to Settings"
              >
                {/* Avatar with initials */}
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center shadow-sm flex-shrink-0">
                  <span className="text-sm font-semibold text-white">
                    {username ? username.charAt(0).toUpperCase() : "?"}
                  </span>
                </div>
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {username || "Guest"}
                  </p>
                  {/* Only show role badge for admin/developer */}
                  {persona !== "user" && (
                    <span
                      className={`inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded ${
                        persona === "admin"
                          ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                          : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                      }`}
                    >
                      {persona}
                    </span>
                  )}
                </div>
              </button>

              {/* Command palette search */}
              <button
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors duration-150"
                title="Command Palette (Cmd+K)"
                onClick={() => {
                  document.dispatchEvent(
                    new KeyboardEvent("keydown", {
                      key: "k",
                      metaKey: true,
                      ctrlKey: true,
                    }),
                  );
                }}
              >
                <Command size={16} />
                <span className="flex-1 text-left">Search...</span>
                <kbd className="px-1.5 py-0.5 text-[10px] font-medium bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600">
                  ⌘K
                </kbd>
              </button>

              {/* Actions row */}
              <div className="flex items-center gap-2">
                {/* Notification bell */}
                <NotificationBell />
                {/* Theme toggle */}
                <button
                  onClick={handleThemeToggle}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  aria-label={
                    isDarkMode ? "Switch to light mode" : "Switch to dark mode"
                  }
                  title={isDarkMode ? "Light mode" : "Dark mode"}
                >
                  {isDarkMode ? <Sun size={16} /> : <Moon size={16} />}
                </button>
                {/* Logout */}
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label={isLoggingOut ? "Signing out..." : "Sign out"}
                  title={isLoggingOut ? "Signing out..." : "Sign out"}
                >
                  {isLoggingOut ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <LogOut size={16} />
                  )}
                </button>
              </div>

              {/* Version - subtle footer */}
              <p className="text-center text-xs text-gray-400 dark:text-gray-500">
                v0.1.0
              </p>
            </div>
          )}
        </div>
      </nav>
    </>
  );
}
