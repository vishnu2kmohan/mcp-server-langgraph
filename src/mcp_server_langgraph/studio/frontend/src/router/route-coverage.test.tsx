/**
 * Route Coverage Tests - TDD RED PHASE
 *
 * These tests verify that all navigation paths defined in UI components
 * actually exist as routes in the router configuration.
 *
 * This test file catches issues where:
 * - ActivityBar points to non-existent routes
 * - Command palette navigates to missing routes
 * - Help links point to undefined routes
 *
 * ISSUE FOUND: This test was written AFTER discovering that:
 * - /studio/agents does not exist (ActivityBar line 72)
 * - /studio/traces does not exist (ActivityBar line 90)
 *
 * RED PHASE: These tests SHOULD FAIL until routes are added.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Import the actual navigation items from ActivityBar
import { NAV_ITEMS, BOTTOM_ITEMS } from "../layout/ActivityBar";

// Import the actual router to extract all defined routes
import { router } from "./index";

// =============================================================================
// Helper: Extract all route paths from React Router configuration
// =============================================================================

interface RouteObject {
  path?: string;
  children?: RouteObject[];
  index?: boolean;
}

/**
 * Recursively extract all route paths from router configuration
 */
function extractRoutePaths(routes: RouteObject[], prefix = ""): string[] {
  const paths: string[] = [];

  for (const route of routes) {
    const currentPath = route.path
      ? route.path.startsWith("/")
        ? route.path
        : `${prefix}/${route.path}`.replace("//", "/")
      : prefix;

    // Add the path if it's defined (not just a layout wrapper)
    if (route.path && !route.path.includes(":")) {
      paths.push(currentPath);
    }

    // Also add index routes
    if (route.index && prefix) {
      paths.push(prefix);
    }

    // Recurse into children
    if (route.children) {
      paths.push(...extractRoutePaths(route.children, currentPath));
    }
  }

  return [...new Set(paths)]; // Remove duplicates
}

// =============================================================================
// Tests
// =============================================================================

