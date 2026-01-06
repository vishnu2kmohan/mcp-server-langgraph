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
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={isSelected}
      className={`px-3 py-1.5 text-sm rounded-full border transition-all ${
        isSelected
          ? "ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/30 border-blue-500 text-blue-700 dark:text-blue-300"
          : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-600"
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {template.name}
    </button>
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
    <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {!compact && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          {template.description}
        </p>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500 dark:text-gray-400">
            Orchestrator:
          </span>
          <span className="font-medium text-gray-900 dark:text-white">
            {template.orchestrator}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <Brain className="w-3 h-3 text-gray-400" />
          <span className="text-gray-500 dark:text-gray-400">Thinking:</span>
          <span className="font-medium text-gray-900 dark:text-white">
            {template.thinkingBudget}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <MessageSquare className="w-3 h-3 text-gray-400" />
          <span className="text-gray-500 dark:text-gray-400">Critique:</span>
          <span className="font-medium text-gray-900 dark:text-white">
            {template.critiqueRounds} rounds
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <CheckCircle className="w-3 h-3 text-gray-400" />
          <span className="text-gray-500 dark:text-gray-400">Success:</span>
          <span className="font-medium text-green-600 dark:text-green-400">
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
        className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4 ${compact ? "compact" : ""}`}
      >
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
          No template suggestions available
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="template-selector"
      className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4 ${compact ? "compact" : ""}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-yellow-500" />
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
            Suggested Templates
          </h4>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {suggestions.length} suggestions
          </span>
        </div>

        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div role="status" className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
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
              <button
                type="button"
                onClick={handleApply}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-600 transition-colors"
              >
                <Check className="w-4 h-4" />
                Apply Template
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
