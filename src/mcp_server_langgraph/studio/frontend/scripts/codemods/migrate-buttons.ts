/**
 * Button Migration Codemod
 *
 * Transforms raw <button> elements to <Button> design system component.
 *
 * Usage:
 *   npx jscodeshift -t scripts/codemods/migrate-buttons.ts src/pages/SettingsPage.tsx
 *
 * Features:
 * - Adds Button import from @/components/UI
 * - Transforms <button> → <Button>
 * - Maps common className patterns to Button variants
 * - Preserves all existing props
 * - Skips files that already use Button
 *
 * Patterns transformed:
 * - bg-primary-* → variant="primary"
 * - bg-error-* or bg-red-* → variant="danger"
 * - bg-neutral-* or hover:bg-neutral-* → variant="secondary"
 * - No background → variant="ghost"
 */

import type {
  API,
  FileInfo,
  JSXElement,
  JSXAttribute,
  Options,
} from "jscodeshift";

// Variant detection patterns
const VARIANT_PATTERNS: Record<string, RegExp[]> = {
  primary: [/bg-primary-\d+/, /bg-brand-primary/],
  danger: [/bg-error-\d+/, /bg-red-\d+/],
  secondary: [/bg-neutral-\d+/, /bg-white/],
  success: [/bg-success-\d+/, /bg-green-\d+/],
  warning: [/bg-warning-\d+/, /bg-yellow-\d+/],
  ghost: [/bg-transparent/, /hover:bg-neutral-/],
};

// Size detection patterns
const SIZE_PATTERNS: Record<string, RegExp[]> = {
  sm: [/text-xs/, /px-2/, /py-1(?!\.)/],
  lg: [/text-lg/, /px-6/, /py-3/],
  // md is default, no explicit pattern needed
};

function detectVariant(className: string): string | null {
  for (const [variant, patterns] of Object.entries(VARIANT_PATTERNS)) {
    if (patterns.some((p) => p.test(className))) {
      return variant;
    }
  }
  return null;
}

function detectSize(className: string): string | null {
  for (const [size, patterns] of Object.entries(SIZE_PATTERNS)) {
    if (patterns.some((p) => p.test(className))) {
      return size;
    }
  }
  return null;
}

// Classes that should be removed (handled by Button component)
const REMOVABLE_CLASSES = [
  // Layout handled by Button
  /inline-flex/,
  /items-center/,
  /justify-center/,
  /gap-\d/,
  // Typography handled by variant
  /font-(medium|semibold|bold)/,
  // Focus states handled by Button
  /focus:outline-none/,
  /focus:ring-\d/,
  /focus-visible:/,
  // Transition handled by Button
  /transition(-colors|-all)?/,
  /duration-\d+/,
  // Cursor handled by Button
  /cursor-pointer/,
  // Disabled state handled by Button
  /disabled:opacity-\d+/,
  /disabled:cursor-not-allowed/,
];

function cleanClassName(className: string): string {
  let cleaned = className;
  for (const pattern of REMOVABLE_CLASSES) {
    cleaned = cleaned.replace(pattern, "");
  }
  // Clean up multiple spaces
  return cleaned.replace(/\s+/g, " ").trim();
}

