/**
 * Shared Constants for Reference Components
 *
 * Centralizes icons, colors, and utility functions used across
 * ReferenceChip, ReferencePopover, autocomplete, and other components.
 */

import {
  Wrench,
  Sparkles,
  FileCode,
  Brain,
  List,
  ChevronRight,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type ReferenceType = "tool" | "skill" | "artifact" | "memory" | "plan";

// =============================================================================
// Icons
// =============================================================================

/**
 * Icon mapping for reference types.
 * Used consistently across all reference components.
 */
export const REFERENCE_ICONS: Record<ReferenceType | "type", typeof Wrench> = {
  tool: Wrench,
  skill: Sparkles,
  artifact: FileCode,
  memory: Brain,
  plan: List,
  type: ChevronRight, // For type suggestions in autocomplete
};

// =============================================================================
// Colors
// =============================================================================

/**
 * Primary icon/text colors for reference types (Radix design tokens).
 */
export const REFERENCE_ICON_COLORS: Record<ReferenceType | "type", string> = {
  tool: "text-primary-9",
  skill: "text-success-9",
  artifact: "text-neutral-9",
  memory: "text-info-9",
  plan: "text-warning-9",
  type: "text-neutral-11",
};

/**
 * Background colors for reference chips (Radix design tokens).
 */
export const REFERENCE_BG_COLORS: Record<ReferenceType, string> = {
  tool: "bg-primary-3",
  skill: "bg-success-3",
  artifact: "bg-neutral-3",
  memory: "bg-info-3",
  plan: "bg-warning-3",
};

/**
 * Border colors for reference chips (Radix design tokens).
 */
export const REFERENCE_BORDER_COLORS: Record<ReferenceType, string> = {
  tool: "border-primary-6",
  skill: "border-success-6",
  artifact: "border-neutral-6",
  memory: "border-info-6",
  plan: "border-warning-6",
};

/**
 * Text colors for reference labels (Radix design tokens).
 */
export const REFERENCE_TEXT_COLORS: Record<ReferenceType, string> = {
  tool: "text-primary-11",
  skill: "text-success-11",
  artifact: "text-neutral-11",
  memory: "text-info-11",
  plan: "text-warning-11",
};

// =============================================================================
// Labels
// =============================================================================

/**
 * Human-readable labels for reference types.
 */
export const REFERENCE_TYPE_LABELS: Record<ReferenceType, string> = {
  tool: "Tool",
  skill: "Skill",
  artifact: "Artifact",
  memory: "Memory",
  plan: "Plan",
};

/**
 * Descriptions for reference types (used in autocomplete).
 */
export const REFERENCE_TYPE_DESCRIPTIONS: Record<ReferenceType, string> = {
  tool: "Reference an MCP tool",
  skill: "Reference a skill",
  artifact: "Reference an artifact",
  memory: "Reference a memory note",
  plan: "Reference an execution plan",
};

// =============================================================================
// Utilities
// =============================================================================

/**
 * Get the icon component for a reference type.
 */
export function getReferenceIcon(type: ReferenceType | "type") {
  return REFERENCE_ICONS[type] || REFERENCE_ICONS.type;
}

/**
 * Get the icon color class for a reference type.
 */
export function getReferenceIconColor(type: ReferenceType | "type") {
  return REFERENCE_ICON_COLORS[type] || REFERENCE_ICON_COLORS.type;
}

/**
 * Get the background color class for a reference type.
 */
export function getReferenceBgColor(type: ReferenceType) {
  return REFERENCE_BG_COLORS[type] || REFERENCE_BG_COLORS.artifact;
}

/**
 * Get the border color class for a reference type.
 */
export function getReferenceBorderColor(type: ReferenceType) {
  return REFERENCE_BORDER_COLORS[type] || REFERENCE_BORDER_COLORS.artifact;
}

/**
 * Get the text color class for a reference type.
 */
export function getReferenceTextColor(type: ReferenceType) {
  return REFERENCE_TEXT_COLORS[type] || REFERENCE_TEXT_COLORS.artifact;
}

/**
 * Generate markdown reference syntax from components.
 */
export function toMarkdownReference(
  type: ReferenceType,
  qualifier: string,
  id?: string,
  label?: string,
): string {
  let ref: string;

  if (type === "tool" && id) {
    ref = `[[tool:${qualifier}:${id}]]`;
  } else {
    ref = `[[${type}:${qualifier}]]`;
  }

  if (label) {
    // Insert label before closing brackets
    ref = ref.slice(0, -2) + `|${label}]]`;
  }

  return ref;
}

/**
 * Parse a markdown reference string into components.
 * Returns null if the string is not a valid reference.
 */
export function parseMarkdownReference(ref: string): {
  type: ReferenceType;
  qualifier: string;
  id?: string;
  label?: string;
} | null {
  const match = ref.match(
    /^\[\[(tool|skill|artifact|memory|plan):([a-zA-Z0-9_:/-]+)(?:\|([^\]]+))?\]\]$/,
  );

  if (!match) {
    return null;
  }

  const [, type, qualifierId, label] = match;
  const validType = type as ReferenceType;

  // For tools, qualifier and id are separated by colon
  if (validType === "tool") {
    const parts = qualifierId.split(":");
    if (parts.length >= 2) {
      return {
        type: validType,
        qualifier: parts[0],
        id: parts.slice(1).join(":"),
        label,
      };
    }
  }

  // For other types, qualifier and id are the same
  return {
    type: validType,
    qualifier: qualifierId,
    id: qualifierId,
    label,
  };
}

// =============================================================================
// Validation
// =============================================================================

/**
 * Supported reference types for parsing.
 * All types now supported after Phase 4 data model changes.
 */
export const SUPPORTED_REFERENCE_TYPES: ReferenceType[] = [
  "tool",
  "skill",
  "artifact",
  "memory",
  "plan",
];

/**
 * Legacy constant for backwards compatibility.
 * @deprecated All types are now in SUPPORTED_REFERENCE_TYPES
 */
export const FUTURE_REFERENCE_TYPES: ReferenceType[] = [];

/**
 * Check if a type string is a valid reference type.
 */
export function isValidReferenceType(type: string): type is ReferenceType {
  return [...SUPPORTED_REFERENCE_TYPES, ...FUTURE_REFERENCE_TYPES].includes(
    type as ReferenceType,
  );
}

/**
 * Check if a reference type is currently supported.
 */
export function isSupportedReferenceType(type: ReferenceType): boolean {
  return SUPPORTED_REFERENCE_TYPES.includes(type);
}
