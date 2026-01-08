/**
 * AgentApprovalAuditLog Component
 *
 * Displays the history of agent HITL approval/rejection decisions.
 *
 * Features:
 * - Display approval/rejection history
 * - Filter by decision type
 * - Export functionality
 * - Expandable rows for details
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import React, { useState, useMemo } from "react";

// =============================================================================
// Types
// =============================================================================

export interface AuditEntry {
  id: string;
  requestId: string;
  agentName: string;
  decision: "approved" | "rejected";
  confidence: number;
  threshold: number;
  decidedBy: string;
  decidedAt: string;
  reason: string | null;
}

export interface AgentApprovalAuditLogProps {
  /** Audit entries to display */
  entries: AuditEntry[];
  /** Whether data is loading */
  isLoading?: boolean;
  /** Export callback */
  onExport?: (entries: AuditEntry[]) => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function AgentApprovalAuditLog({
  entries,
  isLoading = false,
  onExport,
  className = "",
}: AgentApprovalAuditLogProps): React.ReactElement {
  const [filter, setFilter] = useState<"all" | "approved" | "rejected">("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filter entries based on selected filter
  const filteredEntries = useMemo(() => {
    if (filter === "all") return entries;
    return entries.filter((entry) => entry.decision === filter);
  }, [entries, filter]);

  // Format date for display
  const formatDate = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  // Handle export click
  const handleExport = () => {
    if (onExport) {
      onExport(filteredEntries);
    }
  };

  // Handle row click to expand/collapse
  const handleRowClick = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  // Render loading state
  if (isLoading) {
    return (
      <div className={`p-4 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
        <p className="text-gray-500 dark:text-gray-400 mt-2">Loading...</p>
      </div>
    );
  }

  return (
    <div className={`p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Approval Audit Log</h2>

        <div className="flex items-center gap-4">
          {/* Filter */}
          <select
            value={filter}
            onChange={(e) =>
              setFilter(e.target.value as "all" | "approved" | "rejected")
            }
            className="px-3 py-1.5 border rounded-md text-sm bg-white"
            aria-label="Filter decisions"
          >
            <option value="all">All Decisions</option>
            <option value="approved">Approved Only</option>
            <option value="rejected">Rejected Only</option>
          </select>

          {/* Export button */}
          <button
            onClick={handleExport}
            className="px-3 py-1.5 bg-primary-600 text-white rounded-md text-sm hover:bg-primary-700 transition-colors"
            aria-label="Export"
          >
            Export
          </button>
        </div>
      </div>

      {/* Empty state */}
      {filteredEntries.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>No approval history available.</p>
        </div>
      )}

      {/* Table */}
      {filteredEntries.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse" role="table">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  Agent
                </th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  Decision
                </th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  Confidence
                </th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  Decided By
                </th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  Date
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredEntries.map((entry) => (
                <React.Fragment key={entry.id}>
                  {/* Main row */}
                  <tr
                    className="border-b hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleRowClick(entry.id)}
                    role="row"
                  >
                    <td className="px-4 py-3 text-sm">{entry.agentName}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          entry.decision === "approved"
                            ? "bg-success-100 text-success-800"
                            : "bg-error-100 text-error-800"
                        }`}
                      >
                        {entry.decision}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`${
                          entry.confidence >= entry.threshold
                            ? "text-success-600"
                            : "text-warning-600"
                        }`}
                      >
                        {Math.round(entry.confidence * 100)}%
                      </span>
                      <span className="text-gray-400 dark:text-gray-400 text-xs ml-1">
                        / {Math.round(entry.threshold * 100)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                      {entry.decidedBy}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                      {formatDate(entry.decidedAt)}
                    </td>
                  </tr>

                  {/* Expanded details row */}
                  {expandedId === entry.id && (
                    <tr className="bg-gray-50">
                      <td colSpan={5} className="px-4 py-3">
                        <div className="text-sm">
                          <div className="mb-2">
                            <span className="font-medium text-gray-700 dark:text-gray-200">
                              Request ID:
                            </span>{" "}
                            <span className="font-mono text-gray-600 dark:text-gray-300">
                              {entry.requestId}
                            </span>
                          </div>
                          {entry.reason && (
                            <div>
                              <span className="font-medium text-gray-700 dark:text-gray-200">
                                Reason:
                              </span>{" "}
                              <span className="text-gray-600 dark:text-gray-300">
                                {entry.reason}
                              </span>
                            </div>
                          )}
                          {!entry.reason && (
                            <div className="text-gray-400 dark:text-gray-400 italic">
                              No reason provided
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      {entries.length > 0 && (
        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          Showing {filteredEntries.length} of {entries.length} entries
          {filter !== "all" && ` (filtered by: ${filter})`}
        </div>
      )}
    </div>
  );
}
