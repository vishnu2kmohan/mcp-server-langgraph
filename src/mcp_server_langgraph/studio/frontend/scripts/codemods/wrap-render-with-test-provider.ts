/**
 * Wrap render() calls with TestProvider
 *
 * Transforms bare render(<Component />) calls to render(<TestProvider><Component /></TestProvider>)
 * to fix missing Redux Provider errors in tests.
 *
 * Usage:
 *   npx jscodeshift --parser=tsx --extensions=tsx -t scripts/codemods/wrap-render-with-test-provider.ts src/
 *
 * Features:
 * - Wraps bare render() calls with TestProvider
 * - Replaces MemoryRouter wrappers with TestProvider (preserving initialEntries)
 * - Skips files with custom renderWith* wrapper functions
 * - Skips files with vi.mock for Redux store/hooks/slices
 * - Skips render calls already wrapped with TestProvider or Provider
 * - Skips render calls with dynamic/non-JSX arguments
 * - Adds TestProvider import from @/test-utils
 * - Removes unused MemoryRouter imports
 */

import type {
  API,
  FileInfo,
  JSXElement,
  JSXFragment,
  Options,
  Collection,
  ASTPath,
  CallExpression,
  ImportDeclaration,
  JSXIdentifier,
} from "jscodeshift";

// =============================================================================
// Skip Detection Patterns
// =============================================================================

// Pattern for custom render wrapper functions
const CUSTOM_RENDER_PATTERNS = [
  /^renderWith/,
  /^customRender$/,
];

// Pattern for vi.mock paths that indicate Redux mocking
const REDUX_MOCK_PATTERNS = [
  /store/i,
  /redux/i,
  /slice/i,
];

// Components that are considered "already wrapped" providers
const PROVIDER_NAMES = new Set([
  "TestProvider",
  "Provider",
  "ReduxProvider",
  "RouterProvider", // Has its own router, don't wrap with TestProvider
]);

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Check if file has custom render wrapper functions
 */
function hasCustomRenderWrapper(root: Collection, j: typeof import("jscodeshift")): boolean {
  // Check function declarations: function renderWithStore() {}
  const funcDecls = root.find(j.FunctionDeclaration).filter((path) => {
    const name = path.node.id?.name ?? "";
    return CUSTOM_RENDER_PATTERNS.some((p) => p.test(name));
  });

  if (funcDecls.length > 0) {
    return true;
  }

  // Check variable declarations: const renderWithStore = () => {}
  const varDecls = root.find(j.VariableDeclarator).filter((path) => {
    if (path.node.id.type === "Identifier") {
      const name = path.node.id.name;
      return CUSTOM_RENDER_PATTERNS.some((p) => p.test(name));
    }
    return false;
  });

  return varDecls.length > 0;
}

/**
 * Check if file uses its own router (RouterProvider, createMemoryRouter, etc.)
 * These files should not be wrapped with TestProvider as it would create nested routers
 */
function hasOwnRouter(root: Collection, j: typeof import("jscodeshift")): boolean {
  // Check for RouterProvider JSX element anywhere in the file
  const routerProviderElements = root.findJSXElements("RouterProvider");
  if (routerProviderElements.length > 0) {
    return true;
  }

  // Check for createMemoryRouter or createBrowserRouter calls
  const routerCreators = root.find(j.CallExpression).filter((path) => {
    if (path.node.callee.type === "Identifier") {
      const name = path.node.callee.name;
      return name === "createMemoryRouter" || name === "createBrowserRouter" || name === "createHashRouter";
    }
    return false;
  });

  return routerCreators.length > 0;
}

/**
 * Check if file has vi.mock for Redux-related paths
 */
function hasReduxMock(root: Collection, j: typeof import("jscodeshift")): boolean {
  const viMockCalls = root.find(j.CallExpression, {
    callee: {
      type: "MemberExpression",
      object: { type: "Identifier", name: "vi" },
      property: { type: "Identifier", name: "mock" },
    },
  });

  return viMockCalls.some((path) => {
    const args = path.node.arguments;
    if (args.length > 0 && args[0].type === "StringLiteral") {
      const mockPath = args[0].value;
      return REDUX_MOCK_PATTERNS.some((p) => p.test(mockPath));
    }
    return false;
  });
}

/**
 * Check if a JSX element is wrapped with a provider
 */
