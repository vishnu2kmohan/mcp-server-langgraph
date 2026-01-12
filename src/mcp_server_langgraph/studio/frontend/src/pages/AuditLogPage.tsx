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
import { CursorPagination, Button, Input } from "../components/UI";

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
      return "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400";
    if (action.includes("create"))
      return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400";
    if (action.includes("update"))
      return "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400";
    if (action.includes("login"))
      return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400";
    return "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 dark:bg-neutral-900/30 dark:text-neutral-400";
  };

  return (
    <div className="h-screen flex flex-col bg-neutral-50 dark:bg-neutral-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="text-primary-500" size={28} />
            <div>
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                Audit Logs
              </h1>
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                System activity and security events
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              className="flex px-4 py-2 bg-neutral-100 dark:bg-neutral-700 rounded-lg hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600"
              onClick={handleExport}
            >
              <Download size={16} />
              Export
            </Button>
            <Button
              variant="secondary"
              className="flex px-4 py-2 bg-neutral-100 dark:bg-neutral-700 rounded-lg hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600"
              onClick={() => refetch()}
            >
              <RefreshCw size={16} />
              Refresh
            </Button>
          </div>
        </div>
      </header>
      {/* Filters */}
      <div className="px-6 py-3 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-4">
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
            placeholder="Filter by action..."
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
          />
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
            placeholder="Filter by user..."
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
          />
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {filteredLogs.length} of {total} entries
          </span>
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw size={32} className="animate-spin text-primary-500" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-neutral-500 dark:text-neutral-400">
            <FileText size={48} className="mb-4 opacity-50" />
            <p className="text-lg">Failed to load audit logs</p>
            <Button
              variant="primary"
              className="mt-4 flex px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              onClick={() => refetch()}
            >
              <RefreshCw size={16} />
              Retry
            </Button>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-neutral-500 dark:text-neutral-400">
            <FileText size={48} className="mb-4 opacity-50" />
            <p className="text-lg">No audit logs found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredLogs.map((log) => (
              <div
                key={log.id}
                data-testid="audit-log-row"
                className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
              >
                <div
                  onClick={() => toggleLogDetails(log.id)}
                  className="p-4 cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {expandedLogId === log.id ? (
                        <ChevronDown
                          size={16}
                          className="text-neutral-400 dark:text-neutral-400"
                        />
                      ) : (
                        <ChevronRight
                          size={16}
                          className="text-neutral-400 dark:text-neutral-400"
                        />
                      )}
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${getActionColor(log.action)}`}
                      >
                        {log.action}
                      </span>
                      <span className="text-neutral-900 dark:text-neutral-100">
                        {log.user_email ?? log.user_id}
                      </span>
                      <span className="text-neutral-500 dark:text-neutral-400 text-sm">
                        {log.resource_type}/{log.resource_id}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-400">
                      {log.ip_address && <span>{log.ip_address}</span>}
                      <span>{new Date(log.timestamp).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedLogId === log.id && log.details && (
                  <div className="px-4 pb-4 pt-2 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
                    <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                      Details
                    </h4>
                    <pre className="text-sm text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 p-3 rounded-lg overflow-auto">
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
