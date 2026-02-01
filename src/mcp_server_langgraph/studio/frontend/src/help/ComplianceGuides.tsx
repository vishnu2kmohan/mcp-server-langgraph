/**
 * ComplianceGuides - Phase 6
 *
 * Compliance runbooks and guides in the help module.
 * Provides step-by-step procedures for SOC-2, HIPAA, GDPR, and FedRAMP.
 */
import { useState, useCallback, useMemo } from "react";
import {
  Search,
  ChevronDown,
  ChevronRight,
  Printer,
  Check,
  FileText,
} from "lucide-react";
import { cn } from "../utils/cn";

import { Button, Input, Select, Checkbox } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type ComplianceFramework = "soc2" | "hipaa" | "gdpr" | "fedramp";

export interface GuideStep {
  title: string;
  description: string;
}

export interface Guide {
  id: string;
  title: string;
  framework: ComplianceFramework;
  summary: string;
  steps: GuideStep[];
  lastUpdated: string;
}

export interface ComplianceGuidesProps {
  guides: Guide[];
  enableProgress?: boolean;
  onProgressChange?: (
    guideId: string,
    stepIndex: number,
    completed: boolean,
  ) => void;
  onPrint?: (guide: Guide) => void;
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const FRAMEWORK_LABELS: Record<ComplianceFramework, string> = {
  soc2: "SOC-2",
  hipaa: "HIPAA",
  gdpr: "GDPR",
  fedramp: "FedRAMP",
};

const FRAMEWORK_COLORS: Record<ComplianceFramework, string> = {
  soc2: "bg-primary-3 bg-primary-4 text-primary-11 dark:text-primary-5",
  hipaa: "bg-success-3 bg-success-4 text-success-11 dark:text-success-5",
  gdpr: "bg-insight-2 dark:bg-insight-a4 text-insight-11 dark:text-insight-5",
  fedramp:
    "bg-grafana-2 dark:bg-grafana-12/30 text-grafana-11 dark:text-grafana-4",
};

// =============================================================================
// Component
// =============================================================================

export function ComplianceGuides({
  guides,
  enableProgress = false,
  onProgressChange,
  onPrint,
  className,
}: ComplianceGuidesProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [frameworkFilter, setFrameworkFilter] = useState<
    ComplianceFramework | "all"
  >("all");
  const [expandedGuide, setExpandedGuide] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<
    Record<string, Set<number>>
  >({});

  const filteredGuides = useMemo(() => {
    return guides.filter((guide) => {
      const matchesFramework =
        frameworkFilter === "all" || guide.framework === frameworkFilter;
      const matchesSearch =
        !searchQuery ||
        guide.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        guide.summary.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFramework && matchesSearch;
    });
  }, [guides, frameworkFilter, searchQuery]);

  const handleGuideClick = useCallback((guideId: string) => {
    setExpandedGuide((prev) => (prev === guideId ? null : guideId));
  }, []);

  const handleStepToggle = useCallback(
    (guideId: string, stepIndex: number) => {
      setCompletedSteps((prev) => {
        const guideSteps = new Set(prev[guideId] || []);
        const isNowCompleted = !guideSteps.has(stepIndex);
        if (isNowCompleted) {
          guideSteps.add(stepIndex);
        } else {
          guideSteps.delete(stepIndex);
        }
        onProgressChange?.(guideId, stepIndex, isNowCompleted);
        return { ...prev, [guideId]: guideSteps };
      });
    },
    [onProgressChange],
  );

  const handlePrint = useCallback(
    (guide: Guide, e: React.MouseEvent) => {
      e.stopPropagation();
      onPrint?.(guide);
    },
    [onPrint],
  );

  const getCompletedCount = useCallback(
    (guideId: string) => {
      return completedSteps[guideId]?.size || 0;
    },
    [completedSteps],
  );

  return (
    <div
      data-testid="compliance-guides"
      className={cn("bg-neutral-1 rounded-lg", className)}
    >
      {/* Header */}
      <div className="p-4 border-b border-neutral-5">
        <h3 className="text-sm font-medium text-neutral-12 mb-3">
          Compliance Guides
        </h3>

        {/* Search and Filter */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-9"
            />
            <Input
              className="pl-9 pr-3 py-2 text-sm bg-neutral-1 text-neutral-12 placeholder-neutral-9 focus:ring-primary-7"
              type="search"
              role="searchbox"
              data-testid="guide-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search guides..."
            />
          </div>
          <Select
            className="px-3 py-2 text-sm bg-neutral-1 text-neutral-12 focus:ring-primary-7"
            data-testid="framework-filter"
            value={frameworkFilter}
            onChange={(e) =>
              setFrameworkFilter(e.target.value as ComplianceFramework | "all")
            }
          >
            <option value="all">All Frameworks</option>
            <option value="soc2">SOC-2</option>
            <option value="hipaa">HIPAA</option>
            <option value="gdpr">GDPR</option>
            <option value="fedramp">FedRAMP</option>
          </Select>
        </div>
      </div>
      {/* Guide List */}
      <div className="divide-y divide-neutral-5 dark:divide-neutral-6">
        {guides.length === 0 && (
          <div className="p-8 text-center text-neutral-10">
            <FileText size={32} className="mx-auto mb-2 opacity-50" />
            <p>No compliance guides available</p>
          </div>
        )}

        {guides.length > 0 && filteredGuides.length === 0 && (
          <div className="p-8 text-center text-neutral-10">
            <Search size={32} className="mx-auto mb-2 opacity-50" />
            <p>No guides found matching your search</p>
          </div>
        )}

        {filteredGuides.map((guide) => {
          const isExpanded = expandedGuide === guide.id;
          const completedCount = getCompletedCount(guide.id);

          return (
            <div key={guide.id}>
              {/* Guide Header */}
              <Button
                variant="secondary"
                className="w-full flex items-start p-4 text-left hover:bg-neutral-a6"
                type="button"
                data-testid={`guide-${guide.id}`}
                aria-expanded={isExpanded}
                onClick={() => handleGuideClick(guide.id)}
              >
                {isExpanded ? (
                  <ChevronDown
                    size={18}
                    className="text-neutral-9 mt-0.5 flex-shrink-0"
                  />
                ) : (
                  <ChevronRight
                    size={18}
                    className="text-neutral-9 mt-0.5 flex-shrink-0"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-neutral-12">
                      {guide.title}
                    </span>
                    <span
                      data-testid={`framework-badge-${guide.framework}`}
                      className={cn(
                        "px-1.5 py-0.5 text-xs font-medium rounded",
                        FRAMEWORK_COLORS[guide.framework],
                      )}
                    >
                      {FRAMEWORK_LABELS[guide.framework]}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-10">{guide.summary}</p>
                  {enableProgress && completedCount > 0 && (
                    <p className="text-xs text-primary-10 dark:text-primary-7 mt-1">
                      {completedCount} of {guide.steps.length} steps complete
                    </p>
                  )}
                </div>
              </Button>
              {/* Expanded Content */}
              {isExpanded && (
                <div className="px-4 pb-4 pl-12">
                  {/* Actions */}
                  <div className="flex justify-end mb-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="flex px-2 py-1 text-xs text-neutral-11 hover:bg-neutral-2 rounded"
                      type="button"
                      data-testid="print-guide"
                      onClick={(e) => handlePrint(guide, e)}
                    >
                      <Printer size={14} />
                      Print
                    </Button>
                  </div>

                  {/* Steps */}
                  <div data-testid="guide-steps" className="space-y-2">
                    {guide.steps.map((step, index) => {
                      // Ensure isCompleted is always a boolean to avoid controlled/uncontrolled warning
                      const isCompleted =
                        completedSteps[guide.id]?.has(index) ?? false;

                      return (
                        <div
                          key={index}
                          className={cn(
                            "flex items-start gap-3 p-3 rounded-lg border",
                            isCompleted
                              ? "bg-success-1 dark:bg-success-a2 border-success-4 dark:border-success-11"
                              : "bg-neutral-1 border-neutral-5",
                          )}
                        >
                          {enableProgress ? (
                            <Checkbox
                              checked={isCompleted}
                              onChange={() => handleStepToggle(guide.id, index)}
                              size="sm"
                              className="mt-0.5"
                            />
                          ) : (
                            <div className="mt-0.5 w-5 h-5 rounded-full bg-neutral-3 flex items-center justify-center text-xs text-neutral-11">
                              {index + 1}
                            </div>
                          )}
                          <div className="flex-1">
                            <div className="text-sm font-medium text-neutral-12">
                              {step.title}
                            </div>
                            <div className="text-xs text-neutral-10">
                              {step.description}
                            </div>
                          </div>
                          {isCompleted && (
                            <Check
                              size={16}
                              className="text-success-9 flex-shrink-0"
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Progress Summary */}
                  {enableProgress && (
                    <div className="mt-3 text-xs text-neutral-10">
                      {completedCount} of {guide.steps.length} steps complete
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
