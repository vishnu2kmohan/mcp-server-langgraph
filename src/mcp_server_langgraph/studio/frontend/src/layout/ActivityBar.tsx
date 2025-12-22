/**
 * ActivityBar Component
 *
 * RBAC-aware sidebar navigation with icons.
 * Extracted from HybridShellLayout for maintainability.
 *
 * Features:
 * - Persona-filtered navigation items (deny-by-default)
 * - Command palette trigger
 * - Active state highlighting
 * - Keyboard accessible
 */
/* eslint-disable react-refresh/only-export-components -- Exports NavItem types and constants alongside component */
import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import {
  MessageSquare,
  GitBranch,
  Cpu,
  Activity,
  Settings,
  Shield,
  Command,
  HelpCircle,
  FileText,
  Database,
  DollarSign,
  Route,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectActiveNavItem,
  setActiveNavItem,
} from "../store/slices/canvasSlice";
import { selectSidebarItems } from "../store/slices/personaSlice";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  path?: string;
}

// =============================================================================
// Navigation Constants
// =============================================================================

export const NAV_ITEMS: NavItem[] = [
  {
    id: "chat",
    icon: <MessageSquare size={20} />,
    label: "Chat",
    path: "/studio/v2/chat",
  },
  {
    id: "workflows",
    icon: <GitBranch size={20} />,
    label: "Workflows",
    path: "/studio/v2/workflows",
  },
  {
    id: "agents",
    icon: <Cpu size={20} />,
    label: "Agents",
    path: "/studio/v2/agents",
  },
  {
    id: "observability",
    icon: <Activity size={20} />,
    label: "Observability",
    path: "/studio/v2/observability",
  },
  {
    id: "files",
    icon: <FileText size={20} />,
    label: "Files",
    path: "/studio/v2/files",
  },
  {
    id: "traces",
    icon: <Route size={20} />,
    label: "Traces",
    path: "/studio/v2/traces",
  },
  {
    id: "mcp",
    icon: <Database size={20} />,
    label: "MCP",
    path: "/studio/v2/mcp",
  },
  {
    id: "cost",
    icon: <DollarSign size={20} />,
    label: "Cost",
    path: "/studio/v2/cost",
  },
  {
    id: "admin",
    icon: <Shield size={20} />,
    label: "Admin",
    path: "/studio/v2/admin",
  },
];

export const BOTTOM_ITEMS: NavItem[] = [
  {
    id: "help",
    icon: <HelpCircle size={20} />,
    label: "Help",
    path: "/studio/v2/help",
  },
  {
    id: "settings",
    icon: <Settings size={20} />,
    label: "Settings",
    path: "/studio/v2/settings",
  },
];

// =============================================================================
// Component
// =============================================================================

export interface ActivityBarProps {
  className?: string;
}

export function ActivityBar({ className }: ActivityBarProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activeNavItem = useAppSelector(selectActiveNavItem);

  // RBAC: Get allowed sidebar items from persona slice (deny-by-default)
  const allowedItems = useAppSelector(selectSidebarItems);

  // Filter navigation items based on persona permissions
  const visibleNavItems = useMemo(
    () => NAV_ITEMS.filter((item) => allowedItems.includes(item.id)),
    [allowedItems],
  );

  // Filter bottom items based on persona permissions
  const visibleBottomItems = useMemo(
    () => BOTTOM_ITEMS.filter((item) => allowedItems.includes(item.id)),
    [allowedItems],
  );

  const handleNavClick = useCallback(
    (item: NavItem) => {
      dispatch(setActiveNavItem(item.id));
      if (item.path) {
        navigate(item.path);
      }
    },
    [dispatch, navigate],
  );

  // Open command palette by dispatching a synthetic Cmd+K event
  const handleCommandPaletteClick = useCallback(() => {
    const event = new KeyboardEvent("keydown", {
      key: "k",
      code: "KeyK",
      metaKey: true,
      ctrlKey: false,
      bubbles: true,
    });
    document.dispatchEvent(event);
  }, []);

  return (
    <nav
      data-testid="activity-bar"
      aria-label="Main navigation"
      className={cn(
        "flex flex-col items-center w-14 py-2",
        "bg-gray-100 dark:bg-gray-900",
        "border-r border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Main navigation icons - RBAC filtered */}
      <div className="flex flex-col gap-1" role="group" aria-label="Primary navigation">
        {visibleNavItems.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`nav-${item.id}`}
            aria-label={item.label}
            title={item.label}
            onClick={() => handleNavClick(item)}
            className={cn(
              "p-2 rounded-lg transition-all",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              activeNavItem === item.id &&
                "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300",
              activeNavItem !== item.id &&
                "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
            )}
          >
            {item.icon}
          </button>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" aria-hidden="true" />

      {/* Bottom icons - RBAC filtered */}
      <div className="flex flex-col gap-1" role="group" aria-label="Secondary navigation">
        <button
          type="button"
          data-testid="command-palette-button"
          aria-label="Command Palette"
          title="Command Palette (⌘K)"
          onClick={handleCommandPaletteClick}
          className={cn(
            "p-2 rounded-lg transition-all",
            "text-gray-500 dark:text-gray-400",
            "hover:bg-gray-200 dark:hover:bg-gray-700",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
          )}
        >
          <Command size={20} />
        </button>
        {visibleBottomItems.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`nav-${item.id}`}
            aria-label={item.label}
            title={item.label}
            onClick={() => handleNavClick(item)}
            className={cn(
              "p-2 rounded-lg transition-all",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
              activeNavItem === item.id &&
                "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300",
              activeNavItem !== item.id &&
                "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
            )}
          >
            {item.icon}
          </button>
        ))}
      </div>
    </nav>
  );
}
