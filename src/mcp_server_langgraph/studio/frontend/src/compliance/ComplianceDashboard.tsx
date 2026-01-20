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

import { useReducedMotion } from "motion/react";
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
import { cn } from "../utils/cn";
import { Badge } from "@/components/UI";

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

function getStatusIcon(status: ComplianceStatus) {
  switch (status) {
    case "compliant":
      return (
        <CheckCircle
          size={16}
          className="text-success-9"
          role="img"
          aria-hidden="true"
        />
      );
    case "partial":
      return (
        <AlertCircle
          size={16}
          className="text-warning-9"
          role="img"
          aria-hidden="true"
        />
      );
    case "non-compliant":
      return (
        <AlertCircle
          size={16}
          className="text-error-9"
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
  if (percentage >= 90) return "text-success-10 dark:text-success-7";
  if (percentage >= 70) return "text-warning-9 dark:text-warning-9";
  return "text-error-10 dark:text-error-7";
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
        "rounded-lg border border-neutral-5",
        "bg-neutral-1 p-4",
        "hover:border-primary-5 dark:hover:border-primary-11",
        "transition-colors cursor-pointer",
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="font-semibold text-neutral-12">
            {name}
          </h3>
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
        <span className="text-neutral-10">
          {summary.compliantCount}/{summary.totalCount} controls
        </span>
        {summary.status === "partial" && (
          <span className="text-warning-9 dark:text-warning-9">
            {getStatusLabel(summary.status)}
          </span>
        )}
      </div>

      {summary.pendingActions !== undefined && summary.pendingActions > 0 && (
        <div className="mt-2 text-xs text-grafana-10 dark:text-grafana-5">
          {summary.pendingActions} actions pending
        </div>
      )}

      {summary.authLevel && (
        <div className="mt-2">
          <Badge
            size="sm"
            className="bg-primary-3 text-primary-11 dark:bg-primary-4 dark:text-primary-7"
          >
            {summary.authLevel}
          </Badge>
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Loading state
  if (isLoading) {
    return (
      <div data-testid="compliance-dashboard" className={cn("p-6", className)}>
        <div className="flex items-center gap-2 text-neutral-10">
          <Loader2 size={16} className={cn(!prefersReducedMotion && "animate-spin")} />
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
          "rounded-lg border border-neutral-5",
          "bg-neutral-1 p-8 text-center",
          className,
        )}
      >
        <LayoutDashboard
          size={32}
          className="mx-auto mb-3 text-neutral-9"
        />
        <p className="text-neutral-10">
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
          <LayoutDashboard size={20} className="text-primary-9" />
          <h2 className="text-xl font-semibold text-neutral-12">
            Compliance Overview
          </h2>
        </div>
      </div>

      {/* Framework Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <FrameworkCard
          name="SOC-2"
          icon={<Shield size={18} className="text-primary-9" />}
          summary={summary.soc2}
        />
        <FrameworkCard
          name="HIPAA"
          icon={<HeartPulse size={18} className="text-error-9" />}
          summary={summary.hipaa}
        />
        <FrameworkCard
          name="GDPR"
          icon={<Flag size={18} className="text-primary-10" />}
          summary={summary.gdpr}
        />
        <FrameworkCard
          name="FedRAMP"
          icon={<BadgeCheck size={18} className="text-insight-10" />}
          summary={summary.fedramp}
        />
      </div>
    </div>
  );
}
