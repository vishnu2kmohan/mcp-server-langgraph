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
import { useCallback, useMemo, useEffect, forwardRef, useState } from "react";
import { useNavigate, useLocation } from "react-router";
import { useReducedMotion } from "motion/react";
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
  DollarSign,
  FolderKanban,
  Boxes,
  Plug,
  ClipboardCheck,
  Scale,
  ChevronDown,
  ChevronRight,
  Package,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectActiveNavItem,
  setActiveNavItem,
} from "../store/slices/canvasSlice";
import {
  selectSidebarItems,
  selectUsername,
} from "../store/slices/personaSlice";
import {
  selectRecentPages,
  selectCurrentPage,
  trackPageVisit,
} from "../store/slices/sessionSlice";
import { cn } from "../utils/cn";
import { storage, STORAGE_KEYS } from "../utils/storage";
import { useNavPrediction } from "../hooks/useUXIntelligence";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  path?: string;
  /** Group this item belongs to (for collapsible groups) */
  group?: NavGroupId;
}

/** Navigation group identifiers (internal to ActivityBar) */
type NavGroupId = "core" | "ai-data" | "observability" | "admin";

/** Navigation group metadata (internal to ActivityBar) */
interface NavGroup {
  id: NavGroupId;
  label: string;
  items: string[]; // Nav item IDs in this group
}

// =============================================================================
// Navigation Constants
// =============================================================================

/**
 * NAV_GROUPS - Navigation group definitions for collapsible sections
 *
 * Organized by functional groups for logical user journey.
 * Each group contains item IDs that belong to it.
 * (Internal to ActivityBar - not exported)
 */
const NAV_GROUPS: NavGroup[] = [
  {
    id: "core",
    label: "Core",
    items: ["projects", "chat", "workflows"],
  },
  {
    id: "ai-data",
    label: "AI & Data",
    items: ["agents", "vectors", "connections", "artifacts"],
  },
  {
    id: "observability",
    label: "Observability",
    items: ["observability", "cost"],
  },
  {
    id: "admin",
    label: "Admin",
    items: ["admin", "skills", "audit", "compliance"],
  },
];

/**
 * NAV_ITEMS - Main navigation items (persona-filtered)
 *
 * Organized by functional groups for logical user journey:
 * - Core Work: projects, chat, workflows
 * - AI & Data: agents, mcp, vectors, connections, artifacts
 * - Observability: traces, observability, cost
 * - Admin: admin, audit, compliance (persona-gated)
 */
