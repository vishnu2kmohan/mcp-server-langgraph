/**
 * Compliance Module Exports
 *
 * Phase 5: Compliance Dashboards
 * Exports all compliance-related components and types.
 */

export { SOC2Panel, type SOC2Control, type SOC2PanelProps } from "./SOC2Panel";

export {
  HIPAAPanel,
  type HIPAAControl,
  type HIPAACategory,
  type HIPAAPanelProps,
} from "./HIPAAPanel";

export { GDPRPanel, type GDPRControl, type GDPRPanelProps } from "./GDPRPanel";

export {
  FedRAMPPanel,
  type FedRAMPControl,
  type FedRAMPAuthStatus,
  type FedRAMPPanelProps,
  type ImpactLevel,
  type AuthLevel,
} from "./FedRAMPPanel";

export {
  ComplianceDashboard,
  type ComplianceSummary,
  type FrameworkSummary,
  type ComplianceStatus,
  type ComplianceDashboardProps,
} from "./ComplianceDashboard";

// Re-export shared type (defined in multiple modules)
export type { ControlStatus } from "./SOC2Panel";
