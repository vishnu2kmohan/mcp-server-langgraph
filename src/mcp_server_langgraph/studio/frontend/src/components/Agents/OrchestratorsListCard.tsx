/**
 * OrchestratorsListCard
 *
 * Displays the orchestrator registry with feature flag status
 * and task categories for each orchestrator.
 *
 * Read-only display for Sprint 2 (V1).
 * Visible only to admin and developer personas.
 */

import { useSelector } from "react-redux";
import { Network, Check, X } from "lucide-react";
import { selectPersona } from "../../store/slices/personaSlice";
import { Card, CardTitle, CardContent } from "../UI/Card";
import type { OrchestratorInfo } from "../../types/api";

interface OrchestratorsListCardProps {
  orchestrators: OrchestratorInfo[];
  featureFlags: Record<string, boolean>;
}

export function OrchestratorsListCard({
  orchestrators,
  featureFlags,
}: OrchestratorsListCardProps) {
  const persona = useSelector(selectPersona);

  // Only show for admin and developer personas
  if (!["admin", "developer"].includes(persona)) {
    return null;
  }

  // Don't render if no orchestrators
  if (!orchestrators || orchestrators.length === 0) {
    return null;
  }

  return (
    <Card data-testid="orchestrators-list-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Network size={24} className="text-indigo-500" />
          <CardTitle>Orchestrators</CardTitle>
        </div>
        <span className="px-2 py-1 text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-full">
          {orchestrators.length} orchestrators
        </span>
      </div>

      <CardContent>
        <div className="space-y-3">
          {orchestrators.map((orchestrator) => {
            const isEnabled = featureFlags[orchestrator.featureFlag] ?? false;

            return (
              <div
                key={orchestrator.name}
                className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg"
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {isEnabled ? (
                      <Check size={16} className="text-green-500" />
                    ) : (
                      <X size={16} className="text-gray-400" />
                    )}
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {orchestrator.displayName}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${
                      isEnabled
                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                    }`}
                  >
                    {isEnabled ? "Enabled" : "Disabled"}
                  </span>
                </div>

                {/* Description */}
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  {orchestrator.description}
                </p>

                {/* Task Categories */}
                {orchestrator.taskCategories.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {orchestrator.taskCategories.map((category) => (
                      <span
                        key={category}
                        className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded"
                      >
                        {category}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
