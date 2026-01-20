/**
 * OTELDetailsPanel Component
 *
 * Expandable panel for JSON attributes, headers, and payloads.
 * Supports summary view (human-readable) and raw view (JSON).
 *
 * Features:
 * - Summary/Raw view toggle
 * - Tabbed layout for multiple data sections
 * - Copy to clipboard
 * - Format hints for smart value rendering
 * - Headers variant for HTTP header display
 */

import { useState, useCallback, useMemo, type HTMLAttributes, type KeyboardEvent } from "react";
import { Copy, Check, X, Code, List } from "lucide-react";

import { cn } from "../../../utils/cn";
import { Button } from "@/components/UI";
import { SmartValue, type SmartValueType } from "./SmartValue";

// =============================================================================
// Types
// =============================================================================

export type OTELDetailsPanelVariant = "json" | "headers" | "tabbed";
export type OTELDetailsPanelView = "summary" | "raw";

export interface OTELDetailsPanelTab {
  key: string;
  label: string;
  data: unknown;
}

export interface OTELDetailsPanelProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "children"> {
  /** Data to display */
  data: Record<string, unknown>;
  /** Panel title */
  title?: string;
  /** Display variant */
  variant?: OTELDetailsPanelVariant;
  /** Tabs for tabbed variant */
  tabs?: OTELDetailsPanelTab[];
  /** Default view mode */
  defaultView?: OTELDetailsPanelView;
  /** Show view toggle button */
  showViewToggle?: boolean;
  /** Format hints for specific keys */
  formatHints?: Record<string, SmartValueType>;
  /** Callback when copy button clicked */
  onCopy?: () => void;
  /** Callback when close button clicked */
  onClose?: () => void;
}

// =============================================================================
// Helper Components
// =============================================================================

interface KeyValueRowProps {
  keyName: string;
  value: unknown;
  formatHint?: SmartValueType;
}

