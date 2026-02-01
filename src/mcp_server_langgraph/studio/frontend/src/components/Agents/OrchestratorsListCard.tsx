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
          <Network size={24} className="text-primary-9" />
          <CardTitle>Orchestrators</CardTitle>
        </div>
        <span className="px-2 py-1 text-xs bg-primary-3 dark:bg-primary-4 text-primary-11 dark:text-primary-7 rounded-full">
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
                className="p-3 border border-neutral-5 rounded-lg"
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {isEnabled ? (
                      <Check size={16} className="text-success-9" />
                    ) : (
                      <X size={16} className="text-neutral-9" />
                    )}
                    <span className="font-medium text-neutral-12">
                      {orchestrator.displayName}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${
                      isEnabled
                        ? "bg-success-3 text-success-11 bg-success-4 dark:text-success-7"
                        : "bg-neutral-2 text-neutral-11"
                    }`}
                  >
                    {isEnabled ? "Enabled" : "Disabled"}
                  </span>
                </div>

                {/* Description */}
                <p className="text-sm text-neutral-11 mb-2">
                  {orchestrator.description}
                </p>

                {/* Task Categories */}
                {orchestrator.taskCategories.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {orchestrator.taskCategories.map((category) => (
                      <span
                        key={category}
                        className="px-2 py-0.5 text-xs bg-neutral-2 text-neutral-11 rounded"
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
