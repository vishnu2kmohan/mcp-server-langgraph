/**
 * InstalledContent - Manage installed skills tab
 *
 * Shows a list of locally installed skills with:
 * - Uninstall buttons for each skill
 * - Success checkmarks indicating active skills
 * - Empty state when no skills are installed
 *
 * @see SkillsPage.tsx for usage context
 */

import { Package, Trash2, CheckCircle, HardDrive } from "lucide-react";
import { Button } from "@/components/UI";

export interface InstalledContentProps {
  /** List of installed skill names */
  installedSkills: string[];
  /** Callback when uninstall button is clicked */
  onUninstall: (name: string) => void;
  /** Whether uninstallation is in progress */
  isUninstalling: boolean;
}

export function InstalledContent({
  installedSkills,
  onUninstall,
  isUninstalling,
}: InstalledContentProps): JSX.Element {
  if (installedSkills.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center h-64 text-neutral-11"
        data-testid="skills-installed-empty"
      >
        <HardDrive className="w-12 h-12 text-neutral-9 mb-4" />
        <p className="text-lg font-medium text-neutral-12">
          No skills installed
        </p>
        <p className="text-sm">
          Browse the marketplace to discover and install skills.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="skills-installed-list">
      {installedSkills.map((skillName) => (
        <div
          key={skillName}
          className="flex items-center justify-between p-4 bg-neutral-2 rounded-lg border border-neutral-6"
          data-testid={`skills-installed-${skillName}`}
        >
          <div className="flex items-center gap-3">
            <Package className="w-5 h-5 text-primary-9" />
            <span className="font-medium text-neutral-12">{skillName}</span>
            <CheckCircle className="w-4 h-4 text-success-11" />
          </div>
          <Button
            variant="danger"
            className="flex gap-2 focus-visible:ring-2 focus-visible:ring-error-9"
            onClick={() => onUninstall(skillName)}
            disabled={isUninstalling}
            data-testid={`skills-uninstall-${skillName}`}
          >
            <Trash2 className="w-4 h-4" />
            Uninstall
          </Button>
        </div>
      ))}
    </div>
  );
}