function KeyValueRow({ keyName, value, formatHint }: KeyValueRowProps) {
  return (
    <div className="flex items-start gap-3 py-1.5">
      <span className="text-xs font-medium text-neutral-10 min-w-0 shrink-0">
        {keyName}
      </span>
      <span className="text-xs font-mono text-neutral-11 min-w-0 break-all">
        <SmartValue value={value} type={formatHint} />
      </span>
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

/**
 * OTEL Details Panel Component
 *
 * @example
 * ```tsx
 * <OTELDetailsPanel
 *   data={{ "service.name": "api", duration_ms: 1234 }}
 *   title="Span Attributes"
 *   formatHints={{ duration_ms: "duration" }}
 * />
 * ```
 */
export function OTELDetailsPanel({
  data,
  title,
  variant = "json",
  tabs,
  defaultView = "summary",
  showViewToggle = true,
  formatHints = {},
  onCopy,
  onClose,
  className,
  ...props
}: OTELDetailsPanelProps) {
  const [view, setView] = useState<OTELDetailsPanelView>(defaultView);
  const [copied, setCopied] = useState(false);
  const [activeTabIndex, setActiveTabIndex] = useState(0);

  // Get current data for tabbed variant
  const currentData = useMemo(() => {
    if (variant === "tabbed" && tabs && tabs.length > 0) {
      return tabs[activeTabIndex]?.data as Record<string, unknown> ?? {};
    }
    return data ?? {};
  }, [variant, tabs, activeTabIndex, data]);

  // Determine if data is empty (check currentData, not raw data)
  const isEmpty = useMemo(() => {
    if (currentData === null || currentData === undefined) return true;
    if (typeof currentData !== "object") return false;
    return Object.keys(currentData).length === 0;
  }, [currentData]);

  // Handle copy to clipboard
  const handleCopy = useCallback(async () => {
    try {
      const jsonStr = JSON.stringify(currentData, null, 2);
      await navigator.clipboard.writeText(jsonStr);
      setCopied(true);
      onCopy?.();
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  }, [currentData, onCopy]);

  // Toggle view
  const toggleView = useCallback(() => {
    setView((v) => (v === "summary" ? "raw" : "summary"));
  }, []);

  // Handle tab keyboard navigation
  const handleTabKeyDown = useCallback(
    (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
      if (!tabs) return;

      let newIndex = index;
      if (e.key === "ArrowRight") {
        newIndex = (index + 1) % tabs.length;
        e.preventDefault();
      } else if (e.key === "ArrowLeft") {
        newIndex = (index - 1 + tabs.length) % tabs.length;
        e.preventDefault();
      }

      if (newIndex !== index) {
        setActiveTabIndex(newIndex);
        // Focus the new tab
        const tabButtons = e.currentTarget.parentElement?.querySelectorAll('[role="tab"]');
        (tabButtons?.[newIndex] as HTMLElement)?.focus();
      }
    },
    [tabs],
  );

  // Render summary view
  const renderSummaryView = () => {
    if (isEmpty) {
      return (
        <div className="text-xs text-neutral-9 italic py-2">No data</div>
      );
    }

    return (
      <div className="space-y-0.5">
        {Object.entries(currentData as Record<string, unknown>).map(([key, value]) => (
          <KeyValueRow
            key={key}
            keyName={key}
            value={value}
            formatHint={formatHints[key]}
          />
        ))}
      </div>
    );
  };

  // Render raw JSON view
  const renderRawView = () => {
    if (isEmpty) {
      return (
        <div className="text-xs text-neutral-9 italic py-2">No data</div>
      );
    }

    return (
      <pre className="text-xs font-mono text-neutral-11 overflow-x-auto whitespace-pre-wrap">
        {JSON.stringify(currentData, null, 2)}
      </pre>
    );
  };

  // Render headers variant (specialized key-value display)
  const renderHeadersView = () => {
    if (isEmpty) {
      return (
        <div className="text-xs text-neutral-9 italic py-2">No data</div>
      );
    }

    return (
      <div className="space-y-0.5">
        {Object.entries(currentData as Record<string, unknown>).map(([key, value]) => (
          <div key={key} className="flex items-start gap-3 py-1.5">
            <span className="text-xs font-medium text-neutral-10 min-w-0 shrink-0">
              {key}
            </span>
            <span className="text-xs font-mono text-neutral-11 min-w-0 break-all">
              {String(value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  // Render tabbed variant
  const renderTabbedView = () => {
    if (!tabs || tabs.length === 0) {
      return renderSummaryView();
    }

    return (
      <div>
        {/* Tab list */}
        <div
          role="tablist"
          className="flex gap-1 border-b border-neutral-5 mb-3"
        >
          {tabs.map((tab, index) => (
            <Button
              key={tab.key}
              role="tab"
              variant="ghost"
              size="sm"
              aria-selected={index === activeTabIndex}
              aria-controls={`tabpanel-${tab.key}`}
              tabIndex={index === activeTabIndex ? 0 : -1}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-none",
                index === activeTabIndex
                  ? "text-primary-11 border-b-2 border-primary-9 -mb-0.5"
                  : "text-neutral-10 hover:text-neutral-12",
              )}
              onClick={() => setActiveTabIndex(index)}
              onKeyDown={(e) => handleTabKeyDown(e, index)}
            >
              {tab.label}
            </Button>
          ))}
        </div>

        {/* Tab panel */}
        <div
          role="tabpanel"
          id={`tabpanel-${tabs[activeTabIndex]?.key}`}
          aria-labelledby={`tab-${tabs[activeTabIndex]?.key}`}
        >
          {view === "summary" ? renderSummaryView() : renderRawView()}
        </div>
      </div>
    );
  };

  // Render content based on variant
  const renderContent = () => {
    if (variant === "tabbed") {
      return renderTabbedView();
    }
    if (variant === "headers") {
      return renderHeadersView();
    }
    return view === "summary" ? renderSummaryView() : renderRawView();
  };

  return (
    <div
      role="region"
      aria-label={title ?? "Details"}
      className={cn(
        "rounded-lg border border-neutral-5 bg-neutral-1 p-4",
        "dark:bg-neutral-2",
        className,
      )}
      {...props}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-3">
        {title && (
          <h3 className="text-sm font-semibold text-neutral-12">{title}</h3>
        )}

        <div className="flex items-center gap-1 ml-auto">
          {/* View toggle */}
          {showViewToggle && variant !== "headers" && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={toggleView}
              className={cn(
                "inline-flex items-center gap-1 px-2 py-1 text-xs font-medium",
                "text-neutral-10 hover:text-neutral-12",
              )}
              aria-label={view === "summary" ? "Switch to raw view" : "Switch to summary view"}
            >
              {view === "summary" ? (
                <>
                  <Code size={12} aria-hidden="true" />
                  <span>Raw</span>
                </>
              ) : (
                <>
                  <List size={12} aria-hidden="true" />
                  <span>Summary</span>
                </>
              )}
            </Button>
          )}

          {/* Copy button */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-1 text-xs font-medium",
              "text-neutral-10 hover:text-neutral-12",
            )}
            aria-label="Copy to clipboard"
          >
            {copied ? (
              <Check size={12} className="text-success-10" aria-hidden="true" />
            ) : (
              <Copy size={12} aria-hidden="true" />
            )}
            <span>Copy</span>
          </Button>

          {/* Close button */}
          {onClose && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onClose}
              className={cn(
                "inline-flex items-center justify-center w-6 h-6 p-0",
                "text-neutral-10 hover:text-neutral-12",
              )}
              aria-label="Close"
            >
              <X size={14} aria-hidden="true" />
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      {renderContent()}
    </div>
  );
}

export default OTELDetailsPanel;
