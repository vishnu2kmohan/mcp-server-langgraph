/**
 * Button Semantics Codemod
 *
 * Adds semantic variant props to Button components based on:
 * 1. Button text content (Delete -> danger, Cancel -> secondary)
 * 2. Icon type (Trash -> danger, X -> secondary)
 * 3. Default fallback (primary for action buttons, ghost for icon-only)
 *
 * Usage:
 *   npx jscodeshift -t scripts/codemods/fix-button-semantics.ts src/pages/
 *
 * Per STYLE.md:
 * - danger: Delete, Remove, Clear, Destroy, Discard buttons (or Trash icon)
 * - secondary: Cancel, Close, Back, Dismiss, No buttons (or X icon)
 * - primary: Submit, Save, Create, Add, Confirm, Continue, Yes buttons (or Plus icon)
 * - ghost: Icon-only buttons without semantic meaning
 */

import type {
  API,
  FileInfo,
  JSXElement,
  JSXAttribute,
  JSXText,
  Options,
  Collection,
  JSXOpeningElement,
} from "jscodeshift";

// =============================================================================
// Semantic Detection Patterns
// =============================================================================

// Danger variant: destructive actions
// Use word boundary \b to match within phrases like "Delete item"
const DANGER_TEXT_PATTERNS = [
  /\bdelete\b/i,
  /\bremove\b/i,
  /\bclear\b/i,
  /\bdestroy\b/i,
  /\bdiscard\b/i,
];

const DANGER_ICON_PATTERNS = [/^Trash/i, /^Delete/i];

// Secondary variant: cancel/dismiss actions
const SECONDARY_TEXT_PATTERNS = [
  /\bcancel\b/i,
  /\bclose\b/i,
  /\bback\b/i,
  /\bdismiss\b/i,
  /^no$/i, // Exact match for "No" to avoid false positives like "Notes"
];

const SECONDARY_ICON_PATTERNS = [/^X$/i, /^Close/i, /^XCircle/i, /^XMark/i];

// Primary variant: positive/confirm actions
const PRIMARY_TEXT_PATTERNS = [
  /\bsubmit\b/i,
  /\bsave\b/i,
  /\bcreate\b/i,
  /\badd\b/i,
  /\bconfirm\b/i,
  /\bcontinue\b/i,
  /\byes\b/i,
  /\bok\b/i,
  /\bdone\b/i,
  /\bapply\b/i,
  /\bupdate\b/i,
  /\bsend\b/i,
  /\bupload\b/i,
  /\bimport\b/i,
  /\bexport\b/i,
  /\bstart\b/i,
  /\benable\b/i,
  /\bconnect\b/i,
  /\brun\b/i,
  /\bexecute\b/i,
  /\bprocess\b/i,
];

const PRIMARY_ICON_PATTERNS = [/^Plus/i, /^Add/i, /^Check/i, /^Save/i];

// Ghost variant: navigation/utility icons (non-semantic icon-only buttons)
const GHOST_ICON_PATTERNS = [
  /^Settings/i,
  /^Cog/i,
  /^Gear/i,
  /^Chevron/i,
  /^Arrow/i,
  /^Menu/i,
  /^MoreVertical/i,
  /^MoreHorizontal/i,
  /^Dots/i,
  /^Ellipsis/i,
  /^Grip/i,
  /^Drag/i,
  /^Eye/i,
  /^Copy/i,
  /^Edit/i,
  /^Pencil/i,
  /^Search/i,
  /^Filter/i,
  /^Sort/i,
  /^Refresh/i,
  /^Reload/i,
  /^Sync/i,
  /^Info/i,
  /^Help/i,
  /^Question/i,
  /^Bell/i,
  /^Notification/i,
  /^User/i,
  /^Avatar/i,
  /^Calendar/i,
  /^Clock/i,
  /^Link/i,
  /^External/i,
  /^Download/i,
  /^Share/i,
  /^Bookmark/i,
  /^Star/i,
  /^Heart/i,
  /^Flag/i,
  /^Tag/i,
  /^Folder/i,
  /^File/i,
  /^Document/i,
  /^Image/i,
  /^Code/i,
  /^Terminal/i,
  /^Play/i,
  /^Pause/i,
  /^Stop/i,
  /^Volume/i,
  /^Minimize/i,
  /^Maximize/i,
  /^Expand/i,
  /^Collapse/i,
  /^Fullscreen/i,
  /^List/i,
  /^Grid/i,
  /^Table/i,
  /^Layout/i,
  /^Sidebar/i,
  /^Panel/i,
  /^Home/i,
  /^Mail/i,
  /^Phone/i,
  /^Message/i,
  /^Chat/i,
  /^Comment/i,
  /^Lock/i,
  /^Unlock/i,
  /^Key/i,
  /^Shield/i,
  /^Alert/i,
  /^Warning/i,
  /^Loader/i,
  /^Spinner/i,
  /^Zap/i,
  /^Lightning/i,
  /^Sparkle/i,
  /^Wand/i,
];

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Recursively extracts string values from AST nodes (handles ternary, template literals, etc.)
 */