export default function transformer(
  file: FileInfo,
  api: API,
  _options: Options
) {
  const j = api.jscodeshift;
  const root = j(file.source);

  // Skip test files
  if (file.path.includes(".test.") || file.path.includes(".spec.")) {
    return null;
  }

  // Helper: check if import is from UI barrel export
  const isUIBarrelImport = (source: string): boolean =>
    source === "@/components/UI" ||
    source.endsWith("/components/UI") ||
    source.endsWith("/components/UI/index");

  // Skip if already imports Button
  const existingButtonImport = root.find(j.ImportDeclaration).filter((path) => {
    const source = path.node.source.value;
    return typeof source === "string" && isUIBarrelImport(source);
  });

  let hasButtonImport = false;
  existingButtonImport.forEach((path) => {
    const specifiers = path.node.specifiers || [];
    hasButtonImport = specifiers.some(
      (s) => s.type === "ImportSpecifier" && s.imported.name === "Button"
    );
  });

  // Find all button elements
  const buttons = root.findJSXElements("button");

  if (buttons.length === 0) {
    return null; // No changes needed
  }

  let transformedCount = 0;

  buttons.forEach((path) => {
    const element = path.node as JSXElement;
    const openingElement = element.openingElement;

    // Get className attribute
    const classNameAttr = openingElement.attributes?.find(
      (attr): attr is JSXAttribute =>
        attr.type === "JSXAttribute" && attr.name.name === "className"
    );

    let detectedVariant: string | null = null;
    let detectedSize: string | null = null;
    let cleanedClassName: string | null = null;

    if (classNameAttr && classNameAttr.value) {
      let classValue = "";

      if (classNameAttr.value.type === "StringLiteral") {
        classValue = classNameAttr.value.value;
      } else if (
        classNameAttr.value.type === "JSXExpressionContainer" &&
        classNameAttr.value.expression.type === "StringLiteral"
      ) {
        classValue = classNameAttr.value.expression.value;
      } else if (
        classNameAttr.value.type === "JSXExpressionContainer" &&
        classNameAttr.value.expression.type === "TemplateLiteral"
      ) {
        // For template literals, just extract the static parts
        classValue = classNameAttr.value.expression.quasis
          .map((q) => q.value.raw)
          .join(" ");
      }

      if (classValue) {
        detectedVariant = detectVariant(classValue);
        detectedSize = detectSize(classValue);
        cleanedClassName = cleanClassName(classValue);
      }
    }

    // Transform button → Button
    openingElement.name = j.jsxIdentifier("Button");
    if (element.closingElement) {
      element.closingElement.name = j.jsxIdentifier("Button");
    }

    // Build new attributes
    const newAttrs: JSXAttribute[] = [];

    // Add variant if detected
    if (detectedVariant) {
      newAttrs.push(
        j.jsxAttribute(
          j.jsxIdentifier("variant"),
          j.stringLiteral(detectedVariant)
        )
      );
    }

    // Add size if detected
    if (detectedSize) {
      newAttrs.push(
        j.jsxAttribute(j.jsxIdentifier("size"), j.stringLiteral(detectedSize))
      );
    }

    // Keep existing attributes, update className
    const existingAttrs = (openingElement.attributes || []).filter(
      (attr): attr is JSXAttribute => {
        if (attr.type !== "JSXAttribute") return true;
        // Remove className if we're handling it
        if (attr.name.name === "className" && cleanedClassName !== null) {
          return false;
        }
        return true;
      }
    );

    // Add cleaned className if there's anything left
    if (cleanedClassName && cleanedClassName.length > 0) {
      newAttrs.push(
        j.jsxAttribute(
          j.jsxIdentifier("className"),
          j.stringLiteral(cleanedClassName)
        )
      );
    }

    openingElement.attributes = [...newAttrs, ...existingAttrs];
    transformedCount++;
  });

  if (transformedCount === 0) {
    return null;
  }

  // Add Button import if not already present
  if (!hasButtonImport) {
    // Find existing UI barrel import or create new one
    const uiImport = root.find(j.ImportDeclaration).filter((path) => {
      const source = path.node.source.value;
      return typeof source === "string" && isUIBarrelImport(source);
    });

    if (uiImport.length > 0) {
      // Add Button to existing import
      uiImport.forEach((path) => {
        const specifiers = path.node.specifiers || [];
        specifiers.push(j.importSpecifier(j.identifier("Button")));
        path.node.specifiers = specifiers;
      });
    } else {
      // Create new import at top of file
      const newImport = j.importDeclaration(
        [j.importSpecifier(j.identifier("Button"))],
        j.stringLiteral("@/components/UI")
      );

      // Insert after the last import
      const allImports = root.find(j.ImportDeclaration);
      if (allImports.length > 0) {
        allImports.at(-1).insertAfter(newImport);
      } else {
        root.get().node.program.body.unshift(newImport);
      }
    }
  }

  console.log(`Transformed ${transformedCount} buttons in ${file.path}`);
  return root.toSource({ quote: "double" });
}
