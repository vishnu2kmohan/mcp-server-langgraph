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
    <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
      <div className="flex items-center gap-3 mb-4">
        <GitBranch size={24} className="text-indigo-500" />
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          Task Mapping
        </h2>
        <span className="px-2 py-1 text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-full">
          {totalCategories} task categories
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-200 dark:border-neutral-700">
              <th className="text-left py-2 px-3 text-neutral-600 dark:text-neutral-400 font-medium">
                Orchestrator
              </th>
              <th className="text-left py-2 px-3 text-neutral-600 dark:text-neutral-400 font-medium">
                Task Categories
              </th>
              <th className="text-center py-2 px-3 text-neutral-600 dark:text-neutral-400 font-medium">
                Count
              </th>
              <th className="text-center py-2 px-3 text-neutral-600 dark:text-neutral-400 font-medium">
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
                  className="border-b border-neutral-100 dark:border-neutral-700/50 hover:bg-neutral-50 dark:hover:bg-neutral-700/50"
                >
                  <td className="py-3 px-3">
                    <div className="font-medium text-neutral-900 dark:text-neutral-100">
                      {orchestrator.displayName}
                    </div>
                    <div className="text-xs text-neutral-500 dark:text-neutral-400">
                      {orchestrator.description}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-wrap gap-1">
                      {orchestrator.taskCategories?.map((category) => (
                        <span
                          key={category}
                          className="px-2 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 rounded"
                        >
                          {category}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="font-mono text-neutral-900 dark:text-neutral-100">
                      {categoryCount}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-center">
                    {isEnabled ? (
                      <span className="px-2 py-1 text-xs bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-400 rounded-full">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 rounded-full">
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
