/**
 * Layout Components
 *
 * Reusable layout components for the frontend application.
 * Barrel file for clean imports: import { Component } from '../components/Layout';
 */

// =============================================================================
// Dockable Layout (DevTools-style panels)
// =============================================================================

export {
  DockableLayout,
  DockablePanelGroup,
  DockablePanel,
  DockableResizeHandle,
  PanelHeader,
  PanelContent,
} from "./DockableLayout";

// =============================================================================
// Bottom Panel Sub-Components
// =============================================================================

export { ActivityLog } from "./ActivityLog";
export type { ActivityLogProps } from "./ActivityLog";

export { ProblemsPanel } from "./ProblemsPanel";
export type { ProblemsPanelProps } from "./ProblemsPanel";

export { InspectorPanel } from "./InspectorPanel";
export type { InspectorPanelProps } from "./InspectorPanel";

export type {
  DockableLayoutProps,
  DockablePanelGroupProps,
  DockablePanelProps,
  DockableResizeHandleProps,
  PanelHeaderProps,
  PanelContentProps,
  ImperativePanelHandle,
} from "./DockableLayout";
