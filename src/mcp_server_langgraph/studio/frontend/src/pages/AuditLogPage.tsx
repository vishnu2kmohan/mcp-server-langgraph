/**
 * AuditLogPage
 *
 * Admin-only page for viewing system audit logs.
 * Features:
 * - Paginated log listing
 * - Filter by action type, user, date range
 * - Log detail expansion
 * - Export to CSV
 *
 * Uses RTK Query for data fetching with automatic caching.
 */

import { useState, useMemo, useCallback } from "react";
import {
  FileText,
  RefreshCw,
  Download,
  ChevronDown,
  ChevronRight,
  Shield,
} from "lucide-react";
import { useListAuditLogsQuery } from "../api";
import { CursorPagination } from "../components/UI";

export function AuditLogPage() {
  // Pagination state
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);

  // Fetch audit logs using RTK Query
  const {
    data: logsData,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useListAuditLogsQuery({ limit: 50, cursor });

  // Local filter state
  const [actionFilter, setActionFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  // Get total and next cursor from response
  const total = logsData?.total ?? 0;
  const nextCursor = logsData?.next_cursor ?? null;
  const hasNextPage = Boolean(nextCursor);
  const hasPreviousPage = cursorHistory.length > 0;

  // Pagination handlers
  const handleNextPage = useCallback(() => {
    if (nextCursor) {
      // Save current cursor to history for back navigation
      setCursorHistory((prev) => [...prev, cursor ?? ""]);
      setCursor(nextCursor);
    }
  }, [nextCursor, cursor]);

  const handlePreviousPage = useCallback(() => {
    if (cursorHistory.length > 0) {
      const previousCursor = cursorHistory[cursorHistory.length - 1];
      setCursorHistory((prev) => prev.slice(0, -1));
      setCursor(previousCursor || undefined);
    }
  }, [cursorHistory]);

  const filteredLogs = useMemo(() => {
    const items = logsData?.items ?? [];
    return items.filter((log) => {
      const matchesAction =
        !actionFilter ||
        log.action.toLowerCase().includes(actionFilter.toLowerCase());
      const matchesUser =
        !userFilter ||
        log.user_id.toLowerCase().includes(userFilter.toLowerCase()) ||
        (log.user_email?.toLowerCase().includes(userFilter.toLowerCase()) ??
          false);
      return matchesAction && matchesUser;
    });
  }, [logsData?.items, actionFilter, userFilter]);

  const handleExport = () => {
    const headers = [
      "Timestamp",
      "Action",
      "User",
      "Resource Type",
      "Resource ID",
      "IP Address",
    ];
    const rows = filteredLogs.map((log) => [
      log.timestamp,
      log.action,
      log.user_email ?? log.user_id,
      log.resource_type,
      log.resource_id,
      log.ip_address ?? "",
    ]);

    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleLogDetails = (logId: string) => {
    setExpandedLogId(expandedLogId === logId ? null : logId);
  };

  const getActionColor = (action: string) => {
    if (action.includes("delete"))
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    if (action.includes("create"))
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    if (action.includes("update"))
      return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
    if (action.includes("login"))
      return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    return "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400";
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="text-blue-500" size={28} />
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Audit Logs
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                System activity and security events
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <Download size={16} />
              Export
            </button>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="px-6 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4">
          <input
            type="text"
            placeholder="Filter by action..."
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            placeholder="Filter by user..."
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {filteredLogs.length} of {total} entries
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw size={32} className="animate-spin text-blue-500" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            <FileText size={48} className="mb-4 opacity-50" />
            <p className="text-lg">Failed to load audit logs</p>
            <button
              onClick={() => refetch()}
              className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <RefreshCw size={16} />
              Retry
            </button>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            <FileText size={48} className="mb-4 opacity-50" />
            <p className="text-lg">No audit logs found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredLogs.map((log) => (
              <div
                key={log.id}
                data-testid="audit-log-row"
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
              >
                <div
                  onClick={() => toggleLogDetails(log.id)}
                  className="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {expandedLogId === log.id ? (
                        <ChevronDown size={16} className="text-gray-400" />
                      ) : (
                        <ChevronRight size={16} className="text-gray-400" />
                      )}
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${getActionColor(log.action)}`}
                      >
                        {log.action}
                      </span>
                      <span className="text-gray-900 dark:text-gray-100">
                        {log.user_email ?? log.user_id}
                      </span>
                      <span className="text-gray-500 dark:text-gray-400 text-sm">
                        {log.resource_type}/{log.resource_id}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      {log.ip_address && <span>{log.ip_address}</span>}
                      <span>{new Date(log.timestamp).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedLogId === log.id && log.details && (
                  <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Details
                    </h4>
                    <pre className="text-sm text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-900 p-3 rounded-lg overflow-auto">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {!isLoading && !error && (
        <CursorPagination
          hasNextPage={hasNextPage}
          hasPreviousPage={hasPreviousPage}
          onNextPage={handleNextPage}
          onPreviousPage={handlePreviousPage}
          isLoading={isFetching}
          itemCount={filteredLogs.length}
          totalCount={total}
        />
      )}
    </div>
  );
}

export default AuditLogPage;
