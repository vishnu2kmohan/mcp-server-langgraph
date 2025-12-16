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

export type {
  DockableLayoutProps,
  DockablePanelGroupProps,
  DockablePanelProps,
  DockableResizeHandleProps,
  PanelHeaderProps,
  PanelContentProps,
  ImperativePanelHandle,
} from "./DockableLayout";
