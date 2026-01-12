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
                className="p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg"
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {isEnabled ? (
                      <Check size={16} className="text-success-500" />
                    ) : (
                      <X
                        size={16}
                        className="text-neutral-400 dark:text-neutral-400"
                      />
                    )}
                    <span className="font-medium text-neutral-900 dark:text-neutral-100">
                      {orchestrator.displayName}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${
                      isEnabled
                        ? "bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400"
                        : "bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
                    }`}
                  >
                    {isEnabled ? "Enabled" : "Disabled"}
                  </span>
                </div>

                {/* Description */}
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
                  {orchestrator.description}
                </p>

                {/* Task Categories */}
                {orchestrator.taskCategories.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {orchestrator.taskCategories.map((category) => (
                      <span
                        key={category}
                        className="px-2 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 rounded"
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
