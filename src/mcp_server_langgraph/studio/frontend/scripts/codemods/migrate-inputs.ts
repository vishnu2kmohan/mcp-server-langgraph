/**
 * Input Migration Codemod
 *
 * Transforms raw <input>, <select>, <textarea> elements to design system components.
 *
 * Usage:
 *   npx jscodeshift -t scripts/codemods/migrate-inputs.ts src/pages/SettingsPage.tsx
 *
 * Features:
 * - Adds Input/Select/Textarea import from @/components/UI
 * - Maps common className patterns to component variants
 * - Preserves all existing props
 * - Skips checkbox, radio, hidden, file inputs (special handling needed)
 */

import type {
  API,
  FileInfo,
  JSXElement,
  JSXAttribute,
  Options,
} from "jscodeshift";

// Input types to skip (need special handling)
const SKIP_INPUT_TYPES = ["checkbox", "radio", "hidden", "file", "range"];

// Variant detection patterns
const VARIANT_PATTERNS: Record<string, RegExp[]> = {
  error: [/border-error-/, /border-red-/],
  success: [/border-success-/, /border-green-/],
  // default is assumed if no pattern matches
};

// Size detection patterns
const SIZE_PATTERNS: Record<string, RegExp[]> = {
  sm: [/text-xs/, /py-1(?!\.)/, /px-2/],
  lg: [/text-lg/, /py-3/, /px-4/],
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

// Classes that should be removed (handled by component)
const REMOVABLE_CLASSES = [
  // Layout
  /w-full/,
  /block/,
  // Border
  /border(?!-\w)/,
  /border-neutral-\d+/,
  /dark:border-neutral-\d+/,
  /rounded(-md|-lg)?/,
  // Background
  /bg-white/,
  /dark:bg-neutral-\d+/,
  // Focus states
  /focus:outline-none/,
  /focus:ring-\d/,
  /focus:border-\w+/,
  /focus-visible:/,
  // Transition
  /transition(-colors)?/,
  // Placeholder
  /placeholder:/,
];

function cleanClassName(className: string): string {
  let cleaned = className;
  for (const pattern of REMOVABLE_CLASSES) {
    cleaned = cleaned.replace(pattern, "");
  }
  return cleaned.replace(/\s+/g, " ").trim();
}

export default function transformer(
  file: FileInfo,
  api: API,
  _options: Options
) {
  const j = api.jscodeshift;
  const root = j(file.source);

  // Skip test files, story files, and UI component definitions
  if (
    file.path.includes(".test.") ||
    file.path.includes(".spec.") ||
    file.path.includes(".stories.") ||
    file.path.includes("/components/UI/")
  ) {
    return null;
  }

  const elementsToTransform: Array<{
    element: "input" | "select" | "textarea";
    component: "Input" | "Select" | "Textarea";
  }> = [
    { element: "input", component: "Input" },
    { element: "select", component: "Select" },
    { element: "textarea", component: "Textarea" },
  ];

  const neededImports = new Set<string>();
  let totalTransformed = 0;

  for (const { element, component } of elementsToTransform) {
    const elements = root.findJSXElements(element);

    elements.forEach((path) => {
      const el = path.node as JSXElement;
      const openingElement = el.openingElement;

      // For input, check type and skip certain types
      if (element === "input") {
        const typeAttr = openingElement.attributes?.find(
          (attr): attr is JSXAttribute =>
            attr.type === "JSXAttribute" &&
            attr.name.name === "type" &&
            attr.value?.type === "StringLiteral"
        );

        if (typeAttr && typeAttr.value?.type === "StringLiteral") {
          if (SKIP_INPUT_TYPES.includes(typeAttr.value.value)) {
            return; // Skip this input
          }
        }
      }

      // Get className for variant/size detection
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
        }

        if (classValue) {
          detectedVariant = detectVariant(classValue);
          detectedSize = detectSize(classValue);
          cleanedClassName = cleanClassName(classValue);
        }
      }

      // Transform element → Component
      openingElement.name = j.jsxIdentifier(component);
      if (el.closingElement) {
        el.closingElement.name = j.jsxIdentifier(component);
      }

      // Build new attributes
      const newAttrs: JSXAttribute[] = [];

      if (detectedVariant) {
        newAttrs.push(
          j.jsxAttribute(
            j.jsxIdentifier("variant"),
            j.stringLiteral(detectedVariant)
          )
        );
      }

      if (detectedSize) {
        newAttrs.push(
          j.jsxAttribute(j.jsxIdentifier("size"), j.stringLiteral(detectedSize))
        );
      }

      // Filter existing attributes
      const existingAttrs = (openingElement.attributes || []).filter(
        (attr): attr is JSXAttribute => {
          if (attr.type !== "JSXAttribute") return true;
          if (attr.name.name === "className" && cleanedClassName !== null) {
            return false;
          }
          // Remove type="text" for input (it's the default)
          if (
            element === "input" &&
            attr.name.name === "type" &&
            attr.value?.type === "StringLiteral" &&
            attr.value.value === "text"
          ) {
            return false;
          }
          return true;
        }
      );

      // Add cleaned className if non-empty
      if (cleanedClassName && cleanedClassName.length > 0) {
        newAttrs.push(
          j.jsxAttribute(
            j.jsxIdentifier("className"),
            j.stringLiteral(cleanedClassName)
          )
        );
      }

      openingElement.attributes = [...newAttrs, ...existingAttrs];
      neededImports.add(component);
      totalTransformed++;
    });
  }

  if (totalTransformed === 0) {
    return null;
  }

  // Helper: check if import is from UI barrel export
  const isUIBarrelImport = (source: string): boolean =>
    source === "@/components/UI" ||
    source.endsWith("/components/UI") ||
    source.endsWith("/components/UI/index");

  // Add imports
  const uiImport = root.find(j.ImportDeclaration).filter((path) => {
    const source = path.node.source.value;
    return typeof source === "string" && isUIBarrelImport(source);
  });

  // Find which components need to be imported
  const existingImports = new Set<string>();
  uiImport.forEach((path) => {
    (path.node.specifiers || []).forEach((s) => {
      if (s.type === "ImportSpecifier") {
        existingImports.add(s.imported.name);
      }
    });
  });

  const newImportsNeeded = [...neededImports].filter(
    (i) => !existingImports.has(i)
  );

  if (newImportsNeeded.length > 0) {
    if (uiImport.length > 0) {
      // Add to existing import
      uiImport.forEach((path) => {
        const specifiers = path.node.specifiers || [];
        newImportsNeeded.forEach((name) => {
          specifiers.push(j.importSpecifier(j.identifier(name)));
        });
        path.node.specifiers = specifiers;
      });
    } else {
      // Create new import
      const newImport = j.importDeclaration(
        newImportsNeeded.map((name) => j.importSpecifier(j.identifier(name))),
        j.stringLiteral("@/components/UI")
      );

      const allImports = root.find(j.ImportDeclaration);
      if (allImports.length > 0) {
        allImports.at(-1).insertAfter(newImport);
      } else {
        root.get().node.program.body.unshift(newImport);
      }
    }
  }

  console.log(`Transformed ${totalTransformed} form elements in ${file.path}`);
  return root.toSource({ quote: "double" });
}
