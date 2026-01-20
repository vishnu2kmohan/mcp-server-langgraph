/**
 * OrganizationCostDashboard
 *
 * Admin-only component for viewing organizational cost breakdown.
 * Shows cost aggregation by organization, project, and team.
 * Uses RTK Query for data fetching with automatic caching.
 */

import { useState } from "react";
import { Building2, Folder, Users, TrendingUp } from "lucide-react";
import { Skeleton, SkeletonCard } from "../UI";
// Direct import to avoid circular dependency through barrel export
import { ErrorState } from "../UI/ErrorState";
import {
  useGetCostByOrganizationQuery,
  useGetCostByProjectQuery,
  useGetCostByTeamQuery,
} from "../../api";
import type { OrganizationalCostParams } from "../../types";

import { Button } from "@/components/UI";

export interface OrganizationCostDashboardProps {
  /** Optional organization filter */
  organizationId?: string;
  /** Optional project filter */
  projectId?: string;
  /** Start date filter (YYYY-MM-DD) */
  startDate?: string;
  /** End date filter (YYYY-MM-DD) */
  endDate?: string;
}

type ViewMode = "organization" | "project" | "team";

export function OrganizationCostDashboard({
  organizationId,
  projectId,
  startDate,
  endDate,
}: OrganizationCostDashboardProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("organization");
  const [selectedOrg, setSelectedOrg] = useState<string | undefined>(
    organizationId,
  );
  const [selectedProject, setSelectedProject] = useState<string | undefined>(
    projectId,
  );

  // Build params for queries (camelCase per ADR-0091 Phase 6)
  const orgParams: OrganizationalCostParams = {
    startDate: startDate,
    endDate: endDate,
  };

  const projectParams: OrganizationalCostParams = {
    organizationId: selectedOrg,
    startDate: startDate,
    endDate: endDate,
  };

  const teamParams: OrganizationalCostParams = {
    organizationId: selectedOrg,
    projectId: selectedProject,
    startDate: startDate,
    endDate: endDate,
  };

  // RTK Query hooks
  const {
    data: orgCosts,
    isLoading: orgLoading,
    isError: orgError,
    error: orgErrorData,
    refetch: refetchOrg,
  } = useGetCostByOrganizationQuery(orgParams);

  const {
    data: projectCosts,
    isLoading: projectLoading,
    isError: projectError,
    error: projectErrorData,
    refetch: refetchProject,
  } = useGetCostByProjectQuery(projectParams);

  const {
    data: teamCosts,
    isLoading: teamLoading,
    isError: teamError,
    error: teamErrorData,
    refetch: refetchTeam,
  } = useGetCostByTeamQuery(teamParams);

  const formatCurrency = (amount: number): string => {
    return `$${amount.toFixed(2)}`;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const handleRetry = () => {
    refetchOrg();
    refetchProject();
    refetchTeam();
  };

  const handleOrgClick = (orgId: string) => {
    setSelectedOrg(orgId === selectedOrg ? undefined : orgId);
    setSelectedProject(undefined);
    setViewMode("project");
  };

  const handleProjectClick = (projId: string) => {
    setSelectedProject(projId === selectedProject ? undefined : projId);
    setViewMode("team");
  };

  const isLoading = orgLoading || projectLoading || teamLoading;
  const hasError = orgError || projectError || teamError;
  const errorData = orgErrorData || projectErrorData || teamErrorData;

  // Calculate totals
  const totalOrgCost =
    orgCosts?.reduce((sum, org) => sum + org.totalCost, 0) ?? 0;
  const totalOrgTokens =
    orgCosts?.reduce((sum, org) => sum + org.totalTokens, 0) ?? 0;
  const totalOrgRequests =
    orgCosts?.reduce((sum, org) => sum + org.requestCount, 0) ?? 0;

  return (
    <div className="space-y-6">
      {/* View Mode Tabs */}
      <div className="flex items-center gap-2 border-b border-neutral-5">
        <Button
          className="flex px-4 py-2 border-b-2"
          onClick={() => setViewMode("organization")}
        >
          <Building2 size={16} />
          Organizations
        </Button>
        <Button
          className="flex px-4 py-2 border-b-2"
          onClick={() => setViewMode("project")}
        >
          <Folder size={16} />
          Projects
          {selectedOrg && (
            <span className="ml-1 text-xs bg-primary-3 dark:bg-primary-12 px-1.5 py-0.5 rounded">
              {selectedOrg.replace("organization:", "")}
            </span>
          )}
        </Button>
        <Button
          className="flex px-4 py-2 border-b-2"
          onClick={() => setViewMode("team")}
        >
          <Users size={16} />
          Teams
          {selectedProject && (
            <span className="ml-1 text-xs bg-primary-3 dark:bg-primary-12 px-1.5 py-0.5 rounded">
              {selectedProject.replace("project:", "")}
            </span>
          )}
        </Button>
      </div>
      {/* Summary Cards */}
      {viewMode === "organization" && (
        <div className="grid gap-4 md:grid-cols-4">
          <div className="p-6 bg-neutral-1 rounded-lg border border-neutral-5">
            <div className="flex items-center gap-2 mb-2">
              <Building2 size={20} className="text-primary-9" />
              <h3 className="text-sm font-medium text-neutral-10">
                Total Organizations
              </h3>
            </div>
            <span className="text-3xl font-bold text-neutral-12">
              {orgCosts?.length ?? 0}
            </span>
          </div>
          <div className="p-6 bg-neutral-1 rounded-lg border border-neutral-5">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={20} className="text-success-9" />
              <h3 className="text-sm font-medium text-neutral-10">
                Total Cost
              </h3>
            </div>
            <span className="text-3xl font-bold text-neutral-12">
              {formatCurrency(totalOrgCost)}
            </span>
          </div>
          <div className="p-6 bg-neutral-1 rounded-lg border border-neutral-5">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={20} className="text-insight-9" />
              <h3 className="text-sm font-medium text-neutral-10">
                Total Tokens
              </h3>
            </div>
            <span className="text-3xl font-bold text-neutral-12">
              {formatNumber(totalOrgTokens)}
            </span>
          </div>
          <div className="p-6 bg-neutral-1 rounded-lg border border-neutral-5">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={20} className="text-warning-9" />
              <h3 className="text-sm font-medium text-neutral-10">
                Total Requests
              </h3>
            </div>
            <span className="text-3xl font-bold text-neutral-12">
              {formatNumber(totalOrgRequests)}
            </span>
          </div>
        </div>
      )}
      {/* Content */}
      {isLoading ? (
        <div className="space-y-4">
          <SkeletonCard />
          <div className="space-y-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-3/4" />
          </div>
        </div>
      ) : hasError ? (
        <ErrorState
          title="Failed to load organizational cost data"
          message={
            (errorData as { message?: string })?.message ||
            "Unable to fetch organizational cost information. Please try again."
          }
          onRetry={handleRetry}
        />
      ) : (
        <div className="bg-neutral-1 rounded-lg border border-neutral-5">
          {/* Organization View */}
          {viewMode === "organization" && (
            <>
              <div className="px-6 py-4 border-b border-neutral-5">
                <h2 className="text-lg font-semibold text-neutral-12">
                  Cost by Organization
                </h2>
                <p className="text-sm text-neutral-10">
                  Click an organization to see project breakdown
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-neutral-1">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Organization
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Tokens
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Requests
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        % of Total
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-5 dark:divide-neutral-6">
                    {orgCosts?.map((org) => (
                      <tr
                        key={org.organizationId}
                        onClick={() => handleOrgClick(org.organizationId)}
                        className="cursor-pointer hover:bg-neutral-a6"
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-neutral-12">
                          <div className="flex items-center gap-2">
                            <Building2
                              size={16}
                              className="text-neutral-9"
                            />
                            {org.organizationId.replace("organization:", "")}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-12">
                          {formatCurrency(org.totalCost)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                          {formatNumber(org.totalTokens)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                          {formatNumber(org.requestCount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                          {totalOrgCost > 0
                            ? `${((org.totalCost / totalOrgCost) * 100).toFixed(1)}%`
                            : "0%"}
                        </td>
                      </tr>
                    ))}
                    {(!orgCosts || orgCosts.length === 0) && (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-6 py-8 text-center text-neutral-10"
                        >
                          No organizational cost data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Project View */}
          {viewMode === "project" && (
            <>
              <div className="px-6 py-4 border-b border-neutral-5">
                <h2 className="text-lg font-semibold text-neutral-12">
                  Cost by Project
                  {selectedOrg && (
                    <span className="ml-2 text-sm font-normal text-neutral-10">
                      in {selectedOrg.replace("organization:", "")}
                    </span>
                  )}
                </h2>
                <p className="text-sm text-neutral-10">
                  Click a project to see team breakdown
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-neutral-1">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Project
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Organization
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Tokens
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Requests
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-5 dark:divide-neutral-6">
                    {projectCosts?.map((proj) => (
                      <tr
                        key={proj.projectId}
                        onClick={() => handleProjectClick(proj.projectId)}
                        className="cursor-pointer hover:bg-neutral-a6"
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-neutral-12">
                          <div className="flex items-center gap-2">
                            <Folder
                              size={16}
                              className="text-neutral-9"
                            />
                            {proj.projectId.replace("project:", "")}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-10">
                          {proj.organizationId?.replace("organization:", "") ??
                            "—"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-12">
                          {formatCurrency(proj.totalCost)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                          {formatNumber(proj.totalTokens)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                          {formatNumber(proj.requestCount)}
                        </td>
                      </tr>
                    ))}
                    {(!projectCosts || projectCosts.length === 0) && (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-6 py-8 text-center text-neutral-10"
                        >
                          No project cost data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Team View */}
          {viewMode === "team" && (
            <>
              <div className="px-6 py-4 border-b border-neutral-5">
                <h2 className="text-lg font-semibold text-neutral-12">
                  Cost by Team
                  {selectedProject && (
                    <span className="ml-2 text-sm font-normal text-neutral-10">
                      in {selectedProject.replace("project:", "")}
                    </span>
                  )}
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-neutral-1">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Team
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Organization
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Project
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Tokens
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Requests
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-5 dark:divide-neutral-6">
                    {teamCosts?.map((team) => (
                      <tr
                        key={team.teamId}
                        className="hover:bg-neutral-a6"
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-neutral-12">
                          <div className="flex items-center gap-2">
                            <Users
                              size={16}
                              className="text-neutral-9"
                            />
                            {team.teamId.replace("team:", "")}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-10">
                          {team.organizationId?.replace("organization:", "") ??
                            "—"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-10">
                          {team.projectId?.replace("project:", "") ?? "—"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-12">
                          {formatCurrency(team.totalCost)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                          {formatNumber(team.totalTokens)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                          {formatNumber(team.requestCount)}
                        </td>
                      </tr>
                    ))}
                    {(!teamCosts || teamCosts.length === 0) && (
                      <tr>
                        <td
                          colSpan={6}
                          className="px-6 py-8 text-center text-neutral-10"
                        >
                          No team cost data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default OrganizationCostDashboard;