function extractStringsFromExpression(expr: any): string[] {
  const strings: string[] = [];

  if (!expr) return strings;

  if (expr.type === "StringLiteral" || (expr.type === "Literal" && typeof expr.value === "string")) {
    strings.push(String(expr.value).trim());
  } else if (expr.type === "ConditionalExpression") {
    // Handle ternary: condition ? 'A' : 'B' - extract both branches
    strings.push(...extractStringsFromExpression(expr.consequent));
    strings.push(...extractStringsFromExpression(expr.alternate));
  } else if (expr.type === "TemplateLiteral") {
    // Handle template literals: `Delete ${item}`
    for (const quasi of expr.quasis || []) {
      if (quasi.value?.raw) {
        strings.push(quasi.value.raw.trim());
      }
    }
  } else if (expr.type === "BinaryExpression" && expr.operator === "+") {
    // Handle string concatenation: 'Delete' + ' item'
    strings.push(...extractStringsFromExpression(expr.left));
    strings.push(...extractStringsFromExpression(expr.right));
  }

  return strings;
}

/**
 * Extracts text content from JSX children
 */
function extractTextContent(
  element: JSXElement,
  j: typeof import("jscodeshift")
): string {
  const texts: string[] = [];

  function collectText(children: JSXElement["children"]) {
    if (!children) return;

    for (const child of children) {
      if (child.type === "JSXText") {
        texts.push((child as JSXText).value.trim());
      } else if (child.type === "Literal" && typeof child.value === "string") {
        texts.push(child.value.trim());
      } else if (child.type === "StringLiteral") {
        texts.push(child.value.trim());
      } else if (child.type === "JSXExpressionContainer") {
        // Extract strings from the expression (handles ternary, template literals, etc.)
        const expr = child.expression;
        texts.push(...extractStringsFromExpression(expr));
      }
    }
  }

  collectText(element.children);
  return texts.join(" ").trim();
}

/**
 * Extracts icon component names from JSX children
 */
function extractIconNames(
  element: JSXElement,
  j: typeof import("jscodeshift")
): string[] {
  const icons: string[] = [];

  function collectIcons(children: JSXElement["children"]) {
    if (!children) return;

    for (const child of children) {
      if (child.type === "JSXElement") {
        const openingElement = (child as JSXElement).openingElement;
        if (openingElement.name.type === "JSXIdentifier") {
          const name = openingElement.name.name;
          // Icon components typically start with uppercase and end with Icon or are PascalCase
          if (/^[A-Z]/.test(name)) {
            icons.push(name);
          }
        }
        // Recurse into children
        collectIcons((child as JSXElement).children);
      }
    }
  }

  collectIcons(element.children);
  return icons;
}

/**
 * Extracts aria-label value from JSX attributes
 */
function extractAriaLabel(openingElement: JSXOpeningElement): string | null {
  for (const attr of openingElement.attributes || []) {
    if (attr.type === "JSXAttribute" && attr.name.name === "aria-label") {
      if (attr.value?.type === "StringLiteral") {
        return attr.value.value;
      } else if (
        attr.value?.type === "Literal" &&
        typeof attr.value.value === "string"
      ) {
        return attr.value.value;
      }
    }
  }
  return null;
}

/**
 * Checks if button has size="icon" prop
 */
