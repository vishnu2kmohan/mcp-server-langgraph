/**
 * LeftSidebar Component
 *
 * JupyterLab-inspired hybrid navigation combining Activity Bar + grouped content.
 * Features:
 * - Activity Bar on the left edge for quick group switching
 * - Content panel with expandable group sections
 * - Scroll-to-group behavior when clicking Activity Bar icons
 * - RBAC filtering based on persona
 * - Persistence via Redux workspaceSlice
 */

import {
  useCallback,
  useRef,
  useState,
  useEffect,
  type ReactNode,
} from "react";
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
  FolderKanban,
  ChevronRight,
  ChevronDown,
  Plus,
  ChevronsLeft,
  ChevronsRight,
  Sun,
  Moon,
  Command,
  User,
  LogOut,
  Maximize2,
  Minimize2,
} from "lucide-react";
import { useTheme } from "../../hooks/useTheme";
import { selectUser } from "../../store/slices/authSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectActiveActivityId,
  selectExpandedGroups,
  selectLeftSidebarCollapsed,
  selectFocusMode,
  setActiveActivityId,
  setLeftSidebarCollapsed,
  setFocusMode,
  toggleExpandedGroup,
} from "../../store/slices/workspaceSlice";
import { clearAuthTokens } from "../../utils/storage";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface LeftSidebarProps {
  /** Whether the sidebar is collapsed (shows only activity bar) */
  collapsed?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Callback when "New Chat" button is clicked */
  onNewChat?: () => void;
  /** Callback when "New Project" button is clicked */
  onNewProject?: () => void;
}

type NavGroup =
  | "workspace"
  | "conversations"
  | "build"
  | "connections"
  | "insights"
  | "admin";

interface NavItem {
  id: string;
  path: string;
  label: string;
  icon: ReactNode;
  group: NavGroup;
}

interface GroupConfig {
  id: NavGroup;
  label: string;
  icon: ReactNode;
}

// =============================================================================
// Constants
// =============================================================================

const GROUPS: GroupConfig[] = [
  { id: "workspace", label: "WORKSPACE", icon: <FolderKanban size={20} /> },
  {
    id: "conversations",
    label: "CONVERSATIONS",
    icon: <MessageSquare size={20} />,
  },
  { id: "build", label: "BUILD", icon: <GitBranch size={20} /> },
  { id: "connections", label: "CONNECTIONS", icon: <Puzzle size={20} /> },
  { id: "insights", label: "INSIGHTS", icon: <Activity size={20} /> },
  { id: "admin", label: "ADMIN", icon: <Shield size={20} /> },
];

const NAV_ITEMS: NavItem[] = [
  // WORKSPACE
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
];

// =============================================================================
// Component
// =============================================================================

