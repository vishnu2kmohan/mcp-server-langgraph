/**
 * JSONArtifact Component
 *
 * Displays JSON data in a collapsible tree view with copy functionality.
 */

import { useState, useCallback } from "react";
import { Copy, Check, ChevronDown, ChevronRight, Download } from "lucide-react";
import type { JSONArtifact as JSONArtifactType } from "../../types/artifacts";

export interface JSONArtifactProps {
  artifact: JSONArtifactType;
}

/**
 * Determine if a value is an object (not null, not array)
 */
function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Determine if a value is an array
 */
function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value);
}

/**
 * Get the type of a JSON value for styling
 */
function getValueType(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  if (typeof value === "string") return "string";
  if (isArray(value)) return "array";
  if (isObject(value)) return "object";
  return "unknown";
}

/**
 * Recursive JSON tree node component
 */
function JSONTreeNode({
  keyName,
  value,
  depth = 0,
  isLast = false,
  initialCollapsed = false,
  theme = "light",
}: {
  keyName?: string;
  value: unknown;
  depth?: number;
  isLast?: boolean;
  initialCollapsed?: boolean;
  theme?: "light" | "dark";
}) {
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsed);
  const valueType = getValueType(value);

  const toggleCollapse = useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  const indentSize = depth * 20;

  const keyColor = theme === "dark" ? "text-blue-400" : "text-blue-600";
  const stringColor = theme === "dark" ? "text-green-400" : "text-green-600";
  const numberColor = theme === "dark" ? "text-orange-400" : "text-orange-600";
  const booleanColor = theme === "dark" ? "text-purple-400" : "text-purple-600";
  const nullColor = theme === "dark" ? "text-gray-400" : "text-gray-500";
  const bracketColor = theme === "dark" ? "text-gray-300" : "text-gray-700";

  // Primitive values
  if (!isObject(value) && !isArray(value)) {
    return (
      <div
        className="font-mono text-sm"
        style={{ paddingLeft: `${indentSize}px` }}
      >
        {keyName && (
          <>
            <span className={keyColor}>"{keyName}"</span>
            <span className={bracketColor}>: </span>
          </>
        )}
        <span
          className={
            valueType === "string"
              ? stringColor
              : valueType === "number"
                ? numberColor
                : valueType === "boolean"
                  ? booleanColor
                  : nullColor
          }
        >
          {valueType === "string" ? `"${value}"` : String(value)}
        </span>
        {!isLast && <span className={bracketColor}>,</span>}
      </div>
    );
  }

  // Objects and arrays
  const isArr = isArray(value);
  const entries = isArr
    ? (value as unknown[]).map((v, i) => [String(i), v] as const)
    : Object.entries(value as Record<string, unknown>);
  const isEmpty = entries.length === 0;
  const openBracket = isArr ? "[" : "{";
  const closeBracket = isArr ? "]" : "}";

  return (
    <div className="font-mono text-sm">
      <div
        className="flex items-start hover:bg-opacity-10"
        style={{ paddingLeft: `${indentSize}px` }}
      >
        {!isEmpty && (
          <button
            onClick={toggleCollapse}
            className="mr-1 mt-0.5 hover:opacity-70"
            aria-label="Toggle collapse"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        )}
        {isEmpty && <span className="w-5" />}
        {keyName && (
          <>
            <span className={keyColor}>"{keyName}"</span>
            <span className={bracketColor}>: </span>
          </>
        )}
        <span className={bracketColor}>
          {openBracket}
          {isEmpty && closeBracket}
          {!isEmpty && isCollapsed && "..."}
          {!isEmpty && isCollapsed && closeBracket}
        </span>
        {!isLast && isCollapsed && <span className={bracketColor}>,</span>}
      </div>

      {!isCollapsed && !isEmpty && (
        <>
          {entries.map(([key, val], index) => (
            <JSONTreeNode
              key={key}
              keyName={isArr ? undefined : key}
              value={val}
              depth={depth + 1}
              isLast={index === entries.length - 1}
              initialCollapsed={initialCollapsed}
              theme={theme}
            />
          ))}
          <div
            className={`${bracketColor} font-mono text-sm`}
            style={{ paddingLeft: `${indentSize}px` }}
          >
            {closeBracket}
            {!isLast && <span>,</span>}
          </div>
        </>
      )}
    </div>
  );
}

export function JSONArtifact({ artifact }: JSONArtifactProps) {
  const [copied, setCopied] = useState(false);

  const { data, config, title } = artifact;
  const { collapsed = false, theme = "light" } = config || {};

  /**
   * Copy JSON to clipboard
   */
  const handleCopy = useCallback(async () => {
    try {
      const jsonString = JSON.stringify(data, null, 2);
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy JSON:", error);
    }
  }, [data]);

  /**
   * Download JSON as file
   */
  const handleDownload = useCallback(() => {
    const jsonString = JSON.stringify(data, null, 2);
    const filename = title
      ? title.endsWith(".json")
        ? title
        : `${title.replace(/\s+/g, "_")}.json`
      : "data.json";

    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [data, title]);

  const initialCollapsed = typeof collapsed === "boolean" ? collapsed : false;

  const themeClasses =
    theme === "dark"
      ? "bg-gray-900 text-gray-100 border-gray-700"
      : "bg-gray-50 text-gray-900 border-gray-200";

  return (
    <div
      className={`rounded-lg border ${themeClasses} overflow-hidden`}
      data-theme={theme}
      role="region"
      aria-label="JSON viewer"
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-2 border-b ${
          theme === "dark"
            ? "border-gray-700 bg-gray-800"
            : "border-gray-200 bg-gray-100"
        }`}
      >
        <div className="flex items-center gap-3">
          {title && <span className="font-medium">{title}</span>}
          <span
            className={`text-xs font-mono px-2 py-1 rounded ${
              theme === "dark"
                ? "bg-gray-700 text-gray-300"
                : "bg-gray-200 text-gray-700"
            }`}
          >
            JSON
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className={`flex items-center gap-2 px-3 py-1 text-sm rounded transition-colors ${
              theme === "dark"
                ? "hover:bg-gray-700 text-gray-300"
                : "hover:bg-gray-200 text-gray-700"
            }`}
            aria-label="Copy JSON"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-green-500" />
                <span className="text-green-500">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span>Copy</span>
              </>
            )}
          </button>
          <button
            onClick={handleDownload}
            className={`p-1.5 rounded transition-colors ${
              theme === "dark"
                ? "hover:bg-gray-700 text-gray-300"
                : "hover:bg-gray-200 text-gray-700"
            }`}
            aria-label="Download JSON"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* JSON Content */}
      <div className="p-4 overflow-auto max-h-[600px]">
        <JSONTreeNode
          value={data}
          initialCollapsed={initialCollapsed}
          theme={theme}
        />
      </div>
    </div>
  );
}
