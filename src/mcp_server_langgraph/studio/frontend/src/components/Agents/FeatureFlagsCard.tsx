/**
 * FeatureFlagsCard
 *
 * Displays agent-related feature flags snapshot with enabled/disabled status.
 *
 * Read-only display for Sprint 2 (V1).
 * Visible only to admin and developer personas.
 */

import { useSelector } from "react-redux";
import { Flag, Check, X } from "lucide-react";
import { selectPersona } from "../../store/slices/personaSlice";
import { Card, CardTitle, CardContent } from "../UI/Card";

interface FeatureFlagsCardProps {
  data: Record<string, boolean> | null | undefined;
}

/**
 * Format flag name for display
 * Removes "enable_" prefix and replaces underscores with spaces
 */
function formatFlagName(flagName: string): string {
  return flagName.replace(/^enable_/, "").replace(/_/g, "_");
}

export function FeatureFlagsCard({ data }: FeatureFlagsCardProps) {
  const persona = useSelector(selectPersona);

  // Only show for admin and developer personas
  if (!["admin", "developer"].includes(persona)) {
    return null;
  }

  // Don't render if no data or empty object
  if (!data || Object.keys(data).length === 0) {
    return null;
  }

  const entries = Object.entries(data);
  const enabledCount = entries.filter(([, value]) => value).length;
  const disabledCount = entries.filter(([, value]) => !value).length;

  return (
    <Card data-testid="feature-flags-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Flag size={24} className="text-primary-9" />
          <CardTitle>Feature Flags</CardTitle>
        </div>
        <span className="px-2 py-1 text-xs bg-neutral-2 text-neutral-11 rounded-full">
          {entries.length} flags
        </span>
      </div>

      <CardContent>
        {/* Summary */}
        <div className="flex gap-4 mb-4">
          <div className="flex items-center gap-2">
            <Check size={16} className="text-success-9" />
            <span className="text-sm text-neutral-11">
              {enabledCount} enabled
            </span>
          </div>
          <div className="flex items-center gap-2">
            <X size={16} className="text-neutral-9" />
            <span className="text-sm text-neutral-11">
              {disabledCount} disabled
            </span>
          </div>
        </div>

        {/* Flags List */}
        <div className="space-y-2">
          {entries.map(([flagName, enabled]) => (
            <div
              key={flagName}
              className="flex items-center justify-between p-2 bg-neutral-1 rounded"
            >
              <span className="text-sm text-neutral-11 font-mono">
                {formatFlagName(flagName)}
              </span>
              <span
                className={`px-2 py-0.5 text-xs font-medium rounded ${
                  enabled
                    ? "bg-success-3 text-success-11 bg-success-4 dark:text-success-7"
                    : "bg-neutral-2 text-neutral-11"
                }`}
              >
                {enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
