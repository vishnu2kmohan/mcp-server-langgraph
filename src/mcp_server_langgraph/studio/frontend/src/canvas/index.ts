/**
 * Canvas Module - Phase 1
 *
 * Exports for the Studio Canvas system components.
 */

export { CanvasWorkspace, type CanvasWorkspaceProps } from "./CanvasWorkspace";
export { CanvasArtifact, type CanvasArtifactProps } from "./CanvasArtifact";
export { CanvasTabs, type CanvasTabsProps, type TabType } from "./CanvasTabs";
export { VersionTimeline, type VersionTimelineProps } from "./VersionTimeline";
export { VersionDiff, type VersionDiffProps } from "./VersionDiff";
export {
  ArtifactActions,
  type ArtifactActionsProps,
  type ExportFormat,
} from "./ArtifactActions";
export {
  ConnectedCanvasPanel,
  type ConnectedCanvasPanelProps,
} from "./ConnectedCanvasPanel";
export { getVisibleTabs } from "./canvasUtils";
