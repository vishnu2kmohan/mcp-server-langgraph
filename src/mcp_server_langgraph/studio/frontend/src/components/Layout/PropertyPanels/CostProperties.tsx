/**
 * CostProperties Component
 *
 * Property panel for cost tracking, showing summary
 * statistics and quick cost insights.
 */

import { useGetCostSummaryQuery } from "../../../api";
import type { TabState } from "../../../store/slices/workspaceSlice";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";

// =============================================================================
// Types
// =============================================================================

export interface CostPropertiesProps {
  tab: TabState;
  isSectionExpanded: (id: string) => boolean;
  onToggleSection: (id: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function CostProperties({
  tab: _tab,
  isSectionExpanded,
  onToggleSection,
}: CostPropertiesProps) {
  const { data: summary, isLoading } = useGetCostSummaryQuery({
    period: "30d",
  });

  if (isLoading) {
    return (
      <div className="p-4 text-xs text-gray-500 dark:text-gray-400">
        Loading cost data...
      </div>
    );
  }

  const formatCurrency = (value?: number) => {
    if (value === undefined) return "$0.00";
    return `$${value.toFixed(2)}`;
  };

  const formatNumber = (value?: number | null) => {
    if (value === undefined || value === null) return "0";
    return value.toLocaleString();
  };

  // Estimate requests from tokens (rough estimate: ~1000 tokens per request)
  const estimatedRequests = Math.ceil((summary?.total_tokens ?? 0) / 1000);

  return (
    <div data-testid="cost-properties">
      <PropertySection
        id="cost-summary"
        title="Summary"
        isExpanded={isSectionExpanded("cost-summary")}
        onToggle={() => onToggleSection("cost-summary")}
        badge={
          <span className="text-[10px] font-medium text-green-600 dark:text-green-400">
            {formatCurrency(summary?.total_cost)}
          </span>
        }
      >
        <PropertyRow
          label="Total Cost"
          value={formatCurrency(summary?.total_cost)}
        />
        <PropertyRow
          label="Total Tokens"
          value={formatNumber(summary?.total_tokens)}
        />
        <PropertyRow
          label="Prompt Tokens"
          value={formatNumber(summary?.prompt_tokens)}
        />
        <PropertyRow
          label="Completion Tokens"
          value={formatNumber(summary?.completion_tokens)}
        />
      </PropertySection>

      <PropertySection
        id="cost-period"
        title="Period"
        isExpanded={isSectionExpanded("cost-period")}
        onToggle={() => onToggleSection("cost-period")}
      >
        <PropertyRow label="View" value="Last 30 days" />
        <PropertyRow
          label="Avg/Day"
          value={formatCurrency((summary?.total_cost ?? 0) / 30)}
        />
      </PropertySection>

      <PropertySection
        id="cost-breakdown"
        title="Quick Stats"
        isExpanded={isSectionExpanded("cost-breakdown")}
        onToggle={() => onToggleSection("cost-breakdown")}
      >
        <PropertyRow
          label="Cost per 1K Tokens"
          value={formatCurrency(
            (summary?.total_cost ?? 0) / ((summary?.total_tokens ?? 1) / 1000),
          )}
        />
        <PropertyRow
          label="Est. Requests"
          value={formatNumber(estimatedRequests)}
        />
      </PropertySection>
    </div>
  );
}

export default CostProperties;
