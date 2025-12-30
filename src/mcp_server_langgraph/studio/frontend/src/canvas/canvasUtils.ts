/**
 * Canvas Utility Functions
 *
 * Helper functions for the Canvas components, separated to allow
 * fast refresh to work properly for React components.
 */

import type { TabType } from "./CanvasTabs";

/**
 * Determine which tabs should be visible based on artifact content type.
 *
 * - Plain code: only Code tab
 * - Mermaid, HTML, JSX, markdown: Code + Preview tabs
 * - JSON: Code + Data tabs
 * - All content types always have Code tab
 */
export function getVisibleTabs(contentType: string): TabType[] {
  // Valid contentTypes: "code" | "markdown" | "json" | "jsx" | "mermaid" | "html"
  const previewableTypes = ["mermaid", "html", "jsx", "markdown"];
  const dataTypes = ["json"];

  const tabs: TabType[] = ["code"];

  // Defensive null check: runtime data may have undefined contentType
  // even if TypeScript says it's required (e.g., incomplete API response)
  if (!contentType) {
    return tabs;
  }

  const normalizedType = contentType.toLowerCase();

  if (previewableTypes.includes(normalizedType)) {
    tabs.push("preview");
  }

  if (dataTypes.includes(normalizedType)) {
    tabs.push("data");
  }

  return tabs;
}
