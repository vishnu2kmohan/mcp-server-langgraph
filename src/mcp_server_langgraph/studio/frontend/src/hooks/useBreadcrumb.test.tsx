/**
 * Tests for useBreadcrumb hook
 *
 * TDD RED Phase: Tests written before implementation
 *
 * The useBreadcrumb hook:
 * - Uses useMatches() from react-router to get matched routes
 * - Filters routes with handle.breadcrumb metadata
 * - Returns BreadcrumbItem[] for rendering
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { MemoryRouter, useMatches } from "react-router";
import type { ReactNode } from "react";

// Mock react-router's useMatches
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useMatches: vi.fn(),
  };
});

// Import after mocking
import { useBreadcrumb, type BreadcrumbItem } from "./useBreadcrumb";

// Wrapper for rendering hooks with router context
function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter>{children}</MemoryRouter>;
  };
}

describe("useBreadcrumb", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset to default return value
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("basic functionality", () => {
    it("should return empty array when no routes have breadcrumb handle", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        { id: "root", pathname: "/", handle: undefined },
        { id: "studio", pathname: "/studio", handle: undefined },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toEqual([]);
    });

    it("should return breadcrumb items for routes with handle.breadcrumb", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        { id: "root", pathname: "/", handle: undefined },
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
        {
          id: "projects",
          pathname: "/studio/projects",
          handle: { breadcrumb: "Projects" },
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toHaveLength(2);
      expect(result.current[0]).toEqual({
        label: "Agent Studio",
        path: "/studio",
        isCurrent: false,
      });
      expect(result.current[1]).toEqual({
        label: "Projects",
        path: "/studio/projects",
        isCurrent: true,
      });
    });

    it("should mark only the last item as current", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
        {
          id: "projects",
          pathname: "/studio/projects",
          handle: { breadcrumb: "Projects" },
        },
        {
          id: "project-detail",
          pathname: "/studio/projects/proj-123",
          handle: { breadcrumb: "Project Details" },
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toHaveLength(3);
      expect(result.current[0].isCurrent).toBe(false);
      expect(result.current[1].isCurrent).toBe(false);
      expect(result.current[2].isCurrent).toBe(true);
    });
  });

  describe("dynamic breadcrumbs with params", () => {
    it("should support function-based breadcrumb that receives params", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
        {
          id: "projects",
          pathname: "/studio/projects",
          handle: { breadcrumb: "Projects" },
        },
        {
          id: "project-detail",
          pathname: "/studio/projects/proj-123",
          params: { projectId: "proj-123" },
          handle: {
            breadcrumb: (params: { projectId: string }) =>
              `Project: ${params.projectId}`,
          },
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toHaveLength(3);
      expect(result.current[2]).toEqual({
        label: "Project: proj-123",
        path: "/studio/projects/proj-123",
        isCurrent: true,
      });
    });

    it("should handle workflow nested routes correctly", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
        {
          id: "workflows",
          pathname: "/studio/workflows",
          handle: { breadcrumb: "Workflows" },
        },
        {
          id: "workflow-detail",
          pathname: "/studio/workflows/wf-abc",
          params: { workflowId: "wf-abc" },
          handle: {
            breadcrumb: (params: { workflowId: string }) =>
              `Workflow: ${params.workflowId}`,
          },
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toHaveLength(3);
      expect(result.current[0].label).toBe("Agent Studio");
      expect(result.current[1].label).toBe("Workflows");
      expect(result.current[2].label).toBe("Workflow: wf-abc");
    });
  });

  describe("edge cases", () => {
    it("should skip routes without handle property", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        { id: "root", pathname: "/" },
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
        { id: "chat-wrapper", pathname: "/studio/chat" }, // No handle
        {
          id: "chat-session",
          pathname: "/studio/chat/session-123",
          handle: { breadcrumb: "Chat Session" },
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toHaveLength(2);
      expect(result.current[0].label).toBe("Agent Studio");
      expect(result.current[1].label).toBe("Chat Session");
    });

    it("should handle empty breadcrumb string by skipping", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
        {
          id: "chat",
          pathname: "/studio/chat",
          handle: { breadcrumb: "" }, // Empty = skip
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toHaveLength(1);
      expect(result.current[0].label).toBe("Agent Studio");
    });

    it("should handle null breadcrumb by skipping", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
        {
          id: "settings",
          pathname: "/studio/settings",
          handle: { breadcrumb: null },
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toHaveLength(1);
    });
  });

  describe("type safety", () => {
    it("should return correctly typed BreadcrumbItem array", () => {
      (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: "studio",
          pathname: "/studio",
          handle: { breadcrumb: "Agent Studio" },
        },
      ]);

      const { result } = renderHook(() => useBreadcrumb(), {
        wrapper: createWrapper(),
      });

      // Type check: result.current should be BreadcrumbItem[]
      const items: BreadcrumbItem[] = result.current;
      expect(items).toBeDefined();
      expect(items[0].label).toBeTypeOf("string");
      expect(items[0].path).toBeTypeOf("string");
      expect(items[0].isCurrent).toBeTypeOf("boolean");
    });
  });

  // =========================================================================
  // Route-specific breadcrumb tests (Sprint 2.3 Phase 2)
  // Validates expected breadcrumb structure for additional routes
  // =========================================================================
  describe("route-specific breadcrumbs", () => {
    describe("Admin routes", () => {
      it("should handle /studio/admin route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "admin",
            pathname: "/studio/admin",
            handle: { breadcrumb: "Admin" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Admin",
          path: "/studio/admin",
          isCurrent: true,
        });
      });

      it("should handle /studio/admin/dashboard route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "admin",
            pathname: "/studio/admin",
            handle: { breadcrumb: "Admin" },
          },
          {
            id: "admin-dashboard",
            pathname: "/studio/admin/dashboard",
            handle: { breadcrumb: "Dashboard" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(2);
        expect(result.current[0].label).toBe("Admin");
        expect(result.current[0].isCurrent).toBe(false);
        expect(result.current[1].label).toBe("Dashboard");
        expect(result.current[1].isCurrent).toBe(true);
      });

      it("should handle /studio/admin/audit-logs route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "admin",
            pathname: "/studio/admin",
            handle: { breadcrumb: "Admin" },
          },
          {
            id: "admin-audit-logs",
            pathname: "/studio/admin/audit-logs",
            handle: { breadcrumb: "Audit Logs" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(2);
        expect(result.current[1].label).toBe("Audit Logs");
      });
    });

    describe("Settings route", () => {
      it("should handle /studio/settings route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "settings",
            pathname: "/studio/settings",
            handle: { breadcrumb: "Settings" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Settings",
          path: "/studio/settings",
          isCurrent: true,
        });
      });
    });

    describe("Cost route", () => {
      it("should handle /studio/cost route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "cost",
            pathname: "/studio/cost",
            handle: { breadcrumb: "Cost" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Cost",
          path: "/studio/cost",
          isCurrent: true,
        });
      });
    });

    describe("Help route", () => {
      it("should handle /studio/help route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "help",
            pathname: "/studio/help",
            handle: { breadcrumb: "Help" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Help",
          path: "/studio/help",
          isCurrent: true,
        });
      });
    });

    describe("Files route", () => {
      it("should handle /studio/files route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "files",
            pathname: "/studio/files",
            handle: { breadcrumb: "Files" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Files",
          path: "/studio/files",
          isCurrent: true,
        });
      });
    });

    describe("Compliance route", () => {
      it("should handle /studio/compliance route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "compliance",
            pathname: "/studio/compliance",
            handle: { breadcrumb: "Compliance" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Compliance",
          path: "/studio/compliance",
          isCurrent: true,
        });
      });
    });

    describe("Audit route", () => {
      it("should handle /studio/audit route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "audit",
            pathname: "/studio/audit",
            handle: { breadcrumb: "Audit" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Audit",
          path: "/studio/audit",
          isCurrent: true,
        });
      });
    });

    describe("Analytics route", () => {
      it("should handle /studio/analytics route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "analytics",
            pathname: "/studio/analytics",
            handle: { breadcrumb: "Analytics" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0]).toEqual({
          label: "Analytics",
          path: "/studio/analytics",
          isCurrent: true,
        });
      });
    });

    describe("Standalone observability routes", () => {
      it("should handle /studio/agents standalone route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "agents",
            pathname: "/studio/agents",
            handle: { breadcrumb: "Agents" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0].label).toBe("Agents");
      });

      it("should handle /studio/vectors standalone route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "vectors",
            pathname: "/studio/vectors",
            handle: { breadcrumb: "Vectors" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0].label).toBe("Vectors");
      });

      it("should handle /studio/logs standalone route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "logs",
            pathname: "/studio/logs",
            handle: { breadcrumb: "Logs" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0].label).toBe("Logs");
      });

      it("should handle /studio/metrics standalone route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "metrics",
            pathname: "/studio/metrics",
            handle: { breadcrumb: "Metrics" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0].label).toBe("Metrics");
      });

      it("should handle /studio/alerts standalone route", () => {
        (useMatches as ReturnType<typeof vi.fn>).mockReturnValue([
          {
            id: "alerts",
            pathname: "/studio/alerts",
            handle: { breadcrumb: "Alerts" },
          },
        ]);

        const { result } = renderHook(() => useBreadcrumb(), {
          wrapper: createWrapper(),
        });

        expect(result.current).toHaveLength(1);
        expect(result.current[0].label).toBe("Alerts");
      });
    });
  });
});