function isWrappedWithProvider(element: JSXElement | JSXFragment): boolean {
  if (element.type === "JSXFragment") {
    return false;
  }

  const openingElement = element.openingElement;
  if (openingElement.name.type === "JSXIdentifier") {
    return PROVIDER_NAMES.has(openingElement.name.name);
  }
  return false;
}

/**
 * Check if a JSX element is a MemoryRouter
 */
function isMemoryRouter(element: JSXElement): boolean {
  const openingElement = element.openingElement;
  if (openingElement.name.type === "JSXIdentifier") {
    return openingElement.name.name === "MemoryRouter";
  }
  return false;
}

/**
 * Get initialEntries prop from MemoryRouter if present
 */
function getInitialEntriesProp(
  element: JSXElement,
  j: typeof import("jscodeshift")
): any | null {
  const openingElement = element.openingElement;
  const attrs = openingElement.attributes ?? [];

  for (const attr of attrs) {
    if (
      attr.type === "JSXAttribute" &&
      attr.name.type === "JSXIdentifier" &&
      attr.name.name === "initialEntries"
    ) {
      return attr;
    }
  }
  return null;
}

/**
 * Check if TestProvider is already imported
 */
function hasTestProviderImport(root: Collection, j: typeof import("jscodeshift")): boolean {
  return root.find(j.ImportDeclaration).some((path) => {
    const specifiers = path.node.specifiers ?? [];
    return specifiers.some(
      (s) => s.type === "ImportSpecifier" && s.imported.name === "TestProvider"
    );
  });
}

/**
 * Add TestProvider import to file
 */
function addTestProviderImport(root: Collection, j: typeof import("jscodeshift")): void {
  // Check if already imported
  if (hasTestProviderImport(root, j)) {
    return;
  }

  // Check if there's an existing @/test-utils import to extend
  const testUtilsImport = root.find(j.ImportDeclaration).filter((path) => {
    const source = path.node.source.value;
    return source === "@/test-utils";
  });

  if (testUtilsImport.length > 0) {
    // Add TestProvider to existing import
    testUtilsImport.forEach((path) => {
      const specifiers = path.node.specifiers ?? [];
      specifiers.push(j.importSpecifier(j.identifier("TestProvider")));
      path.node.specifiers = specifiers;
    });
  } else {
    // Create new import
    const newImport = j.importDeclaration(
      [j.importSpecifier(j.identifier("TestProvider"))],
      j.stringLiteral("@/test-utils")
    );

    // Insert after last import
    const allImports = root.find(j.ImportDeclaration);
    if (allImports.length > 0) {
      allImports.at(-1).insertAfter(newImport);
    } else {
      root.get().node.program.body.unshift(newImport);
    }
  }
}

/**
 * Remove MemoryRouter import if no longer used
 */
function removeUnusedMemoryRouterImport(root: Collection, j: typeof import("jscodeshift")): void {
  // Check if MemoryRouter is still used anywhere
  const memoryRouterUsages = root.findJSXElements("MemoryRouter");
  if (memoryRouterUsages.length > 0) {
    return; // Still used, don't remove
  }

  // Find and clean up the import
  root.find(j.ImportDeclaration).forEach((path) => {
    const source = path.node.source.value;
    if (source === "react-router" || source === "react-router-dom") {
      const specifiers = path.node.specifiers ?? [];
      const newSpecifiers = specifiers.filter((s) => {
        if (s.type === "ImportSpecifier") {
          return s.imported.name !== "MemoryRouter";
        }
        return true;
      });

      if (newSpecifiers.length === 0) {
        // Remove entire import if empty
        j(path).remove();
      } else if (newSpecifiers.length !== specifiers.length) {
        // Update specifiers
        path.node.specifiers = newSpecifiers;
      }
    }
  });
}

/**
 * Wrap a JSX element with TestProvider
 */
function wrapWithTestProvider(
  element: JSXElement | JSXFragment,
  j: typeof import("jscodeshift"),
  initialEntriesProp: any | null = null
): JSXElement {
  const attrs = initialEntriesProp ? [initialEntriesProp] : [];

  return j.jsxElement(
    j.jsxOpeningElement(j.jsxIdentifier("TestProvider"), attrs),
    j.jsxClosingElement(j.jsxIdentifier("TestProvider")),
    [element]
  );
}

// =============================================================================
// Main Transform
// =============================================================================