export const NAV_ITEMS: NavItem[] = [
  // === Core Work ===
  {
    id: "projects",
    icon: <FolderKanban size={20} />,
    label: "Projects",
    path: "/studio/projects",
    group: "core",
  },
  {
    id: "chat",
    icon: <MessageSquare size={20} />,
    label: "Chat",
    path: "/studio/chat",
    group: "core",
  },
  {
    id: "workflows",
    icon: <GitBranch size={20} />,
    label: "Workflows",
    path: "/studio/workflows",
    group: "core",
  },
  // === AI & Data ===
  {
    id: "agents",
    icon: <Cpu size={20} />,
    label: "Agents",
    path: "/studio/agents",
    group: "ai-data",
  },
  {
    id: "vectors",
    icon: <Boxes size={20} />,
    label: "Vectors",
    path: "/studio/vectors",
    group: "ai-data",
  },
  {
    id: "connections",
    icon: <Plug size={20} />,
    label: "Connections",
    path: "/studio/connections",
    group: "ai-data",
  },
  {
    id: "artifacts",
    icon: <FileText size={20} />,
    label: "Artifacts",
    path: "/studio/artifacts",
    group: "ai-data",
  },
  // === Observability ===
  {
    id: "observability",
    icon: <Activity size={20} />,
    label: "Observability",
    path: "/studio/observability",
    group: "observability",
  },
  {
    id: "cost",
    icon: <DollarSign size={20} />,
    label: "Cost",
    path: "/studio/cost",
    group: "observability",
  },
  // === Admin (persona-gated) ===
  {
    id: "admin",
    icon: <Shield size={20} />,
    label: "Admin",
    path: "/studio/admin",
    group: "admin",
  },
  {
    id: "skills",
    icon: <Package size={20} />,
    label: "Skills",
    path: "/studio/skills",
    group: "admin",
  },
  {
    id: "audit",
    icon: <ClipboardCheck size={20} />,
    label: "Audit",
    path: "/studio/audit",
    group: "admin",
  },
  {
    id: "compliance",
    icon: <Scale size={20} />,
    label: "Compliance",
    path: "/studio/compliance",
    group: "admin",
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

// NOTE: KNOWN_NAV_IDS is now defined in navConstants.ts (single source of truth)
// to avoid circular dependencies with React Router.
// The NAV_ITEMS and BOTTOM_ITEMS arrays above should stay in sync with
// NAV_ITEM_IDS and BOTTOM_ITEM_IDS in navConstants.ts.

// =============================================================================
// Component
// =============================================================================

/** Type for collapsed groups state */
type CollapsedGroupsState = Record<NavGroupId, boolean>;

export interface ActivityBarProps {
  className?: string;
  /** Enable AI-powered navigation predictions (Sprint 6) */
  enableAI?: boolean;
  /** Reorder navigation items based on AI predictions */
  reorderByPrediction?: boolean;
  /** Enable collapsible navigation groups (Sprint 4.2) */
  enableCollapsibleGroups?: boolean;
}

export const ActivityBar = forwardRef<HTMLElement, ActivityBarProps>(
  function ActivityBar(
    {
      className,
      enableAI = false,
      reorderByPrediction = false,
      enableCollapsibleGroups = false,
    },
    ref,
  ) {
    const dispatch = useAppDispatch();
    const navigate = useNavigate();
    const location = useLocation();
    const activeNavItem = useAppSelector(selectActiveNavItem);
    // WCAG 2.2 AA: Respect user's reduced motion preference
    const prefersReducedMotion = useReducedMotion();

    // Sprint 4.2: Collapsible groups state with storage persistence
    const [collapsedGroups, setCollapsedGroups] =
      useState<CollapsedGroupsState>(() => {
        if (!enableCollapsibleGroups) {
          return {} as CollapsedGroupsState;
        }
        return (
          storage.get<CollapsedGroupsState>(
            STORAGE_KEYS.ACTIVITY_BAR_COLLAPSED_GROUPS,
          ) ?? ({} as CollapsedGroupsState)
        );
      });

    // Toggle group collapse state
    const toggleGroupCollapse = useCallback((groupId: NavGroupId) => {
      setCollapsedGroups((prev) => {
        const next = { ...prev, [groupId]: !prev[groupId] };
        storage.set(STORAGE_KEYS.ACTIVITY_BAR_COLLAPSED_GROUPS, next);
        return next;
      });
    }, []);

    // RBAC: Get allowed sidebar items from persona slice (deny-by-default)
    const allowedItems = useAppSelector(selectSidebarItems);

    // Phase 4.2: Get navigation tracking data for AI predictions
    const username = useAppSelector(selectUsername);
    const recentPages = useAppSelector(selectRecentPages);
    const currentPage = useAppSelector(selectCurrentPage);

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

    // Phase 4.2: Track page visits for AI predictions
    useEffect(() => {
      // Only track if we're on a studio page
      if (location.pathname.startsWith("/studio/")) {
        dispatch(trackPageVisit(location.pathname));
      }
    }, [location.pathname, dispatch]);

    // AI Navigation Predictions (Sprint 6)
    // Phase 4.2: Now uses real navigation tracking data from sessionSlice
    const { predictedItems, isLoading: predictionsLoading } = useNavPrediction({
      userId: username ?? "",
      currentPage: currentPage || activeNavItem || "chat",
      recentPages: recentPages,
      enabled: enableAI,
    });

    // Create a set of predicted item IDs for quick lookup
    const predictedItemIds = useMemo(() => {
      if (!enableAI || !predictedItems?.length) return new Set<string>();
      return new Set(predictedItems.map((p) => p.id));
    }, [enableAI, predictedItems]);

    // Filter navigation items based on persona permissions
    const visibleNavItems = useMemo(() => {
      const filtered = NAV_ITEMS.filter((item) =>
        allowedItems.includes(item.id),
      );

      // Optionally reorder based on predictions
      if (
        enableAI &&
        reorderByPrediction &&
        (predictedItems?.length ?? 0) > 0
      ) {
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

    // Sprint 4.2: Compute visible groups with their filtered items (for collapsible mode)
    const visibleGroups = useMemo(() => {
      if (!enableCollapsibleGroups) return [];

      return NAV_GROUPS.map((group) => {
        // Filter items in this group by RBAC permissions
        const groupItems = NAV_ITEMS.filter(
          (item) => item.group === group.id && allowedItems.includes(item.id),
        );
        return {
          ...group,
          visibleItems: groupItems,
        };
      }).filter((group) => group.visibleItems.length > 0); // Only show groups with visible items
    }, [enableCollapsibleGroups, allowedItems]);

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
        ref={ref}
        data-testid="activity-bar"
        aria-label="Main navigation"
        className={cn(
          "flex flex-col items-center w-14 h-full",
          "bg-neutral-2",
          "border-r border-neutral-5",
          className,
        )}
      >
        {/* Primary nav - scrollable */}
        <div className="flex-1 min-h-0 overflow-y-auto py-2 w-full flex flex-col items-center">
        {/* Main navigation icons - RBAC filtered */}
        {/* Sprint 4.2: Render as collapsible groups or flat list */}
        {enableCollapsibleGroups ? (
          /* Collapsible Groups Mode */
          <div
            className="flex flex-col gap-0.5"
            role="group"
            aria-label="Primary navigation"
          >
            {visibleGroups.map((group) => {
              const isCollapsed = collapsedGroups[group.id] ?? false;
              return (
                <div key={group.id} className="flex flex-col gap-0.5">
                  {/* Group Header (collapsible) */}
                  <Button
                    type="button"
                    variant="ghost"
                    data-testid={`nav-group-${group.id}`}
                    aria-label={`${group.label} group`}
                    aria-expanded={!isCollapsed}
                    aria-controls={`nav-group-items-${group.id}`}
                    title={`${group.label} (${isCollapsed ? "Expand" : "Collapse"})`}
                    onClick={() => toggleGroupCollapse(group.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleGroupCollapse(group.id);
                      }
                    }}
                    className={cn(
                      "p-1.5 rounded-lg flex items-center justify-center",
                      "min-h-[44px] min-w-[44px]", // WCAG 2.5.8 AAA touch target
                      !prefersReducedMotion && "transition-all",
                      "text-neutral-9",
                      "hover:bg-neutral-3",
                      "focus:outline-none focus:ring-2 focus:ring-primary-7",
                    )}
                  >
                    {isCollapsed ? (
                      <ChevronRight size={14} />
                    ) : (
                      <ChevronDown size={14} />
                    )}
                  </Button>
                  {/* Group Items (shown when expanded) */}
                  {!isCollapsed && (
                    <div
                      id={`nav-group-items-${group.id}`}
                      className="flex flex-col gap-0.5"
                    >
                      {group.visibleItems.map((item) => {
                        const isPredicted = predictedItemIds.has(item.id);
                        return (
                          <Button
                            key={item.id}
                            type="button"
                            variant="ghost"
                            data-testid={`nav-${item.id}`}
                            aria-label={item.label}
                            title={
                              isPredicted
                                ? `${item.label} (Suggested)`
                                : item.label
                            }
                            onClick={() => handleNavClick(item)}
                            className={cn(
                              "p-2 rounded-lg relative",
                              "min-h-[44px] min-w-[44px]", // WCAG 2.5.8 AAA touch target
                              !prefersReducedMotion && "transition-all",
                              "focus:outline-none focus:ring-2 focus:ring-primary-7",
                              activeNavItem === item.id &&
                                "bg-primary-3 dark:bg-primary-4 text-primary-11 dark:text-primary-9",
                              activeNavItem !== item.id &&
                                "text-neutral-10 hover:bg-neutral-3",
                            )}
                          >
                            {item.icon}
                            {/* AI Prediction Indicator */}
                            {enableAI && isPredicted && !predictionsLoading && (
                              <span
                                data-testid="nav-prediction-indicator"
                                className={cn(
                                  "absolute -top-0.5 -right-0.5 w-2 h-2",
                                  "bg-primary-9 dark:bg-primary-9 rounded-full",
                                  !prefersReducedMotion && "animate-pulse",
                                )}
                                aria-label="AI suggested"
                              />
                            )}
                          </Button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          /* Flat List Mode (default) */
          <div
            className="flex flex-col gap-1"
            role="group"
            aria-label="Primary navigation"
          >
            {visibleNavItems.map((item) => {
              const isPredicted = predictedItemIds.has(item.id);
              return (
                <Button
                  key={item.id}
                  type="button"
                  variant="ghost"
                  data-testid={`nav-${item.id}`}
                  aria-label={item.label}
                  title={isPredicted ? `${item.label} (Suggested)` : item.label}
                  onClick={() => handleNavClick(item)}
                  className={cn(
                    "p-2 rounded-lg relative",
                    "min-h-[44px] min-w-[44px]", // WCAG 2.5.8 AAA touch target
                    !prefersReducedMotion && "transition-all",
                    "focus:outline-none focus:ring-2 focus:ring-primary-7",
                    activeNavItem === item.id &&
                      "bg-primary-3 dark:bg-primary-4 text-primary-11 dark:text-primary-9",
                    activeNavItem !== item.id &&
                      "text-neutral-10 hover:bg-neutral-3",
                  )}
                >
                  {item.icon}
                  {/* AI Prediction Indicator */}
                  {enableAI && isPredicted && !predictionsLoading && (
                    <span
                      data-testid="nav-prediction-indicator"
                      className={cn(
                        "absolute -top-0.5 -right-0.5 w-2 h-2",
                        "bg-primary-9 dark:bg-primary-9 rounded-full",
                        !prefersReducedMotion && "animate-pulse",
                      )}
                      aria-label="AI suggested"
                    />
                  )}
                </Button>
              );
            })}
          </div>
        )}
        </div>
        {/* Bottom icons - RBAC filtered, pinned to bottom */}
        <div
          className="flex-shrink-0 flex flex-col gap-1 py-2 border-t border-neutral-5"
          role="group"
          aria-label="Secondary navigation"
        >
          <Button
            type="button"
            variant="ghost"
            data-testid="command-palette-button"
            aria-label="Command Palette"
            title="Command Palette (⌘K)"
            onClick={handleCommandPaletteClick}
            className={cn(
              "p-2 rounded-lg",
              "min-h-[44px] min-w-[44px]", // WCAG 2.5.8 AAA touch target
              !prefersReducedMotion && "transition-all",
              "text-neutral-10",
              "hover:bg-neutral-3",
              "focus:outline-none focus:ring-2 focus:ring-primary-7",
            )}
          >
            <Command size={20} />
          </Button>
          {visibleBottomItems.map((item) => (
            <Button
              key={item.id}
              type="button"
              variant="ghost"
              data-testid={`nav-${item.id}`}
              aria-label={item.label}
              title={item.label}
              onClick={() => handleNavClick(item)}
              className={cn(
                "p-2 rounded-lg",
                "min-h-[44px] min-w-[44px]", // WCAG 2.5.8 AAA touch target
                !prefersReducedMotion && "transition-all",
                "focus:outline-none focus:ring-2 focus:ring-primary-7",
                activeNavItem === item.id &&
                  "bg-primary-3 dark:bg-primary-4 text-primary-11 dark:text-primary-9",
                activeNavItem !== item.id &&
                  "text-neutral-10 hover:bg-neutral-3",
              )}
            >
              {item.icon}
            </Button>
          ))}
        </div>
      </nav>
    );
  },
);

// Display name for DevTools
ActivityBar.displayName = "ActivityBar";
