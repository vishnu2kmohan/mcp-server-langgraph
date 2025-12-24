/**
 * ActivityBar Component
 *
 * RBAC-aware sidebar navigation with icons.
 * Extracted from StudioShellLayout for maintainability.
 *
 * Features:
 * - Persona-filtered navigation items (deny-by-default)
 * - Command palette trigger
 * - Active state highlighting
 * - Keyboard accessible
 * - AI-powered navigation predictions (Sprint 6)
 */
/* eslint-disable react-refresh/only-export-components -- Exports NavItem types and constants alongside component */
import { useCallback, useMemo, useEffect } from "react";
import { useNavigate, useLocation } from "react-router";
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
import { useNavPrediction } from "../hooks/useUXIntelligence";

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
    id: "observability",
    icon: <Activity size={20} />,
    label: "Observability",
    path: "/studio/observability",
  },
  {
    id: "files",
    icon: <FileText size={20} />,
    label: "Files",
    path: "/studio/files",
  },
  {
    id: "traces",
    icon: <Route size={20} />,
    label: "Traces",
    path: "/studio/traces",
  },
  {
    id: "mcp",
    icon: <Database size={20} />,
    label: "MCP",
    path: "/studio/mcp",
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
];

export const BOTTOM_ITEMS: NavItem[] = [
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

export interface ActivityBarProps {
  className?: string;
  /** Enable AI-powered navigation predictions (Sprint 6) */
  enableAI?: boolean;
  /** Reorder navigation items based on AI predictions */
  reorderByPrediction?: boolean;
}

export function ActivityBar({
  className,
  enableAI = false,
  reorderByPrediction = false,
}: ActivityBarProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const activeNavItem = useAppSelector(selectActiveNavItem);

  // RBAC: Get allowed sidebar items from persona slice (deny-by-default)
  const allowedItems = useAppSelector(selectSidebarItems);

  // Sync activeNavItem with current route (fixes deep-linking/browser navigation)
  useEffect(() => {
    const allItems = [...NAV_ITEMS, ...BOTTOM_ITEMS];
    const matchedItem = allItems.find(
      (item) => item.path && location.pathname.startsWith(item.path),
    );

    // Only sync if:
    // 1. We found a matching nav item
    // 2. It's different from current active item
    // 3. It's visible to the current persona (in allowedItems)
    if (
      matchedItem &&
      matchedItem.id !== activeNavItem &&
      allowedItems.includes(matchedItem.id)
    ) {
      dispatch(setActiveNavItem(matchedItem.id));
    }
    // Note: Unknown routes (e.g., /studio/projects) don't change activeNavItem
  }, [location.pathname, activeNavItem, allowedItems, dispatch]);

  // AI Navigation Predictions (Sprint 6)
  const { predictedItems, isLoading: predictionsLoading } = useNavPrediction({
    userId: "",
    currentPage: activeNavItem ?? "chat",
    recentPages: [], // Could be tracked via session history
    enabled: enableAI,
  });

  // Create a set of predicted item IDs for quick lookup
  const predictedItemIds = useMemo(() => {
    if (!enableAI || !predictedItems?.length) return new Set<string>();
    return new Set(predictedItems.map((p) => p.id));
  }, [enableAI, predictedItems]);

  // Filter navigation items based on persona permissions
  const visibleNavItems = useMemo(() => {
    const filtered = NAV_ITEMS.filter((item) => allowedItems.includes(item.id));

    // Optionally reorder based on predictions
    if (enableAI && reorderByPrediction && (predictedItems?.length ?? 0) > 0) {
      // Create a score map from predictions
      const scoreMap = new Map(predictedItems.map((p) => [p.id, p.score]));

      // Sort by prediction score (higher first), then original order
      return [...filtered].sort((a, b) => {
        const scoreA = scoreMap.get(a.id) ?? 0;
        const scoreB = scoreMap.get(b.id) ?? 0;
        return (scoreB as number) - (scoreA as number);
      });
    }

    return filtered;
  }, [allowedItems, enableAI, reorderByPrediction, predictedItems]);

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
      <div
        className="flex flex-col gap-1"
        role="group"
        aria-label="Primary navigation"
      >
        {visibleNavItems.map((item) => {
          const isPredicted = predictedItemIds.has(item.id);
          return (
            <button
              key={item.id}
              type="button"
              data-testid={`nav-${item.id}`}
              aria-label={item.label}
              title={isPredicted ? `${item.label} (Suggested)` : item.label}
              onClick={() => handleNavClick(item)}
              className={cn(
                "p-2 rounded-lg transition-all relative",
                "focus:outline-none focus:ring-2 focus:ring-primary-500",
                activeNavItem === item.id &&
                  "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300",
                activeNavItem !== item.id &&
                  "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
              )}
            >
              {item.icon}
              {/* AI Prediction Indicator */}
              {enableAI && isPredicted && !predictionsLoading && (
                <span
                  data-testid="nav-prediction-indicator"
                  className={cn(
                    "absolute -top-0.5 -right-0.5 w-2 h-2",
                    "bg-amber-400 dark:bg-amber-500 rounded-full",
                    "animate-pulse",
                  )}
                  aria-label="AI suggested"
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1" aria-hidden="true" />

      {/* Bottom icons - RBAC filtered */}
      <div
        className="flex flex-col gap-1"
        role="group"
        aria-label="Secondary navigation"
      >
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
