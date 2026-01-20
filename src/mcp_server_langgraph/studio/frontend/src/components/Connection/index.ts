/**
 * Connection Components
 *
 * Exports all MCP connection-related components.
 */

export { ConnectionDialog } from "./ConnectionDialog";
export { ConnectionHealthDashboard } from "./ConnectionHealthDashboard";
export { ConnectionTemplateSelector } from "./ConnectionTemplateSelector";
export { ConnectionBulkActions } from "./ConnectionBulkActions";
export { ConnectionAuditLog } from "./ConnectionAuditLog";

// ADR-0102: Connections Page Redesign Components
export { ConnectorCard } from "./ConnectorCard";
export { ConnectorDirectory } from "./ConnectorDirectory";
export { CapabilitiesTab } from "./CapabilitiesTab";

// ADR-0102 Phase 6: Scope Components
export { ScopeBadge, type ScopeBadgeProps } from "./ScopeBadge";
export { ScopeSelector, type ScopeSelectorProps } from "./ScopeSelector";
