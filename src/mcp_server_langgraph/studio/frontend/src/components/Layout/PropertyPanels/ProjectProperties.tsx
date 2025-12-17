/**
 * ProjectProperties Component
 *
 * Property panel for projects, showing project info,
 * resource counts, and owner details.
 */

import { useGetProjectQuery } from "../../../api";
import type { TabState } from "../../../store/slices/workspaceSlice";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";

// =============================================================================
// Types
// =============================================================================

export interface ProjectPropertiesProps {
  tab: TabState;
  isSectionExpanded: (id: string) => boolean;
  onToggleSection: (id: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function ProjectProperties({
  tab,
  isSectionExpanded,
  onToggleSection,
}: ProjectPropertiesProps) {
  const { data: project, isLoading } = useGetProjectQuery(tab.entityId || "", {
    skip: !tab.entityId,
  });

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  if (isLoading) {
    return (
      <div className="p-4 text-xs text-gray-500 dark:text-gray-400">
        Loading project...
      </div>
    );
  }

  return (
    <div data-testid="project-properties">
      <PropertySection
        id="project-info"
        title="Project Info"
        isExpanded={isSectionExpanded("project-info")}
        onToggle={() => onToggleSection("project-info")}
      >
        <PropertyRow label="ID" value={tab.entityId || "N/A"} mono />
        <PropertyRow label="Name" value={project?.name || tab.title} />
        <PropertyRow label="Status" value={project?.status || "unknown"} />
        <PropertyRow label="Created" value={formatDate(project?.created_at)} />
        <PropertyRow label="Updated" value={formatDate(project?.updated_at)} />
      </PropertySection>

      <PropertySection
        id="owner-info"
        title="Owner"
        isExpanded={isSectionExpanded("owner-info")}
        onToggle={() => onToggleSection("owner-info")}
      >
        <PropertyRow label="Name" value={project?.owner_name || "Unknown"} />
        <PropertyRow label="ID" value={project?.owner_id || "N/A"} mono />
      </PropertySection>

      <PropertySection
        id="resources-info"
        title="Resources"
        isExpanded={isSectionExpanded("resources-info")}
        onToggle={() => onToggleSection("resources-info")}
        badge={
          <span className="text-[10px] text-gray-400">
            {(project?.session_count ?? 0) +
              (project?.workflow_count ?? 0) +
              (project?.connection_count ?? 0)}{" "}
            total
          </span>
        }
      >
        <PropertyRow label="Sessions" value={project?.session_count ?? 0} />
        <PropertyRow label="Workflows" value={project?.workflow_count ?? 0} />
        <PropertyRow
          label="Connections"
          value={project?.connection_count ?? 0}
        />
      </PropertySection>

      {project?.description && (
        <PropertySection
          id="description-info"
          title="Description"
          isExpanded={isSectionExpanded("description-info")}
          onToggle={() => onToggleSection("description-info")}
        >
          <p className="text-xs text-gray-600 dark:text-gray-400">
            {project.description}
          </p>
        </PropertySection>
      )}
    </div>
  );
}

export default ProjectProperties;
