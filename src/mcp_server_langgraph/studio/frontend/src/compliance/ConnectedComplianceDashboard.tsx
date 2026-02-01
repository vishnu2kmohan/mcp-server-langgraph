/**
 * ConnectedComplianceDashboard
 *
 * Phase 5: Compliance Dashboards - Backend Integration
 * Container component that connects ComplianceDashboard to real backend APIs.
 *
 * Features:
 * - Fetches compliance summary from /api/v1/compliance/reports/summary
 * - Transforms backend response to component-friendly format
 * - Handles loading, error, and retry states
 * - Supports custom date range filtering
 */

import { useMemo, useCallback } from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { useGetComplianceSummaryQuery } from "../api";
import {
  ComplianceDashboard,
  type ComplianceSummary,
} from "./ComplianceDashboard";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface ConnectedComplianceDashboardProps {
  /** Start time for compliance report (ISO string). Defaults to 30 days ago. */
  startTime?: string;
  /** End time for compliance report (ISO string). Defaults to now. */
  endTime?: string;
  /** Additional class name */
  className?: string;
}

/** Backend API response shape */
interface BackendFrameworkSummary {
  percentage: number;
  compliant_count: number;
  total_count: number;
  status: "compliant" | "partial" | "non-compliant";
  pending_actions?: number;
  auth_level?: string;
}

interface BackendComplianceSummary {
  soc2: BackendFrameworkSummary;
  hipaa: BackendFrameworkSummary;
  gdpr: BackendFrameworkSummary;
  fedramp: BackendFrameworkSummary;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get default date range (last 30 days)
 */
function getDefaultDateRange(): { start_time: string; end_time: string } {
  const now = new Date();
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  return {
    start_time: thirtyDaysAgo.toISOString(),
    end_time: now.toISOString(),
  };
}

/**
 * Transform backend response to frontend format
 * Converts snake_case to camelCase and restructures data
 */
function transformSummary(
  backendData: BackendComplianceSummary,
): ComplianceSummary {
  const transformFramework = (
    framework: BackendFrameworkSummary,
  ): ComplianceSummary["soc2"] => ({
    percentage: framework.percentage,
    compliantCount: framework.compliant_count,
    totalCount: framework.total_count,
    status: framework.status,
    pendingActions: framework.pending_actions,
    authLevel: framework.auth_level,
  });

  return {
    soc2: transformFramework(backendData.soc2),
    hipaa: transformFramework(backendData.hipaa),
    gdpr: transformFramework(backendData.gdpr),
    fedramp: transformFramework(backendData.fedramp),
  };
}

// =============================================================================
// Component
// =============================================================================

export function ConnectedComplianceDashboard({
  startTime,
  endTime,
  className,
}: ConnectedComplianceDashboardProps) {
  // Calculate date range
  const dateRange = useMemo(() => {
    if (startTime && endTime) {
      return { start_time: startTime, end_time: endTime };
    }
    return getDefaultDateRange();
  }, [startTime, endTime]);

  // Fetch compliance summary from API
  const { data, isLoading, error, refetch } =
    useGetComplianceSummaryQuery(dateRange);

  // Transform backend data to frontend format
  const summary = useMemo(() => {
    if (!data) return null;
    try {
      return transformSummary(data as unknown as BackendComplianceSummary);
    } catch {
      return null;
    }
  }, [data]);

  // Handle retry
  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  // Error state
  if (error) {
    return (
      <div
        data-testid="compliance-dashboard"
        className={cn(
          "rounded-lg border border-error-4 dark:border-error-11",
          "bg-error-1 dark:bg-error-a3 p-6 text-center",
          className,
        )}
      >
        <AlertTriangle
          size={32}
          className="mx-auto mb-3 text-error-9"
          aria-hidden="true"
        />
        <p className="text-error-11 dark:text-error-9 mb-4">
          Failed to load compliance data
        </p>
        <Button
          variant="ghost"
          data-testid="retry-button"
          type="button"
          onClick={handleRetry}
          className={cn(
            "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
            "bg-error-10 text-neutral-12 hover:bg-error-11",
            "transition-colors",
          )}
        >
          <RefreshCw size={16} />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <ComplianceDashboard
      summary={summary}
      isLoading={isLoading}
      className={className}
    />
  );
}
