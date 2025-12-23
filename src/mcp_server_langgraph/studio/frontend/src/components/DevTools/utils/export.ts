/**
 * Export Utilities for DevTools
 *
 * Functions for exporting console and network logs to JSON/CSV formats.
 */

import type { ConsoleEntry, NetworkEntry } from "../types";

// =============================================================================
// JSON Export
// =============================================================================

/**
 * Export data to JSON string with pretty formatting.
 */
export function exportToJSON(data: unknown): string {
  return JSON.stringify(data, null, 2);
}

// =============================================================================
// CSV Export
// =============================================================================

/**
 * Escape a value for CSV format.
 */
function escapeCSVValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  const stringValue = String(value);

  // If value contains comma, newline, or quote, wrap in quotes and escape quotes
  if (
    stringValue.includes(",") ||
    stringValue.includes("\n") ||
    stringValue.includes('"')
  ) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }

  return stringValue;
}

/**
 * Export array of objects to CSV string.
 */
export function exportToCSV(
  data: Record<string, unknown>[],
  columns?: string[],
): string {
  if (data.length === 0) {
    return "";
  }

  // Determine columns from first object if not provided
  const cols = columns ?? Object.keys(data[0]);

  // Create header row
  const header = cols.join(",");

  // Create data rows
  const rows = data.map((row) =>
    cols.map((col) => escapeCSVValue(row[col])).join(","),
  );

  return [header, ...rows].join("\n");
}

// =============================================================================
// Console Entry Formatting
// =============================================================================

export interface FormattedConsoleEntry {
  timestamp: string;
  level: string;
  source: string;
  message: string;
  data: string;
  stackTrace: string;
}

/**
 * Format console entries for export.
 */
export function formatConsoleEntriesForExport(
  entries: ConsoleEntry[],
): FormattedConsoleEntry[] {
  return entries.map((entry) => ({
    timestamp: new Date(entry.timestamp).toISOString(),
    level: entry.level,
    source: entry.source,
    message: entry.message,
    data: entry.data ? JSON.stringify(entry.data) : "",
    stackTrace: entry.stackTrace ?? "",
  }));
}

// =============================================================================
// Network Entry Formatting
// =============================================================================

export interface FormattedNetworkEntry {
  startTime: string;
  method: string;
  url: string;
  status: string;
  statusCode: number | string;
  duration: number | string;
  requestSize: number | string;
  responseSize: number | string;
  requestBody: string;
  responseBody: string;
  source: string;
}

/**
 * Format network entries for export.
 */
export function formatNetworkEntriesForExport(
  entries: NetworkEntry[],
): FormattedNetworkEntry[] {
  return entries.map((entry) => ({
    startTime: new Date(entry.startTime).toISOString(),
    method: entry.method,
    url: entry.url,
    status: entry.status,
    statusCode: entry.statusCode ?? "",
    duration: entry.duration ?? "",
    requestSize: entry.requestSize ?? "",
    responseSize: entry.responseSize ?? "",
    requestBody: entry.requestBody ? JSON.stringify(entry.requestBody) : "",
    responseBody: entry.responseBody ? JSON.stringify(entry.responseBody) : "",
    source: entry.source ?? "",
  }));
}

// =============================================================================
// File Download
// =============================================================================

/**
 * Trigger a file download in the browser.
 */
export function downloadFile(
  content: string,
  filename: string,
  mimeType: string,
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

// =============================================================================
// High-Level Export Functions
// =============================================================================

/**
 * Export console entries to JSON file.
 */
export function exportConsoleToJSON(entries: ConsoleEntry[]): void {
  const formatted = formatConsoleEntriesForExport(entries);
  const content = exportToJSON(formatted);
  const filename = `console-log-${new Date().toISOString().slice(0, 10)}.json`;
  downloadFile(content, filename, "application/json");
}

/**
 * Export console entries to CSV file.
 */
export function exportConsoleToCSV(entries: ConsoleEntry[]): void {
  const formatted = formatConsoleEntriesForExport(entries);
  const content = exportToCSV(
    formatted as unknown as Record<string, unknown>[],
  );
  const filename = `console-log-${new Date().toISOString().slice(0, 10)}.csv`;
  downloadFile(content, filename, "text/csv");
}

/**
 * Export network entries to JSON file.
 */
export function exportNetworkToJSON(entries: NetworkEntry[]): void {
  const formatted = formatNetworkEntriesForExport(entries);
  const content = exportToJSON(formatted);
  const filename = `network-log-${new Date().toISOString().slice(0, 10)}.json`;
  downloadFile(content, filename, "application/json");
}

/**
 * Export network entries to CSV file.
 */
export function exportNetworkToCSV(entries: NetworkEntry[]): void {
  const formatted = formatNetworkEntriesForExport(entries);
  const content = exportToCSV(
    formatted as unknown as Record<string, unknown>[],
  );
  const filename = `network-log-${new Date().toISOString().slice(0, 10)}.csv`;
  downloadFile(content, filename, "text/csv");
}