describe("Route Coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("ActivityBar Navigation Items", () => {
    // Get all defined routes from the router
    // @ts-expect-error - router.routes is internal but accessible
    const definedRoutes = extractRoutePaths(router.routes);

    it("should have NAV_ITEMS defined", () => {
      expect(NAV_ITEMS).toBeDefined();
      expect(NAV_ITEMS.length).toBeGreaterThan(0);
    });

    it("should have BOTTOM_ITEMS defined", () => {
      expect(BOTTOM_ITEMS).toBeDefined();
      expect(BOTTOM_ITEMS.length).toBeGreaterThan(0);
    });

    // Test each navigation item has a valid route
    describe("each NAV_ITEM path should exist in router", () => {
      const allNavItems = [...NAV_ITEMS, ...BOTTOM_ITEMS];

      allNavItems.forEach((item) => {
        if (item.path) {
          it(`route ${item.path} for "${item.label}" should exist`, () => {
            // Check if the route or a parent route exists
            const routeExists =
              definedRoutes.includes(item.path) ||
              definedRoutes.some(
                (route) =>
                  item.path?.startsWith(route) ||
                  route.startsWith(item.path || ""),
              );

            expect(routeExists).toBe(true);
            if (!routeExists) {
              console.error(
                `MISSING ROUTE: ${item.path} (${item.label}) is not defined in router/index.tsx`,
              );
              console.error("Defined routes:", definedRoutes);
            }
          });
        }
      });
    });

    // Specific tests for known problematic routes (RED phase - should fail)
    describe("specific route existence checks", () => {
      it("/studio/agents route should exist", () => {
        const agentsItem = NAV_ITEMS.find((item) => item.id === "agents");
        expect(agentsItem).toBeDefined();
        expect(agentsItem?.path).toBe("/studio/agents");

        // This will FAIL until the route is added
        expect(definedRoutes).toContain("/studio/agents");
      });

      it("/studio/traces route should exist (redirects to observability)", () => {
        // Traces is consolidated under observability (Sprint 7)
        // /studio/traces redirects to /studio/observability/traces
        // Nav item is "observability" not "traces"
        const observabilityItem = NAV_ITEMS.find(
          (item) => item.id === "observability",
        );
        expect(observabilityItem).toBeDefined();
        expect(observabilityItem?.path).toBe("/studio/observability");

        // The redirect route exists in router
        expect(definedRoutes).toContain("/studio/traces");
      });

      it("/studio/chat route should exist", () => {
        const chatItem = NAV_ITEMS.find((item) => item.id === "chat");
        expect(chatItem).toBeDefined();
        expect(chatItem?.path).toBe("/studio/chat");
        expect(definedRoutes).toContain("/studio/chat");
      });

      it("/studio/workflows route should exist", () => {
        const workflowsItem = NAV_ITEMS.find((item) => item.id === "workflows");
        expect(workflowsItem).toBeDefined();
        expect(workflowsItem?.path).toBe("/studio/workflows");
        expect(definedRoutes).toContain("/studio/workflows");
      });

      it("/studio/observability route should exist", () => {
        const obsItem = NAV_ITEMS.find((item) => item.id === "observability");
        expect(obsItem).toBeDefined();
        expect(obsItem?.path).toBe("/studio/observability");
        expect(definedRoutes).toContain("/studio/observability");
      });

      it("/studio/mcp route should exist", () => {
        const mcpItem = NAV_ITEMS.find((item) => item.id === "mcp");
        expect(mcpItem).toBeDefined();
        expect(mcpItem?.path).toBe("/studio/mcp");
        expect(definedRoutes).toContain("/studio/mcp");
      });

      it("/studio/cost route should exist", () => {
        const costItem = NAV_ITEMS.find((item) => item.id === "cost");
        expect(costItem).toBeDefined();
        expect(costItem?.path).toBe("/studio/cost");
        expect(definedRoutes).toContain("/studio/cost");
      });

      it("/studio/files route should exist", () => {
        const filesItem = NAV_ITEMS.find((item) => item.id === "files");
        expect(filesItem).toBeDefined();
        expect(filesItem?.path).toBe("/studio/files");
        expect(definedRoutes).toContain("/studio/files");
      });

      it("/studio/admin route should exist", () => {
        const adminItem = NAV_ITEMS.find((item) => item.id === "admin");
        expect(adminItem).toBeDefined();
        expect(adminItem?.path).toBe("/studio/admin");
        expect(definedRoutes).toContain("/studio/admin");
      });

      it("/studio/help route should exist", () => {
        const helpItem = BOTTOM_ITEMS.find((item) => item.id === "help");
        expect(helpItem).toBeDefined();
        expect(helpItem?.path).toBe("/studio/help");
        expect(definedRoutes).toContain("/studio/help");
      });

      it("/studio/settings route should exist", () => {
        const settingsItem = BOTTOM_ITEMS.find(
          (item) => item.id === "settings",
        );
        expect(settingsItem).toBeDefined();
        expect(settingsItem?.path).toBe("/studio/settings");
        expect(definedRoutes).toContain("/studio/settings");
      });
    });
  });

  describe("Route Definition Consistency", () => {
    it("all ActivityBar paths should be unique", () => {
      const allPaths = [...NAV_ITEMS, ...BOTTOM_ITEMS]
        .filter((item) => item.path)
        .map((item) => item.path);

      const uniquePaths = new Set(allPaths);
      expect(allPaths.length).toBe(uniquePaths.size);
    });

    it("all ActivityBar items should have an id", () => {
      const allItems = [...NAV_ITEMS, ...BOTTOM_ITEMS];
      allItems.forEach((item) => {
        expect(item.id).toBeDefined();
        expect(item.id.length).toBeGreaterThan(0);
      });
    });

    it("all ActivityBar items should have a label", () => {
      const allItems = [...NAV_ITEMS, ...BOTTOM_ITEMS];
      allItems.forEach((item) => {
        expect(item.label).toBeDefined();
        expect(item.label.length).toBeGreaterThan(0);
      });
    });
  });
});

/**
 * Command Palette Route Coverage Tests
 *
 * Verifies that command palette navigation commands point to valid routes.
 */
describe("Command Palette Route Coverage", () => {
  // Import PALETTE_COMMANDS if exposed, or check StudioShellLayout
  // For now, we document the commands that navigate

  const NAVIGATION_COMMANDS = [
    { id: "open-settings", path: "/studio/settings" },
    { id: "open-help", path: "/studio/help" },
    { id: "open-observability", path: "/studio/observability" },
    { id: "open-compliance", path: "/studio/compliance" },
  ];

  // @ts-expect-error - router.routes is internal but accessible
  const definedRoutes = extractRoutePaths(router.routes);

  NAVIGATION_COMMANDS.forEach((cmd) => {
    it(`command "${cmd.id}" navigates to valid route ${cmd.path}`, () => {
      expect(definedRoutes).toContain(cmd.path);
    });
  });
});
