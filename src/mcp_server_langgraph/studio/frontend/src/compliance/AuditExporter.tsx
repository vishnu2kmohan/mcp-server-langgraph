/**
 * AuditExporter - Phase 5
 *
 * Compliance audit export functionality with format selection,
 * rate limiting, and watermarking support.
 */
import { useState, useCallback, useMemo } from "react";
import {
  Download,
  FileText,
  FileJson,
  File,
  Loader2,
  Check,
  AlertCircle,
} from "lucide-react";
import { cn } from "../utils/cn";

import { Button, Checkbox } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type ExportFormat = "csv" | "json" | "pdf";

export interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  action: string;
  resourceType: string;
  resourceId: string;
  metadata: Record<string, unknown>;
  ipAddress: string;
  userAgent: string;
}

export interface AuditFilter {
  startDate?: string;
  endDate?: string;
  userId?: string;
  action?: string;
  resourceType?: string;
}

export interface ExportRequest {
  format: ExportFormat;
  filters: AuditFilter;
  excludeFields?: string[];
  includeWatermark?: boolean;
}

export interface ExportResult {
  url: string;
}

export interface AuditExporterProps {
  auditLogs: AuditLog[];
  filters: AuditFilter;
  onExport: (request: ExportRequest) => Promise<ExportResult | void>;
  remainingExports?: number;
  maxExports?: number;
  showFieldSelection?: boolean;
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const EXPORT_FORMATS: {
  value: ExportFormat;
  label: string;
  icon: React.ElementType;
}[] = [
  { value: "csv", label: "CSV", icon: FileText },
  { value: "json", label: "JSON", icon: FileJson },
  { value: "pdf", label: "PDF", icon: File },
];

const FIELD_OPTIONS = [
  { key: "timestamp", label: "Timestamp" },
  { key: "userId", label: "User ID" },
  { key: "action", label: "Action" },
  { key: "resourceType", label: "Resource Type" },
  { key: "resourceId", label: "Resource ID" },
  { key: "ipAddress", label: "IP Address" },
  { key: "userAgent", label: "User Agent" },
];

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// =============================================================================
// Component
// =============================================================================

export function AuditExporter({
  auditLogs,
  filters,
  onExport,
  remainingExports,
  maxExports = 10,
  showFieldSelection = false,
  className,
}: AuditExporterProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("csv");
  const [isExporting, setIsExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<
    "idle" | "success" | "error"
  >("idle");
  const [error, setError] = useState<string | undefined>();
  const [includeWatermark, setIncludeWatermark] = useState(true);
  const [excludedFields, setExcludedFields] = useState<Set<string>>(new Set());

  const isRateLimited = remainingExports !== undefined && remainingExports <= 0;
  const isEmpty = auditLogs.length === 0;
  const canExport = !isEmpty && !isRateLimited && !isExporting;

  const handleFormatSelect = useCallback((format: ExportFormat) => {
    setSelectedFormat(format);
    setExportStatus("idle");
  }, []);

  const handleFieldToggle = useCallback((field: string) => {
    setExcludedFields((prev) => {
      const next = new Set(prev);
      if (next.has(field)) {
        next.delete(field);
      } else {
        next.add(field);
      }
      return next;
    });
  }, []);

  const handleExport = useCallback(async () => {
    if (!canExport) return;

    setIsExporting(true);
    setExportStatus("idle");
    setError(undefined);

    try {
      await onExport({
        format: selectedFormat,
        filters,
        excludeFields:
          excludedFields.size > 0 ? Array.from(excludedFields) : undefined,
        includeWatermark:
          selectedFormat === "pdf" ? includeWatermark : undefined,
      });
      setExportStatus("success");
    } catch (err) {
      setExportStatus("error");
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setIsExporting(false);
    }
  }, [
    canExport,
    onExport,
    selectedFormat,
    filters,
    excludedFields,
    includeWatermark,
  ]);

  const dateRangeText = useMemo(() => {
    const start = filters.startDate
      ? formatDate(filters.startDate)
      : "All time";
    const end = filters.endDate ? formatDate(filters.endDate) : "Present";
    return { start, end };
  }, [filters.startDate, filters.endDate]);

  return (
    <div
      data-testid="audit-exporter"
      className={cn(
        "bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Download
            size={18}
            className="text-neutral-500 dark:text-neutral-400"
          />
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Export Audit Logs
          </h3>
        </div>
        {remainingExports !== undefined && (
          <span
            className={cn(
              "text-xs",
              isRateLimited
                ? "text-error-500"
                : "text-neutral-500 dark:text-neutral-400",
            )}
          >
            {isRateLimited
              ? "Rate limit reached"
              : `${remainingExports} of ${maxExports} exports remaining`}
          </span>
        )}
      </div>
      {/* Summary */}
      <div className="mb-4 p-3 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg">
        <div className="text-sm text-neutral-700 dark:text-neutral-300">
          <span className="font-medium">{auditLogs.length} records</span>
          {isEmpty ? (
            <span className="ml-2 text-neutral-500 dark:text-neutral-400">
              No audit logs to export
            </span>
          ) : (
            <span className="ml-2 text-neutral-500 dark:text-neutral-400">
              from {dateRangeText.start} to {dateRangeText.end}
            </span>
          )}
        </div>
      </div>
      {/* Format Selection */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">
          Export Format
        </label>
        <div
          role="radiogroup"
          aria-label="Export format"
          className="flex gap-2"
        >
          {EXPORT_FORMATS.map(({ value, label, icon: Icon }) => (
            <Button
              key={value}
              type="button"
              role="radio"
              aria-checked={selectedFormat === value}
              data-testid={`format-${value}`}
              onClick={() => handleFormatSelect(value)}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors",
                selectedFormat === value
                  ? "selected border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300"
                  : "border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:border-neutral-300 dark:border-neutral-600 dark:hover:border-neutral-600",
              )}
            >
              <Icon size={16} />
              <span className="text-sm font-medium">{label}</span>
            </Button>
          ))}
        </div>
      </div>
      {/* PDF Watermark Option */}
      {selectedFormat === "pdf" && (
        <div className="mb-4">
          <Checkbox
            checked={includeWatermark}
            onChange={setIncludeWatermark}
            label="Include watermark (user ID, timestamp)"
            size="sm"
          />
        </div>
      )}
      {/* Field Selection */}
      {showFieldSelection && (
        <div data-testid="field-selection" className="mb-4">
          <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">
            Fields to Include
          </label>
          <div className="grid grid-cols-2 gap-2">
            {FIELD_OPTIONS.map(({ key, label }) => (
              <Checkbox
                key={key}
                checked={!excludedFields.has(key)}
                onChange={() => handleFieldToggle(key)}
                label={label}
                size="sm"
              />
            ))}
          </div>
        </div>
      )}
      {/* Export Button */}
      <Button
        type="button"
        data-testid="export-button"
        onClick={handleExport}
        disabled={!canExport}
        className={cn(
          "w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors",
          canExport
            ? "bg-primary-500 text-white hover:bg-primary-600"
            : "bg-neutral-200 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 cursor-not-allowed",
        )}
      >
        {isExporting ? (
          <>
            <Loader2
              data-testid="export-loading"
              size={16}
              className="animate-spin"
            />
            <span>Exporting...</span>
          </>
        ) : (
          <>
            <Download size={16} />
            <span>Export {selectedFormat.toUpperCase()}</span>
          </>
        )}
      </Button>
      {/* Status Messages */}
      {exportStatus === "success" && (
        <div
          role="status"
          data-testid="export-success"
          className="mt-3 flex items-center gap-2 text-success-600 dark:text-success-400"
        >
          <Check size={16} />
          <span className="text-sm">Export complete! Download started.</span>
        </div>
      )}
      {exportStatus === "error" && error && (
        <div
          role="alert"
          className="mt-3 flex items-center gap-2 text-error-600 dark:text-error-400"
        >
          <AlertCircle size={16} />
          <span className="text-sm">{error}</span>
        </div>
      )}
    </div>
  );
}
