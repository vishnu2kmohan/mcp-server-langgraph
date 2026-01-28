/**
 * UpdatesContent - Skill updates tab
 *
 * Displays available skill updates with:
 * - Count of available updates
 * - "Apply All Updates" bulk action
 * - Success state when all skills are up to date
 *
 * @see SkillsPage.tsx for usage context
 */

import { CheckCircle, Loader2, ArrowUpCircle } from "lucide-react";
import { Button } from "@/components/UI";

export interface UpdatesContentProps {
  /** List of available updates */
  updates: unknown[];
  /** Callback to apply all updates */
  onApplyAll: () => void;
  /** Whether updates are being applied */
  isApplying: boolean;
}

export function UpdatesContent({
  updates,
  onApplyAll,
  isApplying,
}: UpdatesContentProps): JSX.Element {
  if (updates.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center h-64 text-neutral-11"
        data-testid="skills-updates-empty"
      >
        <CheckCircle className="w-12 h-12 text-success-11 mb-4" />
        <p className="text-lg font-medium text-neutral-12">
          All skills are up to date
        </p>
        <p className="text-sm">No updates available at this time.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="skills-updates-list">
      <div className="flex items-center justify-between">
        <p className="text-neutral-11">{updates.length} update(s) available</p>
        <Button
          variant="primary"
          className="flex gap-2 focus-visible:ring-2 focus-visible:ring-primary-9"
          onClick={onApplyAll}
          disabled={isApplying}
          data-testid="skills-apply-updates"
        >
          {isApplying ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ArrowUpCircle className="w-4 h-4" />
          )}
          Apply All Updates
        </Button>
      </div>
    </div>
  );
}
