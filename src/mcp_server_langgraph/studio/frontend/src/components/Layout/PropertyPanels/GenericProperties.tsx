/**
 * GenericProperties Component
 *
 * Fallback property panel for unknown tab types.
 */

import type { TabState } from "../../../store/slices/workspaceSlice";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";

// =============================================================================
// Types
// =============================================================================

export interface GenericPropertiesProps {
  tab: TabState;
  isSectionExpanded: (id: string) => boolean;
  onToggleSection: (id: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function GenericProperties({
  tab,
  isSectionExpanded,
  onToggleSection,
}: GenericPropertiesProps) {
  return (
    <div data-testid="generic-properties">
      <PropertySection
        id="document-info"
        title="Document Info"
        isExpanded={isSectionExpanded("document-info")}
        onToggle={() => onToggleSection("document-info")}
      >
        <PropertyRow label="ID" value={tab.id} mono />
        <PropertyRow label="Title" value={tab.title} />
        <PropertyRow label="Type" value={tab.type} />
        {tab.entityId && (
          <PropertyRow label="Entity ID" value={tab.entityId} mono />
        )}
      </PropertySection>
    </div>
  );
}

export default GenericProperties;
