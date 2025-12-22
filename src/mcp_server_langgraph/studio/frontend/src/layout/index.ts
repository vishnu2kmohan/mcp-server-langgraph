/**
 * Layout Module - Hybrid Canvas Shell Components
 *
 * Phase 1: HybridShellLayout with resizable panels
 * Exports main layout component and sub-components.
 */

// Main shell layout
export { HybridShellLayout } from "./HybridShellLayout";

// Activity bar (RBAC-aware navigation)
export {
  ActivityBar,
  NAV_ITEMS,
  BOTTOM_ITEMS,
  type NavItem,
  type ActivityBarProps,
} from "./ActivityBar";

// Session navigation (time-travel grouped)
export {
  SessionNav,
  groupSessionsByDate,
  type SessionNavProps,
  type GroupedSessions,
} from "./SessionNav";

// Top bar (minimal header)
export { TopBar, type TopBarProps } from "./TopBar";

// Status bar (agent/connection status)
export {
  StatusBar,
  type StatusBarProps,
  type ConnectionStatus,
} from "./StatusBar";

// User menu dropdown
export {
  UserMenuDropdown,
  type UserMenuDropdownProps,
} from "./UserMenuDropdown";

// Responsive layout utilities
export {
  ResponsiveLayout,
  useBreakpoint,
  type ResponsiveLayoutProps,
  type Breakpoint,
} from "./ResponsiveLayout";

// Resize handle for panels
export { ResizeHandle, type ResizeHandleProps } from "./ResizeHandle";

// Feature flag toggle (dev utility)
export {
  FeatureFlagToggle,
  type FeatureFlagToggleProps,
} from "./FeatureFlagToggle";

// Alert badge for header (ADR-0026)
export { AlertBadge, type AlertBadgeProps } from "./AlertBadge";

// AI Session Card (Sprint 2: Session Intelligence)
export { AISessionCard, type AISessionCardProps } from "./AISessionCard";
