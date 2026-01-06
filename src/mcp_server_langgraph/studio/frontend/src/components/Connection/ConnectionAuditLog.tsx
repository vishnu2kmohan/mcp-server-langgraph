/**
 * ConnectionAuditLog Component
 *
 * Displays audit trail for connection operations.
 * Shows event history with expandable details.
 */

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Loader2,
  FileText,
  Filter,
} from "lucide-react";
import { authenticatedFetch } from "../../utils/authenticatedFetch";
import { transformSnakeToCamel } from "../../api/transforms";

interface AuditLogEntry {
  id: string;
  eventType: string;
  resourceType: string;
  resourceId: string;
  actorId: string;
  action: string;
  details: Record<string, unknown>;
  ipAddress: string | null;
  userAgent: string | null;
  timestamp: string;
}

interface AuditLogResponse {
  logs: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

interface ConnectionAuditLogProps {
  connectionId: string;
}

// Action badge colors
const actionColors: Record<string, string> = {
  create:
    "bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300",
  update: "bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300",
  delete: "bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300",
  test: "bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300",
  authorize:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300",
};

export function ConnectionAuditLog({ connectionId }: ConnectionAuditLogProps) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("");

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      let url = `/api/v1/connections/${connectionId}/audit`;
      if (eventTypeFilter) {
        url = `/api/v1/connections/audit/logs?resource_id=${connectionId}&event_type=${eventTypeFilter}`;
      }

      const response = await authenticatedFetch(url);
      if (!response.ok) {
        throw new Error("Failed to fetch audit logs");
      }

      const rawData = await response.json();
      const data = transformSnakeToCamel<AuditLogResponse>(rawData);
      setLogs(data.logs);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load audit logs",
      );
    } finally {
      setIsLoading(false);
    }
  }, [connectionId, eventTypeFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const handleEventTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setEventTypeFilter(e.target.value);
  };

  const getActionColor = (action: string) => {
    return (
      actionColors[action] ||
      "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
    );
  };

  if (isLoading) {
    return (
      <div
        data-testid="loading-audit-logs"
        className="flex items-center justify-center gap-3 py-12"
      >
        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        <span className="text-gray-600 dark:text-gray-400">
          Loading audit logs...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-4 py-12"
        role="alert"
      >
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="text-red-600 dark:text-red-400">
          Failed to load audit logs: {error}
        </p>
        <button
          onClick={fetchLogs}
          className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="min-w-[500px]">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-purple-600" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Audit Log
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {/* Event Type Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              data-testid="event-type-filter"
              value={eventTypeFilter}
              onChange={handleEventTypeChange}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="">All Events</option>
              <option value="connection.created">Created</option>
              <option value="connection.updated">Updated</option>
              <option value="connection.deleted">Deleted</option>
              <option value="connection.tested">Tested</option>
              <option value="connection.oauth2_authorized">
                OAuth2 Authorized
              </option>
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchLogs}
            className="flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Empty State */}
      {logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FileText className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">
            No audit logs found for this connection.
          </p>
        </div>
      ) : (
        /* Log List */
        <div className="space-y-2">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-lg border border-gray-200 bg-white transition-shadow hover:shadow-sm dark:border-gray-700 dark:bg-gray-800"
            >
              {/* Entry Header */}
              <div
                className="flex cursor-pointer items-center justify-between p-3"
                onClick={() => toggleExpand(log.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-gray-700 dark:text-gray-300">
                    {log.eventType}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${getActionColor(log.action)}`}
                  >
                    {log.action}
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {log.actorId}
                  </span>
                  <span className="text-sm text-gray-400 dark:text-gray-500">
                    {formatDate(log.timestamp)}
                  </span>
                  <button
                    data-testid="expand-log"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleExpand(log.id);
                    }}
                    className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                    aria-label={expandedId === log.id ? "Collapse" : "Expand"}
                  >
                    {expandedId === log.id ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Expanded Details */}
              {expandedId === log.id && (
                <div className="border-t border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50">
                  {/* Details JSON */}
                  <div className="mb-4">
                    <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                      Details
                    </h4>
                    <pre className="overflow-x-auto rounded-md bg-gray-100 p-3 text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </div>

                  {/* Metadata */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {log.ipAddress && (
                      <div>
                        <span className="font-medium text-gray-600 dark:text-gray-400">
                          IP Address:
                        </span>
                        <span className="ml-2 font-mono text-gray-800 dark:text-gray-200">
                          {log.ipAddress}
                        </span>
                      </div>
                    )}
                    {log.userAgent && (
                      <div className="col-span-2">
                        <span className="font-medium text-gray-600 dark:text-gray-400">
                          User Agent:
                        </span>
                        <span className="ml-2 text-gray-800 dark:text-gray-200">
                          {log.userAgent}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
