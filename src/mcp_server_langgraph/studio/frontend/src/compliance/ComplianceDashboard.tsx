/**
 * ComplianceDashboard Component
 *
 * Phase 5: Compliance Dashboards
 * Unified view of all compliance frameworks.
 *
 * Features:
 * - Overview cards for SOC-2, HIPAA, GDPR, FedRAMP
 * - Compliance percentages and status indicators
 * - Quick access to individual framework details
 */

import {
  LayoutDashboard,
  Shield,
  HeartPulse,
  Flag,
  BadgeCheck,
  CheckCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type ComplianceStatus = "compliant" | "partial" | "non-compliant";

export interface FrameworkSummary {
  percentage: number;
  compliantCount: number;
  totalCount: number;
  status: ComplianceStatus;
  pendingActions?: number;
  authLevel?: string;
}

export interface ComplianceSummary {
  soc2: FrameworkSummary;
  hipaa: FrameworkSummary;
  gdpr: FrameworkSummary;
  fedramp: FrameworkSummary;
}

export interface ComplianceDashboardProps {
  summary: ComplianceSummary | null;
  isLoading?: boolean;
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

function getStatusIcon(status: ComplianceStatus) {
  switch (status) {
    case "compliant":
      return (
        <CheckCircle
          size={16}
          className="text-green-500"
          role="img"
          aria-hidden="true"
        />
      );
    case "partial":
      return (
        <AlertCircle
          size={16}
          className="text-yellow-500"
          role="img"
          aria-hidden="true"
        />
      );
    case "non-compliant":
      return (
        <AlertCircle
          size={16}
          className="text-red-500"
          role="img"
          aria-hidden="true"
        />
      );
  }
}

function getStatusLabel(status: ComplianceStatus): string {
  switch (status) {
    case "compliant":
      return "Compliant";
    case "partial":
      return "Partial";
    case "non-compliant":
      return "Non-Compliant";
  }
}

function getPercentageColor(percentage: number): string {
  if (percentage >= 90) return "text-green-600 dark:text-green-400";
  if (percentage >= 70) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

// =============================================================================
// Framework Card
// =============================================================================

interface FrameworkCardProps {
  name: string;
  icon: React.ReactNode;
  summary: FrameworkSummary;
}

function FrameworkCard({ name, icon, summary }: FrameworkCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900 p-4",
        "hover:border-primary-300 dark:hover:border-primary-700",
        "transition-colors cursor-pointer",
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon}
          <h4 className="font-semibold text-gray-900 dark:text-gray-100">
            {name}
          </h4>
        </div>
        {getStatusIcon(summary.status)}
      </div>

      <div className="flex items-baseline gap-1 mb-2">
        <span
          className={cn(
            "text-3xl font-bold",
            getPercentageColor(summary.percentage),
          )}
        >
          {summary.percentage}%
        </span>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          {summary.compliantCount}/{summary.totalCount} controls
        </span>
        {summary.status === "partial" && (
          <span className="text-yellow-600 dark:text-yellow-400">
            {getStatusLabel(summary.status)}
          </span>
        )}
      </div>

      {summary.pendingActions !== undefined && summary.pendingActions > 0 && (
        <div className="mt-2 text-xs text-orange-600 dark:text-orange-400">
          {summary.pendingActions} actions pending
        </div>
      )}

      {summary.authLevel && (
        <div className="mt-2">
          <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
            {summary.authLevel}
          </span>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

export function ComplianceDashboard({
  summary,
  isLoading = false,
  className,
}: ComplianceDashboardProps) {
  // Loading state
  if (isLoading) {
    return (
      <div data-testid="compliance-dashboard" className={cn("p-6", className)}>
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 size={16} className="animate-spin" />
          <span>Loading compliance data...</span>
        </div>
      </div>
    );
  }

  // Empty state
  if (!summary) {
    return (
      <div
        data-testid="compliance-dashboard"
        className={cn(
          "rounded-lg border border-gray-200 dark:border-gray-700",
          "bg-white dark:bg-gray-900 p-8 text-center",
          className,
        )}
      >
        <LayoutDashboard size={32} className="mx-auto mb-3 text-gray-400" />
        <p className="text-gray-500 dark:text-gray-400">
          No compliance data available
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="compliance-dashboard"
      className={cn("space-y-6", className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <LayoutDashboard size={20} className="text-primary-500" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Compliance Overview
          </h2>
        </div>
      </div>

      {/* Framework Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <FrameworkCard
          name="SOC-2"
          icon={<Shield size={18} className="text-blue-500" />}
          summary={summary.soc2}
        />
        <FrameworkCard
          name="HIPAA"
          icon={<HeartPulse size={18} className="text-red-500" />}
          summary={summary.hipaa}
        />
        <FrameworkCard
          name="GDPR"
          icon={<Flag size={18} className="text-blue-600" />}
          summary={summary.gdpr}
        />
        <FrameworkCard
          name="FedRAMP"
          icon={<BadgeCheck size={18} className="text-purple-600" />}
          summary={summary.fedramp}
        />
      </div>
    </div>
  );
}