export function LeftSidebar({
  collapsed: collapsedProp,
  className,
  onNewChat,
  onNewProject,
}: LeftSidebarProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activeActivityId = useAppSelector(selectActiveActivityId);
  const expandedGroups = useAppSelector(selectExpandedGroups);
  const collapsedFromStore = useAppSelector(selectLeftSidebarCollapsed);
  const focusMode = useAppSelector(selectFocusMode);
  const user = useAppSelector(selectUser);
  const { isDark, toggleTheme } = useTheme();

  // User menu state
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Use prop if provided, otherwise use Redux state
  const collapsed = collapsedProp ?? collapsedFromStore;

  // Toggle content panel collapse
  const handleToggleCollapse = useCallback(() => {
    dispatch(setLeftSidebarCollapsed(!collapsed));
  }, [dispatch, collapsed]);

  // Open command palette (Cmd+K)
  const handleOpenCommandPalette = useCallback(() => {
    // Dispatch keyboard event to trigger CommandPalette
    const event = new KeyboardEvent("keydown", {
      key: "k",
      metaKey: true,
      ctrlKey: false,
      bubbles: true,
    });
    document.dispatchEvent(event);
  }, []);

  // Handle user menu toggle
  const handleUserMenuToggle = useCallback(() => {
    setIsUserMenuOpen((prev) => !prev);
  }, []);

  // Handle logout - redirect to Keycloak end-session endpoint
  const handleLogout = useCallback(() => {
    // Clear local storage tokens using centralized utility
    clearAuthTokens();
    setIsUserMenuOpen(false);

    // Redirect to backend logout endpoint which handles Keycloak session termination
    // This ensures both frontend tokens AND Keycloak session are cleared
    const logoutUrl = `/api/v1/auth/logout?post_logout_redirect_uri=${encodeURIComponent(window.location.origin + "/login")}`;
    window.location.href = logoutUrl;
  }, []);

  // Handle Focus Mode toggle
  const handleToggleFocusMode = useCallback(() => {
    dispatch(setFocusMode(!focusMode));
  }, [dispatch, focusMode]);

  // Handle settings navigation
  const handleGoToSettings = useCallback(() => {
    setIsUserMenuOpen(false);
    navigate("/studio/settings");
  }, [navigate]);

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setIsUserMenuOpen(false);
      }
    };

    if (isUserMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isUserMenuOpen]);

  // Refs for scrolling to groups
  const groupRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Handle activity bar click - expand group and scroll to it
  const handleActivityClick = useCallback(
    (groupId: string) => {
      dispatch(setActiveActivityId(groupId));

      // Expand the group if not already
      if (!expandedGroups.includes(groupId)) {
        dispatch(toggleExpandedGroup(groupId));
      }

      // Scroll to group (only if scrollIntoView is available)
      const groupElement = groupRefs.current[groupId];
      if (groupElement && typeof groupElement.scrollIntoView === "function") {
        groupElement.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    },
    [dispatch, expandedGroups],
  );

  // Handle group header click - toggle expansion
  const handleGroupToggle = useCallback(
    (groupId: string) => {
      dispatch(toggleExpandedGroup(groupId));
      dispatch(setActiveActivityId(groupId));
    },
    [dispatch],
  );

  // Group items by group
  const itemsByGroup = NAV_ITEMS.reduce(
    (acc, item) => {
      if (!acc[item.group]) {
        acc[item.group] = [];
      }
      acc[item.group].push(item);
      return acc;
    },
    {} as Record<NavGroup, NavItem[]>,
  );

  return (
    <div
      data-testid="left-sidebar"
      className={cn("flex h-full", "bg-gray-50 dark:bg-gray-800", className)}
    >
      {/* Activity Bar */}
      <div
        data-testid="activity-bar"
        role="tablist"
        aria-orientation="vertical"
        className={cn(
          "flex flex-col gap-1 p-2 w-12",
          "bg-gray-100 dark:bg-gray-900",
          "border-r border-gray-200 dark:border-gray-700",
        )}
      >
        {GROUPS.map((group) => (
          <button
            key={group.id}
            type="button"
            role="tab"
            aria-selected={activeActivityId === group.id}
            aria-label={group.label}
            title={group.label}
            onClick={() => handleActivityClick(group.id)}
            className={cn(
              "p-2 rounded-lg transition-all",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              activeActivityId === group.id &&
                "bg-primary-100 dark:bg-primary-900/30",
              activeActivityId === group.id &&
                "text-primary-700 dark:text-primary-300",
              activeActivityId !== group.id &&
                "text-gray-500 dark:text-gray-400",
              activeActivityId !== group.id &&
                "hover:bg-gray-200 dark:hover:bg-gray-700",
            )}
          >
            {group.icon}
          </button>
        ))}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Theme Toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          title={isDark ? "Light Mode" : "Dark Mode"}
          className={cn(
            "p-2 rounded-lg transition-all",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            "text-gray-500 dark:text-gray-400",
            "hover:bg-gray-200 dark:hover:bg-gray-700",
          )}
        >
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>

        {/* Command Palette */}
        <button
          type="button"
          onClick={handleOpenCommandPalette}
          aria-label="Open command palette (⌘K)"
          title="Command Palette (⌘K)"
          className={cn(
            "p-2 rounded-lg transition-all",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            "text-gray-500 dark:text-gray-400",
            "hover:bg-gray-200 dark:hover:bg-gray-700",
          )}
        >
          <Command size={20} />
        </button>

        {/* Focus Mode Toggle */}
        <button
          type="button"
          onClick={handleToggleFocusMode}
          aria-label={focusMode ? "Exit focus mode" : "Enter focus mode"}
          title={
            focusMode
              ? "Exit Focus Mode (Esc)"
              : "Focus Mode - Hide sidebars (⌘⇧F)"
          }
          className={cn(
            "p-2 rounded-lg transition-all",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            focusMode
              ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
              : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
          )}
        >
          {focusMode ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
        </button>

        {/* User Menu */}
        <div ref={userMenuRef} className="relative">
          <button
            type="button"
            onClick={handleUserMenuToggle}
            aria-label="User menu"
            title={user?.username ?? "User"}
            className={cn(
              "p-2 rounded-lg transition-all",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              isUserMenuOpen
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
            )}
          >
            <User size={20} />
          </button>

          {/* User Dropdown Menu */}
          {isUserMenuOpen && (
            <div
              className={cn(
                "absolute left-12 bottom-0 z-50",
                "w-48 py-1 rounded-lg shadow-lg",
                "bg-white dark:bg-gray-800",
                "border border-gray-200 dark:border-gray-700",
              )}
            >
              {/* User Info */}
              <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {user?.username ?? "Guest"}
                </p>
                {user?.email && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {user.email}
                  </p>
                )}
              </div>

              {/* Menu Items */}
              <button
                type="button"
                onClick={handleGoToSettings}
                className={cn(
                  "w-full px-3 py-2 text-left text-sm",
                  "text-gray-700 dark:text-gray-300",
                  "hover:bg-gray-100 dark:hover:bg-gray-700",
                  "flex items-center gap-2",
                )}
              >
                <Settings size={16} />
                Settings
              </button>

              <button
                type="button"
                onClick={handleLogout}
                className={cn(
                  "w-full px-3 py-2 text-left text-sm",
                  "text-red-600 dark:text-red-400",
                  "hover:bg-gray-100 dark:hover:bg-gray-700",
                  "flex items-center gap-2",
                )}
              >
                <LogOut size={16} />
                Sign out
              </button>
            </div>
          )}
        </div>

        {/* Collapse/Expand Navigation Panel Toggle */}
        <button
          type="button"
          onClick={handleToggleCollapse}
          aria-label={
            collapsed ? "Expand navigation panel" : "Collapse navigation panel"
          }
          title={
            collapsed
              ? "Expand Navigation Panel (⌘\\)"
              : "Collapse Navigation Panel (⌘\\)"
          }
          className={cn(
            "p-2 rounded-lg transition-all",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            "text-gray-500 dark:text-gray-400",
            "hover:bg-gray-200 dark:hover:bg-gray-700",
          )}
        >
          {collapsed ? <ChevronsRight size={20} /> : <ChevronsLeft size={20} />}
        </button>
      </div>

      {/* Content Panel */}
      <div
        data-testid="sidebar-content"
        className={cn("flex-1 overflow-y-auto", collapsed && "hidden")}
      >
        {GROUPS.map((group) => {
          const items = itemsByGroup[group.id] || [];
          if (items.length === 0) return null;

          const isExpanded = expandedGroups.includes(group.id);

          return (
            <div
              key={group.id}
              ref={(el) => {
                groupRefs.current[group.id] = el;
              }}
              className="border-b border-gray-200 dark:border-gray-700 last:border-b-0"
            >
              {/* Group Header */}
              <button
                type="button"
                onClick={() => handleGroupToggle(group.id)}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-2",
                  "text-xs font-semibold tracking-wider",
                  "text-gray-500 dark:text-gray-400",
                  "hover:bg-gray-100 dark:hover:bg-gray-700/50",
                  "transition-colors",
                )}
              >
                {isExpanded ? (
                  <ChevronDown size={14} />
                ) : (
                  <ChevronRight size={14} />
                )}
                <span>{group.label}</span>
              </button>

              {/* Group Items */}
              {isExpanded && (
                <div className="pb-2">
                  {/* Action button for specific groups */}
                  {group.id === "conversations" && (
                    <button
                      type="button"
                      onClick={onNewChat}
                      className={cn(
                        "flex items-center gap-2 px-4 py-1.5 mx-2 mb-1 rounded-md w-[calc(100%-1rem)]",
                        "text-sm transition-colors",
                        "bg-primary-100 dark:bg-primary-900/30",
                        "text-primary-700 dark:text-primary-300",
                        "hover:bg-primary-200 dark:hover:bg-primary-900/50",
                      )}
                    >
                      <Plus size={16} />
                      <span>New Chat</span>
                    </button>
                  )}
                  {group.id === "workspace" && (
                    <button
                      type="button"
                      onClick={onNewProject}
                      className={cn(
                        "flex items-center gap-2 px-4 py-1.5 mx-2 mb-1 rounded-md w-[calc(100%-1rem)]",
                        "text-sm transition-colors",
                        "bg-primary-100 dark:bg-primary-900/30",
                        "text-primary-700 dark:text-primary-300",
                        "hover:bg-primary-200 dark:hover:bg-primary-900/50",
                      )}
                    >
                      <Plus size={16} />
                      <span>New Project</span>
                    </button>
                  )}
                  {items.map((item) => (
                    <NavLink
                      key={item.id}
                      to={item.path}
                      aria-label={item.label}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-2 px-4 py-1.5 mx-2 rounded-md",
                          "text-sm transition-colors",
                          "focus:outline-none focus:ring-2 focus:ring-primary-500",
                          isActive && "bg-primary-100 dark:bg-primary-900/30",
                          isActive && "text-primary-700 dark:text-primary-300",
                          !isActive && "text-gray-700 dark:text-gray-300",
                          !isActive &&
                            "hover:bg-gray-100 dark:hover:bg-gray-700/50",
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span className="sr-only">Current page: </span>
                          )}
                          {item.icon}
                          <span aria-current={isActive ? "page" : undefined}>
                            {item.label}
                          </span>
                        </>
                      )}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default LeftSidebar;
