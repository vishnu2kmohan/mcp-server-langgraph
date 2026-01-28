/**
 * SkillCard Component
 *
 * Displays a skill in the marketplace browser with install/installed state.
 * Shows skill name, description, version, tags, and action buttons.
 *
 * @see SkillCard.test.tsx for TDD test cases
 */

import { Button } from "@/components/UI";
import type { SkillMetadata } from "../../types/skills";

interface SkillCardProps {
  /** Skill metadata to display */
  skill: SkillMetadata;
  /** Whether the skill is already installed */
  isInstalled: boolean;
  /** Callback when install button is clicked */
  onInstall: () => void;
  /** Whether installation is in progress */
  isInstalling: boolean;
  /** Optional callback when card is clicked for details */
  onViewDetails?: (skill: SkillMetadata) => void;
}

export function SkillCard({
  skill,
  isInstalled,
  onInstall,
  isInstalling,
  onViewDetails,
}: SkillCardProps): JSX.Element {
  const handleCardClick = (e: React.MouseEvent) => {
    // Don't trigger if clicking on the button
    if ((e.target as HTMLElement).closest("button")) {
      return;
    }
    onViewDetails?.(skill);
  };

  return (
    <div
      data-testid={`skills-card-${skill.name}`}
      onClick={handleCardClick}
      className="flex flex-col rounded-lg border border-neutral-6 bg-neutral-2 p-4 transition-colors hover:border-neutral-7 hover:bg-neutral-3"
      role="article"
    >
      {/* Header: Name + Version */}
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-12">{skill.name}</h3>
        <span className="rounded bg-neutral-4 px-2 py-0.5 text-xs text-neutral-11">
          v{skill.version}
        </span>
      </div>

      {/* Description */}
      <p className="mb-3 flex-1 text-sm text-neutral-11">{skill.description}</p>

      {/* Tags */}
      <div className="mb-3 flex flex-wrap gap-1">
        {skill.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="rounded-full bg-primary-3 px-2 py-0.5 text-xs text-primary-11"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Action */}
      <div className="mt-auto">
        {isInstalled ? (
          <span className="inline-flex items-center gap-1 text-sm font-medium text-success-11">
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            Installed
          </span>
        ) : (
          <Button
            onClick={onInstall}
            disabled={isInstalling}
            loading={isInstalling}
            variant="primary"
            size="sm"
          >
            {isInstalling ? "Installing..." : "Install"}
          </Button>
        )}
      </div>
    </div>
  );
}