function hasIconSize(openingElement: JSXOpeningElement): boolean {
  for (const attr of openingElement.attributes || []) {
    if (attr.type === "JSXAttribute" && attr.name.name === "size") {
      if (attr.value?.type === "StringLiteral" && attr.value.value === "icon") {
        return true;
      } else if (
        attr.value?.type === "Literal" &&
        attr.value.value === "icon"
      ) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Checks if button already has variant prop
 */
function hasVariantProp(openingElement: JSXOpeningElement): boolean {
  for (const attr of openingElement.attributes || []) {
    if (attr.type === "JSXAttribute" && attr.name.name === "variant") {
      return true;
    } else if (attr.type === "JSXSpreadAttribute") {
      // If there's a spread, we can't be sure, so we skip to be safe
      return true;
    }
  }
  return false;
}

/**
 * Detects the appropriate variant based on button content
 */
function detectVariant(
  element: JSXElement,
  j: typeof import("jscodeshift")
): string | null {
  const openingElement = element.openingElement;

  // Get text content, icon names, and aria-label
  const textContent = extractTextContent(element, j);
  const iconNames = extractIconNames(element, j);
  const ariaLabel = extractAriaLabel(openingElement);
  const isIconButton = hasIconSize(openingElement);

  // Combined text for matching (text + aria-label)
  const allText = [textContent, ariaLabel].filter(Boolean).join(" ");

  // Check danger patterns first (most specific)
  for (const pattern of DANGER_TEXT_PATTERNS) {
    if (pattern.test(allText)) {
      return "danger";
    }
  }
  for (const iconName of iconNames) {
    for (const pattern of DANGER_ICON_PATTERNS) {
      if (pattern.test(iconName)) {
        return "danger";
      }
    }
  }

  // Check secondary patterns (cancel/dismiss)
  for (const pattern of SECONDARY_TEXT_PATTERNS) {
    if (pattern.test(allText)) {
      return "secondary";
    }
  }
  for (const iconName of iconNames) {
    for (const pattern of SECONDARY_ICON_PATTERNS) {
      if (pattern.test(iconName)) {
        return "secondary";
      }
    }
  }

  // Check primary patterns (action/confirm)
  for (const pattern of PRIMARY_TEXT_PATTERNS) {
    if (pattern.test(allText)) {
      return "primary";
    }
  }
  for (const iconName of iconNames) {
    for (const pattern of PRIMARY_ICON_PATTERNS) {
      if (pattern.test(iconName)) {
        return "primary";
      }
    }
  }

  // Check ghost patterns (utility icons)
  for (const iconName of iconNames) {
    for (const pattern of GHOST_ICON_PATTERNS) {
      if (pattern.test(iconName)) {
        return "ghost";
      }
    }
  }

  // Icon-only buttons without recognized icon → ghost
  if (isIconButton && !textContent) {
    return "ghost";
  }

  // Default fallback: primary for action buttons with text
  if (textContent) {
    return "primary";
  }

  // Empty icon button → ghost
  if (isIconButton) {
    return "ghost";
  }

  return "primary"; // Default fallback
}

// =============================================================================
// Transform
// =============================================================================

export default function transformer(
  file: FileInfo,
  api: API,
  _options: Options
): string | null {
  const j = api.jscodeshift;
  const root = j(file.source);

  // Skip test, story, and UI component definition files
  if (
    file.path.includes(".test.") ||
    file.path.includes(".spec.") ||
    file.path.includes(".stories.") ||
    file.path.includes("/components/UI/")
  ) {
    return null;
  }

  // Find all Button elements
  const buttons = root.findJSXElements("Button");

  if (buttons.length === 0) {
    return null;
  }

  let transformedCount = 0;

  buttons.forEach((path) => {
    const element = path.node as JSXElement;
    const openingElement = element.openingElement;

    // Skip if already has variant prop
    if (hasVariantProp(openingElement)) {
      return;
    }

    // Detect appropriate variant
    const variant = detectVariant(element, j);

    if (!variant) {
      return;
    }

    // Add variant prop at the beginning of attributes
    const variantAttr = j.jsxAttribute(
      j.jsxIdentifier("variant"),
      j.stringLiteral(variant)
    );

    openingElement.attributes = [variantAttr, ...(openingElement.attributes || [])];
    transformedCount++;
  });

  if (transformedCount === 0) {
    return null;
  }

  console.log(`Added variant to ${transformedCount} buttons in ${file.path}`);
  return root.toSource({ quote: "double" });
}
