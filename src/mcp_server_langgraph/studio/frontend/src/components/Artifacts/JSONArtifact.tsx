/**
 * JSONArtifact Component
 *
 * Displays JSON data in a collapsible tree view with copy functionality.
 */

import { useState, useCallback } from "react";
import { Copy, Check, ChevronDown, ChevronRight, Download } from "lucide-react";
import type { JSONArtifact as JSONArtifactType } from "../../types/artifacts";

import { Button } from "@/components/UI";
import { cn } from "@/utils/cn";
import { getIndentClass } from "@/utils/indent";

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

  const keyColor = theme === "dark" ? "text-primary-7" : "text-primary-10";
  const stringColor =
    theme === "dark" ? "text-success-7" : "text-success-10";
  const numberColor =
    theme === "dark" ? "text-grafana-5" : "text-grafana-10";
  const booleanColor =
    theme === "dark" ? "text-insight-9" : "text-insight-10";
  const nullColor =
    theme === "dark"
      ? "text-neutral-9"
      : "text-neutral-10";
  const bracketColor =
    theme === "dark"
      ? "text-neutral-9"
      : "text-neutral-11";

  // Primitive values
  if (!isObject(value) && !isArray(value)) {
    return (
      <div
        className={cn("font-mono text-sm", getIndentClass(indentSize))}
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
        className={cn("flex items-start hover:bg-opacity-10", getIndentClass(indentSize))}
      >
        {!isEmpty && (
          <Button
            variant="primary"
            className="mr-1 mt-0.5 hover:opacity-70"
            onClick={toggleCollapse}
            aria-label="Toggle collapse">
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
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
            className={cn(`${bracketColor} font-mono text-sm`, getIndentClass(indentSize))}
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
      ? "bg-neutral-2 text-neutral-9 border-neutral-7"
      : "bg-neutral-1 text-neutral-12 border-neutral-5";

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
            ? "border-neutral-7 bg-neutral-3"
            : "border-neutral-5 bg-neutral-2"
        }`}
      >
        <div className="flex items-center gap-3">
          {title && <span className="font-medium">{title}</span>}
          <span
            className={`text-xs font-mono px-2 py-1 rounded ${
              theme === "dark"
                ? "bg-neutral-4 text-neutral-9"
                : "bg-neutral-3 text-neutral-11"
            }`}
          >
            JSON
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="primary"
            size="sm"
            className="flex px-3 py-1 text-sm rounded"
            onClick={handleCopy}
            aria-label="Copy JSON">
            {copied ? (
              <>
                <Check className="w-4 h-4 text-success-9" />
                <span className="text-success-9">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span>Copy</span>
              </>
            )}
          </Button>
          <Button size="icon" variant="ghost"
            className="p-1.5 rounded"
            onClick={handleDownload}
            aria-label="Download JSON"
          >
            <Download className="w-4 h-4" />
          </Button>
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
