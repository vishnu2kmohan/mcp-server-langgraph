/**
 * SkillDetails Modal Component
 *
 * Displays full skill information in a modal dialog.
 * Shows all metadata and provides install action.
 *
 * @see SkillDetails.test.tsx for TDD test cases
 */

import { useEffect } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/UI";
import type { SkillMetadata } from "../../types/skills";

interface SkillDetailsProps {
  /** Skill to display (null when closed) */
  skill: SkillMetadata | null;
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Callback when install button is clicked */
  onInstall: () => void;
  /** Whether the skill is already installed */
  isInstalled: boolean;
  /** Whether installation is in progress */
  isInstalling: boolean;
}

export function SkillDetails({
  skill,
  isOpen,
  onClose,
  onInstall,
  isInstalled,
  isInstalling,
}: SkillDetailsProps): JSX.Element | null {
  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isOpen) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  // Don't render if closed or no skill
  if (!isOpen || !skill) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="skill-details-title"
        data-testid="skill-details-modal"
        className="relative mx-4 max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-lg bg-neutral-1 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <Button
          onClick={onClose}
          aria-label="Close"
          variant="ghost"
          size="icon"
          className="absolute right-4 top-4"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </Button>

        {/* Header */}
        <div className="mb-4 pr-8">
          <h2
            id="skill-details-title"
            className="text-xl font-semibold text-neutral-12"
          >
            {skill.name}
          </h2>
          <div className="mt-1 flex items-center gap-2 text-sm text-neutral-11">
            <span>v{skill.version}</span>
            {skill.author && (
              <>
                <span>•</span>
                <span>{skill.author}</span>
              </>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="mb-4 text-sm text-neutral-11">{skill.description}</p>

        {/* Tags */}
        <div className="mb-6 flex flex-wrap gap-2">
          {skill.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-primary-3 px-3 py-1 text-sm text-primary-11"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Action */}
        <div className="flex justify-end">
          {isInstalled ? (
            <span className="inline-flex items-center gap-2 rounded-md bg-success-3 px-4 py-2 text-sm font-medium text-success-11">
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
            >
              Install
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
