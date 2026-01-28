/**
 * BrowseContent - Browse marketplace skills tab
 *
 * Displays a grid of available skills with:
 * - Install buttons for each skill
 * - "Installed" badges for already installed skills
 * - Pagination with "Load More" for large skill sets
 * - Error handling with retry capability
 *
 * @see SkillsPage.tsx for usage context
 */

import {
  Package,
  RefreshCw,
  AlertCircle,
  Loader2,
  ArrowUpCircle,
} from "lucide-react";
import { Button } from "@/components/UI";
import { SkillCard } from "./SkillCard";
import type { SkillMetadata } from "../../types/skills";

/** Helper to extract error message from RTK Query errors */
function getErrorMessage(error: unknown): string {
  if (!error) return "An unknown error occurred";

  if (typeof error === "object" && error !== null) {
    const errObj = error as Record<string, unknown>;

    if (errObj.status === 403) {
      return "You don't have permission to perform this action. Contact your administrator if you believe this is an error.";
    }

    if (errObj.data && typeof errObj.data === "object") {
      const data = errObj.data as Record<string, unknown>;
      if (typeof data.detail === "string") {
        return data.detail;
      }
    }

    if (typeof errObj.message === "string") {
      return errObj.message;
    }
  }

  return "An unexpected error occurred. Please try again.";
}

export interface BrowseContentProps {
  /** List of skills to display */
  skills: SkillMetadata[];
  /** List of installed skill names */
  installedSkills: string[];
  /** Callback when install button is clicked */
  onInstall: (name: string) => void;
  /** Whether installation is in progress */
  isInstalling: boolean;
  /** Error from API call, if any */
  error: unknown;
  /** Callback to retry loading skills */
  onRetry: () => void;
  /** Total number of skills (for pagination) */
  total: number;
  /** Callback to load more skills */
  onLoadMore?: () => void;
  /** Whether more skills are being loaded */
  isLoadingMore?: boolean;
  /** Callback when skill card is clicked for details */
  onViewDetails?: (skill: SkillMetadata) => void;
}

export function BrowseContent({
  skills,
  installedSkills,
  onInstall,
  isInstalling,
  error,
  onRetry,
  total,
  onLoadMore,
  isLoadingMore,
  onViewDetails,
}: BrowseContentProps): JSX.Element {
  if (error) {
    const errorObj = error as Record<string, unknown>;
    const is403 = errorObj?.status === 403;
    const errorMessage = getErrorMessage(error);

    return (
      <div
        className="flex flex-col items-center justify-center h-64 text-neutral-11"
        data-testid="skills-browse-error"
      >
        <AlertCircle className="w-12 h-12 text-error-11 mb-4" />
        <p className="text-lg font-medium text-neutral-12">
          {is403 ? "Access Denied" : "Failed to load skills"}
        </p>
        <p className="text-sm text-center max-w-md">
          {is403 ? errorMessage : "Please check your connection and try again."}
        </p>
        {!is403 && (
          <Button
            variant="secondary"
            className="mt-4 flex gap-2 focus-visible:ring-2 focus-visible:ring-primary-9"
            onClick={onRetry}
            data-testid="skills-retry-button"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </Button>
        )}
      </div>
    );
  }

  if (skills.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center h-64 text-neutral-11"
        data-testid="skills-browse-empty"
      >
        <Package className="w-12 h-12 text-neutral-9 mb-4" />
        <p className="text-lg font-medium text-neutral-12">No skills found</p>
        <p className="text-sm">Try adjusting your search or filters.</p>
      </div>
    );
  }

  const hasMore = skills.length < total;

  return (
    <div className="space-y-6" data-testid="skills-browse-list">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {skills.map((skill) => (
          <SkillCard
            key={skill.name}
            skill={skill}
            isInstalled={installedSkills.includes(skill.name)}
            onInstall={() => onInstall(skill.name)}
            isInstalling={isInstalling}
            onViewDetails={onViewDetails}
          />
        ))}
      </div>

      {/* Pagination controls */}
      {total > 0 && (
        <div
          className="flex flex-col items-center gap-3 pt-4"
          data-testid="skills-pagination"
        >
          <p className="text-sm text-neutral-11">
            Showing {skills.length} of {total} skills
          </p>
          {hasMore && onLoadMore && (
            <Button
              variant="secondary"
              className="flex gap-2 focus-visible:ring-2 focus-visible:ring-primary-9"
              onClick={onLoadMore}
              disabled={isLoadingMore}
              data-testid="skills-load-more"
            >
              {isLoadingMore ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowUpCircle className="w-4 h-4 rotate-180" />
              )}
              Load More
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
