/**
 * MDX Parser
 *
 * Lightweight parser for MDX content that extracts known components
 * and renders them as React elements without full MDX compilation.
 *
 * Supported components (Mintlify-compatible):
 * - Callout, Note, Warning, Tip
 * - Accordion, AccordionGroup
 * - Card, CardGroup
 * - Tabs, Tab
 * - Steps, Step
 */

// ============================================================================
// Types
// ============================================================================

export interface MDXParsedNode {
  /** Node type: text or component */
  type: "text" | "component";
  /** Raw content (for text nodes) */
  content?: string;
  /** Component name (for component nodes) */
  component?: string;
  /** Component props (for component nodes) */
  props?: Record<string, string | number | boolean>;
  /** Children content (for component nodes) */
  children?: string;
}

// ============================================================================
// Known Components
// ============================================================================

const KNOWN_COMPONENTS = new Set([
  // Callouts
  "Callout",
  "Note",
  "Warning",
  "Tip",
  "Info",
  "Check",
  // Accordion
  "Accordion",
  "AccordionGroup",
  // Cards
  "Card",
  "CardGroup",
  // Tabs
  "Tabs",
  "Tab",
  // Steps
  "Steps",
  "Step",
  // Code
  "CodeGroup",
  // Layout
  "Frame",
  "Expandable",
  "Icon",
  // API Documentation
  "ResponseField",
  "ParamField",
]);

/**
 * Returns list of known MDX components
 */
export function extractMDXComponents(): string[] {
  return Array.from(KNOWN_COMPONENTS);
}

// ============================================================================
// Prop Parsing
// ============================================================================

/**
 * Parse component props from opening tag
 */
function parseProps(
  propsString: string,
): Record<string, string | number | boolean> {
  const props: Record<string, string | number | boolean> = {};

  if (!propsString.trim()) {
    return props;
  }

  // Match prop patterns:
  // - prop="value" or prop='value'
  // - prop={123} or prop={true}
  // - prop (boolean shorthand)
  const propRegex = /(\w+)(?:=(?:"([^"]*)"|'([^']*)'|\{([^}]*)\}))?/g;

  let match: RegExpExecArray | null;
  while ((match = propRegex.exec(propsString)) !== null) {
    const [, name, doubleQuoted, singleQuoted, braced] = match;
    if (!name) continue;

    if (doubleQuoted !== undefined) {
      props[name] = doubleQuoted;
    } else if (singleQuoted !== undefined) {
      props[name] = singleQuoted;
    } else if (braced !== undefined) {
      // Parse braced value (number, boolean, or string)
      const trimmed = braced.trim();
      if (trimmed === "true") {
        props[name] = true;
      } else if (trimmed === "false") {
        props[name] = false;
      } else if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
        props[name] = parseFloat(trimmed);
      } else {
        props[name] = trimmed;
      }
    } else {
      // Boolean shorthand (e.g., defaultOpen)
      props[name] = true;
    }
  }

  return props;
}

// ============================================================================
// Component Extraction
// ============================================================================

/**
 * Extract a single component from content at the given position
 */
function extractComponent(
  content: string,
  componentName: string,
  startIndex: number,
): { node: MDXParsedNode; endIndex: number } | null {
  // Find the opening tag
  const openTagRegex = new RegExp(`<${componentName}([^>]*?)(\\/?)>`, "s");
  const openMatch = openTagRegex.exec(content.slice(startIndex));

  if (!openMatch) {
    return null;
  }

  const propsString = openMatch[1] || "";
  const isSelfClosing = openMatch[2] === "/";
  const openTagEnd = startIndex + openMatch.index + openMatch[0].length;

  if (isSelfClosing) {
    return {
      node: {
        type: "component",
        component: componentName,
        props: parseProps(propsString),
        children: "",
      },
      endIndex: openTagEnd,
    };
  }

  // Find the matching closing tag
  const closeTagRegex = new RegExp(`</${componentName}>`, "s");
  const closeMatch = closeTagRegex.exec(content.slice(openTagEnd));

  if (!closeMatch) {
    // No closing tag found - treat as text
    return null;
  }

  const closeTagStart = openTagEnd + closeMatch.index;
  const closeTagEnd = closeTagStart + closeMatch[0].length;
  const children = content.slice(openTagEnd, closeTagStart).trim();

  return {
    node: {
      type: "component",
      component: componentName,
      props: parseProps(propsString),
      children,
    },
    endIndex: closeTagEnd,
  };
}

// ============================================================================
// Main Parser
// ============================================================================

/**
 * Parse MDX content into nodes (text and components)
 */
export function parseMDXContent(content: string): MDXParsedNode[] {
  if (!content || !content.trim()) {
    return [];
  }

  const nodes: MDXParsedNode[] = [];
  let currentIndex = 0;

  // Build regex to find any known component
  const componentNames = Array.from(KNOWN_COMPONENTS).join("|");
  const componentTagRegex = new RegExp(
    `<(${componentNames})(?:\\s|>|\\/)`,
    "g",
  );

  let match: RegExpExecArray | null;
  while ((match = componentTagRegex.exec(content)) !== null) {
    const componentName = match[1];
    const matchStart = match.index;

    // Add text before this component
    if (matchStart > currentIndex) {
      const textContent = content.slice(currentIndex, matchStart).trim();
      if (textContent) {
        nodes.push({
          type: "text",
          content: textContent,
        });
      }
    }

    // Extract the component
    const extracted = extractComponent(content, componentName, matchStart);
    if (extracted) {
      nodes.push(extracted.node);
      currentIndex = extracted.endIndex;
      // Reset regex to continue from new position
      componentTagRegex.lastIndex = currentIndex;
    } else {
      // Failed to extract - skip this match
      currentIndex = matchStart + match[0].length;
      componentTagRegex.lastIndex = currentIndex;
    }
  }

  // Add remaining text after last component
  if (currentIndex < content.length) {
    const textContent = content.slice(currentIndex).trim();
    if (textContent) {
      nodes.push({
        type: "text",
        content: textContent,
      });
    }
  }

  return nodes;
}

// ============================================================================
// Utilities
// ============================================================================

/**
 * Check if content contains any known MDX components
 */
export function hasMDXComponents(content: string): boolean {
  const componentNames = Array.from(KNOWN_COMPONENTS).join("|");
  const regex = new RegExp(`<(${componentNames})(?:\\s|>|\\/)`, "g");
  return regex.test(content);
}

/**
 * Get component type category
 */
export function getComponentCategory(
  componentName: string,
):
  | "callout"
  | "accordion"
  | "card"
  | "tabs"
  | "steps"
  | "code"
  | "layout"
  | "api"
  | "unknown" {
  switch (componentName) {
    case "Callout":
    case "Note":
    case "Warning":
    case "Tip":
    case "Info":
    case "Check":
      return "callout";
    case "Accordion":
    case "AccordionGroup":
      return "accordion";
    case "Card":
    case "CardGroup":
      return "card";
    case "Tabs":
    case "Tab":
      return "tabs";
    case "Steps":
    case "Step":
      return "steps";
    case "CodeGroup":
      return "code";
    case "Frame":
    case "Expandable":
    case "Icon":
      return "layout";
    case "ResponseField":
    case "ParamField":
      return "api";
    default:
      return "unknown";
  }
}
