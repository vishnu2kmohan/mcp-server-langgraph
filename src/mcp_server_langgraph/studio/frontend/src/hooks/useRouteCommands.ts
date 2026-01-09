/**
 * useRouteCommands Hook
 *
 * Registers route-specific commands with the CommandPaletteContext.
 * Commands are automatically registered when navigating to a route
 * and unregistered when leaving.
 *
 * Features:
 * - Route-based command registration
 * - Automatic cleanup on route change
 * - Supports nested routes (matches parent path patterns)
 *
 * Sprint 4: CommandPalette Enhancement
 * Reference: Plan Part 3 - useRouteCommands Hook
 */

import { useEffect } from "react";
import { useLocation } from "react-router";
import { useCommandPalette } from "../contexts/CommandPaletteContext";
import type { Command } from "../ai/AICommandPalette";

// ==============================================================================
// Route Command Definitions
// ==============================================================================

/**
 * Get commands for a specific route pathname.
 * Matches by checking if pathname includes the route pattern.
 */
function getCommandsForRoute(pathname: string): Command[] {
  // Workflow routes
  if (pathname.includes("/workflows")) {
    return [
      {
        id: "route-new-workflow",
        name: "New Workflow",
        description: "Create a new workflow",
        category: "Workflow",
      },
      {
        id: "route-import-workflow",
        name: "Import Workflow",
        description: "Import workflow from JSON",
        category: "Workflow",
      },
      {
        id: "route-export-workflow",
        name: "Export Workflow",
        description: "Export current workflow",
        category: "Workflow",
      },
    ];
  }

  // Observability routes
  if (pathname.includes("/observability")) {
    return [
      {
        id: "route-query-logs",
        name: "Query Logs",
        description: "Search log entries",
        category: "Observability",
      },
      {
        id: "route-create-alert",
        name: "Create Alert Rule",
        description: "Create new alert rule",
        category: "Observability",
      },
      {
        id: "route-view-traces",
        name: "View Traces",
        description: "View distributed traces",
        category: "Observability",
      },
    ];
  }

  // Connections routes
  if (pathname.includes("/connections")) {
    return [
      {
        id: "route-new-connection",
        name: "New Connection",
        description: "Add new MCP connection",
        category: "Connections",
      },
      {
        id: "route-test-connections",
        name: "Test All Connections",
        description: "Test all connection health",
        category: "Connections",
      },
    ];
  }

  // Projects routes
  if (pathname.includes("/projects")) {
    return [
      {
        id: "route-new-project",
        name: "New Project",
        description: "Create a new project",
        category: "Projects",
      },
    ];
  }

  // Settings routes
  if (pathname.includes("/settings")) {
    return [
      {
        id: "route-export-settings",
        name: "Export Settings",
        description: "Export configuration",
        category: "Settings",
      },
      {
        id: "route-import-settings",
        name: "Import Settings",
        description: "Import configuration",
        category: "Settings",
      },
    ];
  }

  // MCP routes
  if (pathname.includes("/mcp")) {
    return [
      {
        id: "route-browse-tools",
        name: "Browse Tools",
        description: "Browse available MCP tools",
        category: "MCP",
      },
      {
        id: "route-browse-resources",
        name: "Browse Resources",
        description: "Browse available MCP resources",
        category: "MCP",
      },
      {
        id: "route-browse-prompts",
        name: "Browse Prompts",
        description: "Browse available MCP prompts",
        category: "MCP",
      },
    ];
  }

  // Agents routes
  if (pathname.includes("/agents")) {
    return [
      {
        id: "route-configure-agent",
        name: "Configure Agent",
        description: "Configure agent settings",
        category: "Agents",
      },
      {
        id: "route-test-agent",
        name: "Test Agent",
        description: "Run agent diagnostics",
        category: "Agents",
      },
    ];
  }

  // Artifacts routes
  if (pathname.includes("/artifacts")) {
    return [
      {
        id: "route-upload-artifact",
        name: "Upload Artifact",
        description: "Upload a new artifact",
        category: "Artifacts",
      },
      {
        id: "route-search-artifacts",
        name: "Search Artifacts",
        description: "Search in artifacts",
        category: "Artifacts",
      },
    ];
  }

  // Cost routes
  if (pathname.includes("/cost")) {
    return [
      {
        id: "route-set-budget",
        name: "Set Budget",
        description: "Configure budget limits",
        category: "Cost",
      },
      {
        id: "route-export-cost-report",
        name: "Export Cost Report",
        description: "Export cost analytics",
        category: "Cost",
      },
    ];
  }

  // Help routes
  if (pathname.includes("/help")) {
    return [
      {
        id: "route-search-docs",
        name: "Search Docs",
        description: "Search documentation",
        category: "Help",
      },
      {
        id: "route-keyboard-shortcuts",
        name: "Keyboard Shortcuts",
        description: "View keyboard shortcuts",
        category: "Help",
      },
    ];
  }

  // Compliance routes
  if (pathname.includes("/compliance")) {
    return [
      {
        id: "route-run-compliance-check",
        name: "Run Compliance Check",
        description: "Run compliance validation",
        category: "Compliance",
      },
      {
        id: "route-export-compliance-report",
        name: "Export Report",
        description: "Export compliance report",
        category: "Compliance",
      },
    ];
  }

  // Audit routes
  if (pathname.includes("/audit")) {
    return [
      {
        id: "route-export-audit-log",
        name: "Export Audit Log",
        description: "Export audit log entries",
        category: "Audit",
      },
      {
        id: "route-filter-audit-log",
        name: "Filter Audit Log",
        description: "Apply audit log filters",
        category: "Audit",
      },
    ];
  }

  // Vectors routes
  if (pathname.includes("/vectors")) {
    return [
      {
        id: "route-search-vectors",
        name: "Search Vectors",
        description: "Semantic vector search",
        category: "Vectors",
      },
      {
        id: "route-reindex-vectors",
        name: "Reindex Vectors",
        description: "Reindex vector database",
        category: "Vectors",
      },
    ];
  }

  // Analytics routes
  if (pathname.includes("/analytics")) {
    return [
      {
        id: "route-export-report",
        name: "Export Report",
        description: "Export analytics report",
        category: "Analytics",
      },
      {
        id: "route-configure-metrics",
        name: "Configure Metrics",
        description: "Configure HEART metrics",
        category: "Analytics",
      },
    ];
  }

  // Skills routes
  if (pathname.includes("/skills")) {
    return [
      {
        id: "route-browse-marketplace",
        name: "Browse Marketplace",
        description: "Browse skills marketplace",
        category: "Skills",
      },
      {
        id: "route-install-skill",
        name: "Install Skill",
        description: "Install a new skill",
        category: "Skills",
      },
    ];
  }

  // Admin routes
  if (pathname.includes("/admin")) {
    return [
      {
        id: "route-manage-users",
        name: "Manage Users",
        description: "User management",
        category: "Admin",
      },
      {
        id: "route-view-system-health",
        name: "System Health",
        description: "View system health",
        category: "Admin",
      },
    ];
  }

  // Default: no route-specific commands
  return [];
}

// ==============================================================================
// Hook
// ==============================================================================

/**
 * Hook to register route-specific commands with the command palette.
 * Call this in components that need route-aware command registration.
 *
 * Commands are automatically registered on mount/route change and
 * unregistered on unmount/route change.
 */
export function useRouteCommands(): void {
  const location = useLocation();
  const { registerCommands, unregisterCommands } = useCommandPalette();

  // Only trigger on pathname changes (ignore hash/query)
  const pathname = location.pathname;

  useEffect(() => {
    const commands = getCommandsForRoute(pathname);

    // Don't register if no commands for this route
    if (commands.length === 0) {
      return;
    }

    // Register commands
    registerCommands(commands);

    // Cleanup: unregister when route changes or component unmounts
    return () => {
      unregisterCommands(commands.map((c) => c.id));
    };
  }, [pathname, registerCommands, unregisterCommands]);
}

export default useRouteCommands;
