/**
 * TaskMappingCard
 *
 * Displays a table mapping orchestrators to their task categories.
 * Shows feature flag status (Active/Inactive) and category count for each orchestrator.
 *
 * Visible only to admin and developer personas.
 */

import { useSelector } from "react-redux";
import { GitBranch } from "lucide-react";
import { selectPersona } from "../../store/slices/personaSlice";
import type { OrchestratorInfo } from "../../types/api";

interface TaskMappingCardProps {
  orchestrators: OrchestratorInfo[];
  featureFlags: Record<string, boolean>;
}

export function TaskMappingCard({
  orchestrators,
  featureFlags,
}: TaskMappingCardProps) {
  const persona = useSelector(selectPersona);

  // Only show for admin and developer personas
  if (!["admin", "developer"].includes(persona)) {
    return null;
  }

  // Don't render if no orchestrators
  if (!orchestrators || orchestrators.length === 0) {
    return null;
  }

  // Calculate total task categories across all orchestrators
  const totalCategories = orchestrators.reduce(
    (sum, orch) => sum + (orch.taskCategories?.length ?? 0),
    0,
  );

  return (
    <div className="bg-neutral-1 rounded-lg border border-neutral-5 p-6">
      <div className="flex items-center gap-3 mb-4">
        <GitBranch size={24} className="text-primary-9" />
        <h2 className="text-xl font-semibold text-neutral-12">
          Task Mapping
        </h2>
        <span className="px-2 py-1 text-xs bg-primary-3 dark:bg-primary-4 text-primary-11 dark:text-primary-7 rounded-full">
          {totalCategories} task categories
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-5">
              <th className="text-left py-2 px-3 text-neutral-11 font-medium">
                Orchestrator
              </th>
              <th className="text-left py-2 px-3 text-neutral-11 font-medium">
                Task Categories
              </th>
              <th className="text-center py-2 px-3 text-neutral-11 font-medium">
                Count
              </th>
              <th className="text-center py-2 px-3 text-neutral-11 font-medium">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {orchestrators.map((orchestrator) => {
              const isEnabled = featureFlags[orchestrator.featureFlag] ?? false;
              const categoryCount = orchestrator.taskCategories?.length ?? 0;

              return (
                <tr
                  key={orchestrator.name}
                  className="border-b border-neutral-a6 hover:bg-neutral-a6"
                >
                  <td className="py-3 px-3">
                    <div className="font-medium text-neutral-12">
                      {orchestrator.displayName}
                    </div>
                    <div className="text-xs text-neutral-10">
                      {orchestrator.description}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-wrap gap-1">
                      {orchestrator.taskCategories?.map((category) => (
                        <span
                          key={category}
                          className="px-2 py-0.5 text-xs bg-neutral-2 text-neutral-11 rounded"
                        >
                          {category}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="font-mono text-neutral-12">
                      {categoryCount}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center">
                    {isEnabled ? (
                      <span className="px-2 py-1 text-xs bg-success-3 bg-success-4 text-success-11 dark:text-success-7 rounded-full">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs bg-neutral-2 text-neutral-10 rounded-full">
                        Inactive
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default TaskMappingCard;
