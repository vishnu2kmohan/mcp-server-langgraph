/**
 * Property Panels
 *
 * Context-sensitive property panels for the RightSidebar.
 * Each panel displays relevant information for a specific tab type.
 */

export { ChatProperties, type ChatPropertiesProps } from "./ChatProperties";
export {
  WorkflowProperties,
  type WorkflowPropertiesProps,
} from "./WorkflowProperties";
export {
  ProjectProperties,
  type ProjectPropertiesProps,
} from "./ProjectProperties";
export {
  SettingsProperties,
  type SettingsPropertiesProps,
} from "./SettingsProperties";
export { CostProperties, type CostPropertiesProps } from "./CostProperties";
export {
  ObservabilityProperties,
  type ObservabilityPropertiesProps,
} from "./ObservabilityProperties";
export {
  GenericProperties,
  type GenericPropertiesProps,
} from "./GenericProperties";

// Shared components
export { PropertySection, type PropertySectionProps } from "./PropertySection";
export { PropertyRow, type PropertyRowProps } from "./PropertyRow";
