/**
 * MobileDrawer Component (Sprint 5.1)
 *
 * A slide-out drawer for mobile navigation.
 * Reuses navigation items from ActivityBar for consistency.
 *
 * Features:
 * - RBAC-filtered navigation items
 * - Focus trap for accessibility
 * - Backdrop click to close
 * - Escape key to close
 * - Smooth slide-in animation
 *
 * Gated behind feature flag: mobile_drawer
 */
import { useCallback, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router";
import {
  MessageSquare,
  GitBranch,
  Cpu,
  Activity,
  Settings,
  Shield,
  HelpCircle,
  FileText,
  Database,
  DollarSign,
  FolderKanban,
  Boxes,
  Plug,
  ClipboardCheck,
  Scale,
  X,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { setActiveNavItem } from "../store/slices/canvasSlice";
import { selectSidebarItems } from "../store/slices/personaSlice";
import { useFocusTrap } from "../hooks/useFocusTrap";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

interface MobileNavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  path: string;
}

// =============================================================================
// Navigation Items (same as ActivityBar for consistency)
// =============================================================================

const MOBILE_NAV_ITEMS: MobileNavItem[] = [
  {
    id: "projects",
    icon: <FolderKanban size={20} />,
    label: "Projects",
    path: "/studio/projects",
  },
  {
    id: "chat",
    icon: <MessageSquare size={20} />,
    label: "Chat",
    path: "/studio/chat",
  },
  {
    id: "workflows",
    icon: <GitBranch size={20} />,
    label: "Workflows",
    path: "/studio/workflows",
  },
  {
    id: "agents",
    icon: <Cpu size={20} />,
    label: "Agents",
    path: "/studio/agents",
  },
  {
    id: "mcp",
    icon: <Database size={20} />,
    label: "MCP",
    path: "/studio/mcp",
  },
  {
    id: "vectors",
    icon: <Boxes size={20} />,
    label: "Vectors",
    path: "/studio/vectors",
  },
  {
    id: "connections",
    icon: <Plug size={20} />,
    label: "Connections",
    path: "/studio/connections",
  },
  {
    id: "files",
    icon: <FileText size={20} />,
    label: "Files",
    path: "/studio/files",
  },
  {
    id: "observability",
    icon: <Activity size={20} />,
    label: "Observability",
    path: "/studio/observability",
  },
  {
    id: "cost",
    icon: <DollarSign size={20} />,
    label: "Cost",
    path: "/studio/cost",
  },
  {
    id: "admin",
    icon: <Shield size={20} />,
    label: "Admin",
    path: "/studio/admin",
  },
  {
    id: "audit",
    icon: <ClipboardCheck size={20} />,
    label: "Audit",
    path: "/studio/audit",
  },
  {
    id: "compliance",
    icon: <Scale size={20} />,
    label: "Compliance",
    path: "/studio/compliance",
  },
];

const MOBILE_BOTTOM_ITEMS: MobileNavItem[] = [
  {
    id: "help",
    icon: <HelpCircle size={20} />,
    label: "Help",
    path: "/studio/help",
  },
  {
    id: "settings",
    icon: <Settings size={20} />,
    label: "Settings",
    path: "/studio/settings",
  },
];

// =============================================================================
// Component
// =============================================================================

export interface MobileDrawerProps {
  /** Whether the drawer is open */
  isOpen: boolean;
  /** Callback when drawer should close */
  onClose: () => void;
  /** Additional class names for the drawer */
  className?: string;
}

export function MobileDrawer({
  isOpen,
  onClose,
  className,
}: MobileDrawerProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const drawerRef = useRef<HTMLDivElement>(null);

  // RBAC: Get allowed sidebar items from persona slice
  const allowedItems = useAppSelector(selectSidebarItems);

  // Filter navigation items based on permissions
  const visibleNavItems = MOBILE_NAV_ITEMS.filter((item) =>
    allowedItems.includes(item.id),
  );
  const visibleBottomItems = MOBILE_BOTTOM_ITEMS.filter((item) =>
    allowedItems.includes(item.id),
  );

  // Focus trap for accessibility (WCAG 2.1 AA)
  useFocusTrap(drawerRef, isOpen);

  // Handle escape key to close
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Handle navigation item click
  const handleNavClick = useCallback(
    (item: MobileNavItem) => {
      dispatch(setActiveNavItem(item.id));
      navigate(item.path);
      onClose();
    },
    [dispatch, navigate, onClose],
  );

  // Determine active item from current path
  const getActiveItem = useCallback(() => {
    const allItems = [...MOBILE_NAV_ITEMS, ...MOBILE_BOTTOM_ITEMS];
    return allItems.find((item) => location.pathname.startsWith(item.path))?.id;
  }, [location.pathname]);

  const activeItem = getActiveItem();

  // Don't render if not open
  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        data-testid="mobile-drawer-backdrop"
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-black/50",
          "transition-opacity duration-200",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        id="mobile-drawer"
        data-testid="mobile-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation"
        className={cn(
          "fixed top-0 left-0 z-50 h-full w-72",
          "bg-white dark:bg-gray-900",
          "border-r border-gray-200 dark:border-gray-700",
          "shadow-xl",
          "transform transition-transform duration-200 ease-out",
          isOpen ? "translate-x-0" : "-translate-x-full",
          className,
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <span className="text-lg font-semibold text-gray-900 dark:text-white">
            Navigation
          </span>
          <button
            type="button"
            data-testid="mobile-drawer-close"
            onClick={onClose}
            aria-label="Close navigation menu"
            className={cn(
              "p-2 rounded-lg",
              "text-gray-500 dark:text-gray-400",
              "hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-800",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
            )}
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex flex-col flex-1 overflow-y-auto py-4">
          <div className="flex flex-col gap-1 px-2">
            {visibleNavItems.map((item) => (
              <button
                key={item.id}
                type="button"
                data-testid={`mobile-nav-${item.id}`}
                onClick={() => handleNavClick(item)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg",
                  "text-left transition-colors",
                  "focus:outline-none focus:ring-2 focus:ring-primary-500",
                  activeItem === item.id
                    ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-800",
                )}
              >
                {item.icon}
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            ))}
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Bottom Items */}
          <div className="flex flex-col gap-1 px-2 pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
            {visibleBottomItems.map((item) => (
              <button
                key={item.id}
                type="button"
                data-testid={`mobile-nav-${item.id}`}
                onClick={() => handleNavClick(item)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg",
                  "text-left transition-colors",
                  "focus:outline-none focus:ring-2 focus:ring-primary-500",
                  activeItem === item.id
                    ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-800",
                )}
              >
                {item.icon}
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            ))}
          </div>
        </nav>
      </div>
    </>
  );
}

MobileDrawer.displayName = "MobileDrawer";