export default function transformer(
  file: FileInfo,
  api: API,
  _options: Options
): string | null {
  const j = api.jscodeshift;
  const root = j(file.source);

  // Only process test files
  if (!file.path.includes(".test.") && !file.path.includes(".spec.")) {
    return null;
  }

  // Skip files with custom render wrappers
  if (hasCustomRenderWrapper(root, j)) {
    console.error(`SKIP: custom wrapper function in ${file.path}`);
    return null;
  }

  // Skip files with Redux mocks
  if (hasReduxMock(root, j)) {
    console.error(`SKIP: Redux mock detected in ${file.path}`);
    return null;
  }

  // Skip files that have their own router (would create nested routers)
  if (hasOwnRouter(root, j)) {
    console.error(`SKIP: file has own router in ${file.path}`);
    return null;
  }

  let transformedCount = 0;

  // Find all render() call expressions
  const renderCalls = root.find(j.CallExpression, {
    callee: {
      type: "Identifier",
      name: "render",
    },
  });

  renderCalls.forEach((path) => {
    const args = path.node.arguments;

    // Skip if no arguments
    if (args.length === 0) {
      return;
    }

    const firstArg = args[0];

    // Skip if render call has a wrapper option (second arg is object with wrapper property)
    // These wrappers often include their own router/provider setup
    if (args.length > 1 && args[1]?.type === "ObjectExpression") {
      const options = args[1];
      const hasWrapper = options.properties?.some((prop: any) => {
        if (prop.type === "Property" || prop.type === "ObjectProperty") {
          const key = prop.key;
          return (key.type === "Identifier" && key.name === "wrapper") ||
                 (key.type === "StringLiteral" && key.value === "wrapper");
        }
        return false;
      });
      if (hasWrapper) {
        const loc = path.node.loc?.start;
        console.error(`SKIP: render with wrapper option in ${file.path}:${loc?.line ?? "?"}`);
        return;
      }
    }

    // Skip if argument is not JSX (e.g., variable or function call)
    if (firstArg.type !== "JSXElement" && firstArg.type !== "JSXFragment") {
      // Log dynamic render for manual review
      const loc = path.node.loc?.start;
      console.error(`SKIP: dynamic render in ${file.path}:${loc?.line ?? "?"}`);
      return;
    }

    // Handle JSXFragment - wrap it
    if (firstArg.type === "JSXFragment") {
      args[0] = wrapWithTestProvider(firstArg, j);
      transformedCount++;
      return;
    }

    // Handle JSXElement
    const jsxElement = firstArg as JSXElement;

    // Skip if already wrapped with a provider
    if (isWrappedWithProvider(jsxElement)) {
      return;
    }

    // Handle MemoryRouter replacement
    if (isMemoryRouter(jsxElement)) {
      const initialEntriesProp = getInitialEntriesProp(jsxElement, j);
      const children = jsxElement.children ?? [];

      // Get the actual content (first JSX child)
      const jsxChildren = children.filter(
        (c) => c.type === "JSXElement" || c.type === "JSXFragment"
      );

      if (jsxChildren.length === 1) {
        // Replace MemoryRouter with TestProvider wrapping the child
        args[0] = wrapWithTestProvider(jsxChildren[0] as JSXElement | JSXFragment, j, initialEntriesProp);
      } else if (jsxChildren.length > 1) {
        // Multiple children - wrap the whole MemoryRouter content in a fragment
        const fragment = j.jsxFragment(
          j.jsxOpeningFragment(),
          j.jsxClosingFragment(),
          jsxChildren
        );
        args[0] = wrapWithTestProvider(fragment, j, initialEntriesProp);
      } else {
        // No JSX children, just wrap MemoryRouter's children directly
        args[0] = wrapWithTestProvider(jsxElement, j, initialEntriesProp);
      }
      transformedCount++;
      return;
    }

    // Wrap bare JSX with TestProvider
    args[0] = wrapWithTestProvider(jsxElement, j);
    transformedCount++;
  });

  // If no transformations, return null (no changes)
  if (transformedCount === 0) {
    return null;
  }

  // Add TestProvider import
  addTestProviderImport(root, j);

  // Remove unused MemoryRouter import
  removeUnusedMemoryRouterImport(root, j);

  console.log(`Transformed ${transformedCount} render calls in ${file.path}`);
  return root.toSource({ quote: "double" });
}
