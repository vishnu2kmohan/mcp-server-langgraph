/**
 * TemplateSelector Component
 *
 * Displays suggestion chips for reusable plan templates and allows
 * users to preview and apply templates to the orchestrator configuration.
 *
 * Features:
 * - Suggestion chips for quick template selection
 * - Template preview with configuration details
 * - Apply button to use template configuration
 * - Compact mode for inline display
 */

import { useState } from "react";
import {
  Sparkles,
  Check,
  X,
  Loader2,
  Brain,
  MessageSquare,
  CheckCircle,
} from "lucide-react";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type OrchestratorType = "standard" | "swarm" | "studio" | "ux" | "alert";
export type ThinkingBudget = "none" | "light" | "medium" | "deep";

export interface TemplateOption {
  templateId: string;
  name: string;
  description: string;
  orchestrator: OrchestratorType;
  thinkingBudget: ThinkingBudget;
  critiqueRounds: number;
  autoApprove: boolean;
  useCount: number;
  successRate: number;
}

export interface OrchestratorConfig {
  orchestrator: OrchestratorType;
  thinkingBudget: ThinkingBudget;
  critiqueRounds: number;
  autoApprove: boolean;
}

export interface TemplateSelectorProps {
  /** Suggested templates to display as chips */
  suggestions: TemplateOption[];
  /** Callback when a template is applied */
  onApply: (config: OrchestratorConfig) => void;
  /** Callback when suggestions are dismissed */
  onDismiss: () => void;
  /** Whether suggestions are loading */
  isLoading?: boolean;
  /** Compact display mode */
  compact?: boolean;
}

// =============================================================================
// Helper Components
// =============================================================================

function TemplateChip({
  template,
  isSelected,
  onClick,
  disabled,
}: {
  template: TemplateOption;
  isSelected: boolean;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <Button
      variant="primary"
      className="px-3 py-1.5 text-sm rounded-full border"
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={isSelected}>
      {template.name}
    </Button>
  );
}

function TemplatePreview({
  template,
  compact,
}: {
  template: TemplateOption;
  compact: boolean;
}) {
  return (
    <div className="mt-3 p-3 bg-neutral-1 rounded-lg border border-neutral-5">
      {!compact && (
        <p className="text-sm text-neutral-11 mb-3">
          {template.description}
        </p>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-neutral-10">
            Orchestrator:
          </span>
          <span className="font-medium text-neutral-12">
            {template.orchestrator}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <Brain className="w-3 h-3 text-neutral-9" />
          <span className="text-neutral-10">
            Thinking:
          </span>
          <span className="font-medium text-neutral-12">
            {template.thinkingBudget}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <MessageSquare className="w-3 h-3 text-neutral-9" />
          <span className="text-neutral-10">
            Critique:
          </span>
          <span className="font-medium text-neutral-12">
            {template.critiqueRounds} rounds
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <CheckCircle className="w-3 h-3 text-neutral-9" />
          <span className="text-neutral-10">
            Success:
          </span>
          <span className="font-medium text-success-10 dark:text-success-7">
            {Math.round(template.successRate * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function TemplateSelector({
  suggestions,
  onApply,
  onDismiss,
  isLoading = false,
  compact = false,
}: TemplateSelectorProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedTemplate = suggestions.find((t) => t.templateId === selectedId);

  const handleChipClick = (templateId: string) => {
    setSelectedId(selectedId === templateId ? null : templateId);
  };

  const handleApply = () => {
    if (!selectedTemplate) return;

    onApply({
      orchestrator: selectedTemplate.orchestrator,
      thinkingBudget: selectedTemplate.thinkingBudget,
      critiqueRounds: selectedTemplate.critiqueRounds,
      autoApprove: selectedTemplate.autoApprove,
    });
  };

  // Empty state
  if (!isLoading && suggestions.length === 0) {
    return (
      <div
        data-testid="template-selector"
        className={`bg-neutral-1 rounded-lg border border-neutral-5 p-4 ${compact ? "compact" : ""}`}
      >
        <p className="text-sm text-neutral-10 text-center">
          No template suggestions available
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="template-selector"
      className={`bg-neutral-1 rounded-lg border border-neutral-5 p-4 ${compact ? "compact" : ""}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-warning-9" />
          <h4 className="text-sm font-medium text-neutral-12">
            Suggested Templates
          </h4>
          <span className="text-xs text-neutral-10">
            {suggestions.length} suggestions
          </span>
        </div>

        <Button size="icon" variant="ghost"
          className="p-1 text-neutral-9 hover:text-neutral-11 rounded"
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>
      {/* Loading State */}
      {isLoading ? (
        <div role="status" className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-primary-9" />
          <span className="sr-only">Loading suggestions...</span>
        </div>
      ) : (
        <>
          {/* Template Chips */}
          <div className="flex flex-wrap gap-2">
            {suggestions.map((template) => (
              <TemplateChip
                key={template.templateId}
                template={template}
                isSelected={selectedId === template.templateId}
                onClick={() => handleChipClick(template.templateId)}
                disabled={isLoading}
              />
            ))}
          </div>

          {/* Selected Template Preview */}
          {selectedTemplate && (
            <TemplatePreview template={selectedTemplate} compact={compact} />
          )}

          {/* Apply Button */}
          {selectedTemplate && (
            <div className="mt-3 flex justify-end">
              <Button
                variant="primary"
                className="flex px-4 py-2 bg-primary-9 text-neutral-12 text-sm rounded-lg hover:bg-primary-10"
                type="button"
                onClick={handleApply}
              >
                <Check className="w-4 h-4" />
                Apply Template
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
