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

import { Button, Select } from "@/components/UI";

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
    "bg-success-3 text-success-11 dark:bg-success-a6 dark:text-success-5",
  update:
    "bg-primary-3 text-primary-11 dark:bg-primary-a6 dark:text-primary-5",
  delete:
    "bg-error-3 text-error-11 dark:bg-error-a6 dark:text-error-9",
  test: "bg-insight-2 text-insight-11 dark:bg-insight-a6 dark:text-insight-5",
  authorize:
    "bg-warning-3 text-warning-11 dark:bg-warning-a6 dark:text-warning-6",
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
      "bg-neutral-2 text-neutral-12"
    );
  };

  if (isLoading) {
    return (
      <div
        data-testid="loading-audit-logs"
        className="flex items-center justify-center gap-3 py-12"
      >
        <Loader2 className="h-6 w-6 animate-spin text-primary-9" />
        <span className="text-neutral-11">
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
        <AlertCircle className="h-12 w-12 text-error-9" />
        <p className="text-error-10 dark:text-error-7">
          Failed to load audit logs: {error}
        </p>
        <Button
          variant="primary"
          className="flex rounded-md bg-primary-10 px-4 py-2 text-neutral-12 hover:bg-primary-11"
          onClick={fetchLogs}
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    // eslint-disable-next-line no-restricted-syntax -- Large dialog panel requires specific min-width
    <div className="min-w-[500px]">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-insight-10" />
          <h3 className="text-lg font-semibold text-neutral-12">
            Audit Log
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {/* Event Type Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-neutral-9" />
            <Select
              className="px-3 py-1.5 text-sm -500 focus:ring-primary-7"
              data-testid="event-type-filter"
              value={eventTypeFilter}
              onChange={handleEventTypeChange}
            >
              <option value="">All Events</option>
              <option value="connection.created">Created</option>
              <option value="connection.updated">Updated</option>
              <option value="connection.deleted">Deleted</option>
              <option value="connection.tested">Tested</option>
              <option value="connection.oauth2_authorized">
                OAuth2 Authorized
              </option>
            </Select>
          </div>

          {/* Refresh Button */}
          <Button
            variant="secondary"
            className="flex .5 rounded-md border border-neutral-5 bg-neutral-1 px-3 py-1.5 text-sm text-neutral-11 hover:bg-neutral-1"
            onClick={fetchLogs}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>
      {/* Empty State */}
      {logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FileText className="mb-4 h-12 w-12 text-neutral-9" />
          <p className="text-neutral-10">
            No audit logs found for this connection.
          </p>
        </div>
      ) : (
        /* Log List */
        <div className="space-y-2">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-lg border border-neutral-5 bg-neutral-1 transition-shadow hover:shadow-sm"
            >
              {/* Entry Header */}
              <div
                className="flex cursor-pointer items-center justify-between p-3"
                onClick={() => toggleExpand(log.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-neutral-11">
                    {log.eventType}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${getActionColor(log.action)}`}
                  >
                    {log.action}
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  <span className="text-sm text-neutral-10">
                    {log.actorId}
                  </span>
                  <span className="text-sm text-neutral-9">
                    {formatDate(log.timestamp)}
                  </span>
                  <Button
                    variant="secondary"
                    className="rounded p-1 text-neutral-9 hover:bg-neutral-2 hover:text-neutral-11"
                    data-testid="expand-log"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleExpand(log.id);
                    }}
                    aria-label={expandedId === log.id ? "Collapse" : "Expand"}
                  >
                    {expandedId === log.id ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Expanded Details */}
              {expandedId === log.id && (
                <div className="border-t border-neutral-5 bg-neutral-1 p-4">
                  {/* Details JSON */}
                  <div className="mb-4">
                    <h4 className="mb-2 text-sm font-medium text-neutral-11">
                      Details
                    </h4>
                    <pre className="overflow-x-auto rounded-md bg-neutral-2 p-3 text-xs text-neutral-12">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </div>

                  {/* Metadata */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {log.ipAddress && (
                      <div>
                        <span className="font-medium text-neutral-11">
                          IP Address:
                        </span>
                        <span className="ml-2 font-mono text-neutral-12">
                          {log.ipAddress}
                        </span>
                      </div>
                    )}
                    {log.userAgent && (
                      <div className="col-span-2">
                        <span className="font-medium text-neutral-11">
                          User Agent:
                        </span>
                        <span className="ml-2 text-neutral-12">
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
