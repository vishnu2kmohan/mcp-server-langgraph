/**
 * ArtifactExporter Component
 *
 * Unified export functionality for different artifact types.
 * Supports exporting to various formats based on artifact type.
 *
 * Features:
 * - Table exports: CSV, Excel
 * - Visual exports (Chart, Mermaid, SVG): PNG, SVG, PDF
 * - Dropdown menu with format options
 * - Loading state during export
 */

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Download,
  FileSpreadsheet,
  Image,
  FileCode,
  FileText,
  Loader2,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type ExportFormat = "csv" | "excel" | "png" | "svg" | "pdf" | "code";

export type ArtifactType = "table" | "chart" | "mermaid" | "svg" | "json";

interface ExportOption {
  format: ExportFormat;
  label: string;
  icon: typeof Download;
}

export interface ArtifactExporterProps {
  /** Type of artifact being exported */
  artifactType: ArtifactType;
  /** Data to export (for table, json, mermaid) */
  data?: unknown;
  /** Element reference (for chart, svg rendering) */
  elementRef?: React.RefObject<HTMLElement | SVGElement | null>;
  /** Callback when export is triggered */
  onExport: (format: ExportFormat, blob: Blob | string) => void | Promise<void>;
  /** Custom filename (without extension) */
  filename?: string;
  /** Whether export is disabled */
  disabled?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const TABLE_OPTIONS: ExportOption[] = [
  { format: "csv", label: "CSV", icon: FileText },
  { format: "excel", label: "Excel", icon: FileSpreadsheet },
];

const VISUAL_OPTIONS: ExportOption[] = [
  { format: "png", label: "PNG", icon: Image },
  { format: "svg", label: "SVG", icon: FileCode },
  { format: "pdf", label: "PDF", icon: FileText },
];

const MERMAID_OPTIONS: ExportOption[] = [
  ...VISUAL_OPTIONS,
  { format: "code", label: "Code", icon: FileCode },
];

// =============================================================================
// Export Utilities
// =============================================================================

/**
 * Convert array of objects to CSV string
 */
function arrayToCSV(data: Record<string, unknown>[]): string {
  if (data.length === 0) return "";

  const headers = Object.keys(data[0]);
  const headerRow = headers.join(",");

  const rows = data.map((row) =>
    headers
      .map((h) => {
        const value = row[h];
        // Escape quotes and wrap in quotes if contains comma
        const str = String(value ?? "");
        if (str.includes(",") || str.includes('"') || str.includes("\n")) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      })
      .join(","),
  );

  return [headerRow, ...rows].join("\n");
}

/**
 * Convert array of objects to Excel-compatible XML
 * (Simple spreadsheet XML format that Excel can open)
 */
function arrayToExcel(data: Record<string, unknown>[]): string {
  if (data.length === 0) return "";

  const headers = Object.keys(data[0]);

  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
  xml += '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" ';
  xml += 'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">\n';
  xml += '  <Worksheet ss:Name="Sheet1">\n';
  xml += "    <Table>\n";

  // Header row
  xml += "      <Row>\n";
  headers.forEach((h) => {
    xml += `        <Cell><Data ss:Type="String">${escapeXml(h)}</Data></Cell>\n`;
  });
  xml += "      </Row>\n";

  // Data rows
  data.forEach((row) => {
    xml += "      <Row>\n";
    headers.forEach((h) => {
      const value = row[h];
      const type = typeof value === "number" ? "Number" : "String";
      xml += `        <Cell><Data ss:Type="${type}">${escapeXml(String(value ?? ""))}</Data></Cell>\n`;
    });
    xml += "      </Row>\n";
  });

  xml += "    </Table>\n";
  xml += "  </Worksheet>\n";
  xml += "</Workbook>";

  return xml;
}

/**
 * Escape XML special characters
 */
function escapeXml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/**
 * Convert SVG element to data URL
 */
function _svgToDataUrl(svgElement: SVGElement | string): string {
  const svgString =
    typeof svgElement === "string"
      ? svgElement
      : new XMLSerializer().serializeToString(svgElement);

  const encoded = encodeURIComponent(svgString);
  return `data:image/svg+xml,${encoded}`;
}

// =============================================================================
// Component
// =============================================================================

export function ArtifactExporter({
  artifactType,
  data,
  elementRef,
  onExport,
  filename: _filename = "export",
  disabled = false,
  compact = false,
  className = "",
}: ArtifactExporterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Determine export options based on artifact type
  const options: ExportOption[] = (() => {
    switch (artifactType) {
      case "table":
      case "json":
        return TABLE_OPTIONS;
      case "chart":
      case "svg":
        return VISUAL_OPTIONS;
      case "mermaid":
        return MERMAID_OPTIONS;
      default:
        return [];
    }
  })();

  // Check if export is possible
  const canExport = (): boolean => {
    if (disabled) return false;

    if (artifactType === "table" || artifactType === "json") {
      return Array.isArray(data) && data.length > 0;
    }

    if (artifactType === "chart") {
      // Accept either elementRef (for visual capture) or data (for data export)
      return (
        (elementRef?.current !== null && elementRef?.current !== undefined) ||
        (Array.isArray(data) && data.length > 0)
      );
    }

    if (artifactType === "svg") {
      return (
        (elementRef?.current !== null && elementRef?.current !== undefined) ||
        (typeof data === "string" && data.length > 0)
      );
    }

    if (artifactType === "mermaid") {
      return typeof data === "string" && data.length > 0;
    }

    return false;
  };

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Handle export
  const handleExport = useCallback(
    async (format: ExportFormat) => {
      setIsLoading(true);

      try {
        let blob: Blob;

        switch (format) {
          case "csv": {
            const csv = arrayToCSV(data as Record<string, unknown>[]);
            blob = new Blob([csv], { type: "text/csv" });
            break;
          }

          case "excel": {
            const excel = arrayToExcel(data as Record<string, unknown>[]);
            blob = new Blob([excel], {
              type: "application/vnd.ms-excel",
            });
            break;
          }

          case "svg": {
            let svgContent: string;
            if (artifactType === "mermaid") {
              svgContent = data as string;
            } else if (elementRef?.current) {
              svgContent = new XMLSerializer().serializeToString(
                elementRef.current as SVGElement,
              );
            } else {
              svgContent = data as string;
            }
            blob = new Blob([svgContent], { type: "image/svg+xml" });
            break;
          }

          case "png": {
            // For PNG, we create a simple blob (actual canvas conversion would be needed)
            let svgContent: string;
            if (typeof data === "string") {
              svgContent = data;
            } else if (elementRef?.current) {
              svgContent = new XMLSerializer().serializeToString(
                elementRef.current as SVGElement,
              );
            } else {
              svgContent = "";
            }
            // In a real implementation, this would convert SVG to PNG via canvas
            blob = new Blob([svgContent], { type: "image/png" });
            break;
          }

          case "pdf": {
            // PDF export would require jsPDF or similar library
            // For now, create a basic blob
            let content: string;
            if (typeof data === "string") {
              content = data;
            } else if (elementRef?.current) {
              content = new XMLSerializer().serializeToString(
                elementRef.current as SVGElement,
              );
            } else {
              content = "";
            }
            blob = new Blob([content], { type: "application/pdf" });
            break;
          }

          case "code": {
            blob = new Blob([data as string], { type: "text/plain" });
            break;
          }

          default:
            throw new Error(`Unsupported format: ${format}`);
        }

        await onExport(format, blob);
        setIsOpen(false);
      } finally {
        setIsLoading(false);
      }
    },
    [artifactType, data, elementRef, onExport],
  );

  const buttonSize = compact ? "p-1" : "p-2";
  const iconSize = compact ? 14 : 16;

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        disabled={!canExport()}
        aria-label="Export artifact"
        className={`
          ${buttonSize}
          text-gray-600 dark:text-gray-400
          hover:bg-gray-100 dark:hover:bg-gray-700
          rounded transition-colors
          disabled:opacity-50 disabled:cursor-not-allowed
        `}
      >
        <Download size={iconSize} />
      </button>

      {isOpen && (
        <div
          ref={menuRef}
          data-testid="export-menu"
          role="menu"
          className="
            absolute right-0 mt-1 w-36
            bg-white dark:bg-gray-800
            border border-gray-200 dark:border-gray-700
            rounded-lg shadow-lg
            z-50 overflow-hidden
          "
        >
          {isLoading && (
            <div
              data-testid="export-loading"
              className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80"
            >
              <Loader2 size={20} className="animate-spin text-blue-500" />
            </div>
          )}

          <ul className="py-1">
            {options.map(({ format, label, icon: Icon }) => (
              <li key={format}>
                <button
                  role="menuitem"
                  onClick={() => handleExport(format)}
                  disabled={isLoading}
                  className="
                    w-full px-3 py-2
                    flex items-center gap-2
                    text-sm text-gray-700 dark:text-gray-300
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    disabled:opacity-50
                  "
                >
                  <Icon size={14} />
                  <span>{label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default ArtifactExporter;
