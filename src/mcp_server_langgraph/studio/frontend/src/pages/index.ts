/**
 * Page Components Index
 *
 * Central export for all page wrapper components used by the router.
 * Pages compose existing components with data fetching and state management.
 */

export { WorkflowsPage } from "./WorkflowsPage";
export { WorkflowsListPage } from "./WorkflowsListPage";
export { SharedWorkflowsPage } from "./SharedWorkflowsPage";
// ChatPage REMOVED - deprecated, replaced by StudioShellLayout 3-panel canvas layout
// SessionsPage REMOVED - functionality now in StudioShellLayout SessionNav panel
// MCPPage REMOVED - deprecated, functionality consolidated into ConnectionsPage Capabilities tab (ADR-0102)
export { ObservabilityPage } from "./ObservabilityPage";
export { SettingsPage } from "./SettingsPage";
export { AdminDashboardPage } from "./AdminDashboardPage";
export { AuditLogPage } from "./AuditLogPage";
export { ConnectionsPage } from "./ConnectionsPage";
export { OAuth2CallbackPage } from "./OAuth2CallbackPage";
export { ProjectsPage } from "./ProjectsPage";
export { ProjectDetailPage } from "./ProjectDetailPage";
export { AgentsPage } from "./AgentsPage";
export { VectorsPage } from "./VectorsPage";
export { CostPage } from "./CostPage";
export { AnalyticsDashboardPage } from "./AnalyticsDashboardPage";
