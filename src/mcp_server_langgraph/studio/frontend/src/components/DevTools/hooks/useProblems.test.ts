/**
 * useProblems Hook Tests
 *
 * TDD tests for the problems management hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useProblems, type Problem } from "./useProblems";

// =============================================================================
// Test Data
// =============================================================================

const createMockProblem = (overrides: Partial<Problem> = {}): Problem => ({
  id: `problem-${Date.now()}-${Math.random()}`,
  severity: "error",
  message: "Test error message",
  source: "system",
  timestamp: Date.now(),
  ...overrides,
});

// =============================================================================
// Tests
// =============================================================================

describe("useProblems", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("should return empty problems initially", () => {
      const { result } = renderHook(() => useProblems());

      expect(result.current.problems).toEqual([]);
    });

    it("should return zero errorCount initially", () => {
      const { result } = renderHook(() => useProblems());

      expect(result.current.errorCount).toBe(0);
    });

    it("should return zero warningCount initially", () => {
      const { result } = renderHook(() => useProblems());

      expect(result.current.warningCount).toBe(0);
    });

    it("should return addProblem function", () => {
      const { result } = renderHook(() => useProblems());

      expect(typeof result.current.addProblem).toBe("function");
    });

    it("should return dismissProblem function", () => {
      const { result } = renderHook(() => useProblems());

      expect(typeof result.current.dismissProblem).toBe("function");
    });

    it("should return clearProblems function", () => {
      const { result } = renderHook(() => useProblems());

      expect(typeof result.current.clearProblems).toBe("function");
    });
  });

  describe("addProblem", () => {
    it("should add a problem to the list", () => {
      const { result } = renderHook(() => useProblems());
      const problem = createMockProblem({ id: "problem-1" });

      act(() => {
        result.current.addProblem(problem);
      });

      expect(result.current.problems).toHaveLength(1);
      expect(result.current.problems[0].id).toBe("problem-1");
    });

    it("should add multiple problems", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ id: "problem-1" }));
        result.current.addProblem(createMockProblem({ id: "problem-2" }));
        result.current.addProblem(createMockProblem({ id: "problem-3" }));
      });

      expect(result.current.problems).toHaveLength(3);
    });

    it("should not add duplicate problems with same ID", () => {
      const { result } = renderHook(() => useProblems());
      const problem = createMockProblem({ id: "duplicate-id" });

      act(() => {
        result.current.addProblem(problem);
        result.current.addProblem(problem);
        result.current.addProblem(problem);
      });

      expect(result.current.problems).toHaveLength(1);
    });

    it("should update errorCount when error added", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ severity: "error" }));
      });

      expect(result.current.errorCount).toBe(1);
    });

    it("should update warningCount when warning added", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ severity: "warning" }));
      });

      expect(result.current.warningCount).toBe(1);
    });

    it("should add problem with file location", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({
            id: "problem-1",
            file: "src/app.ts",
            line: 42,
            column: 10,
          }),
        );
      });

      expect(result.current.problems[0].file).toBe("src/app.ts");
      expect(result.current.problems[0].line).toBe(42);
      expect(result.current.problems[0].column).toBe(10);
    });
  });

  describe("dismissProblem", () => {
    it("should mark problem as dismissed", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ id: "problem-1" }));
      });

      act(() => {
        result.current.dismissProblem("problem-1");
      });

      // Dismissed problems are filtered out
      expect(result.current.problems).toHaveLength(0);
    });

    it("should decrease errorCount when error dismissed", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "error" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-2", severity: "error" }),
        );
      });

      expect(result.current.errorCount).toBe(2);

      act(() => {
        result.current.dismissProblem("problem-1");
      });

      expect(result.current.errorCount).toBe(1);
    });

    it("should decrease warningCount when warning dismissed", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "warning" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-2", severity: "warning" }),
        );
      });

      expect(result.current.warningCount).toBe(2);

      act(() => {
        result.current.dismissProblem("problem-1");
      });

      expect(result.current.warningCount).toBe(1);
    });

    it("should do nothing if problem ID not found", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ id: "problem-1" }));
      });

      act(() => {
        result.current.dismissProblem("non-existent");
      });

      expect(result.current.problems).toHaveLength(1);
    });
  });

  describe("clearProblems", () => {
    it("should clear all problems", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ id: "problem-1" }));
        result.current.addProblem(createMockProblem({ id: "problem-2" }));
      });

      expect(result.current.problems).toHaveLength(2);

      act(() => {
        result.current.clearProblems();
      });

      expect(result.current.problems).toHaveLength(0);
    });

    it("should reset errorCount to zero", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "error" }),
        );
      });

      expect(result.current.errorCount).toBe(1);

      act(() => {
        result.current.clearProblems();
      });

      expect(result.current.errorCount).toBe(0);
    });

    it("should reset warningCount to zero", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "warning" }),
        );
      });

      expect(result.current.warningCount).toBe(1);

      act(() => {
        result.current.clearProblems();
      });

      expect(result.current.warningCount).toBe(0);
    });
  });

  describe("filtering", () => {
    it("should show all problems when filter is 'all'", () => {
      const { result } = renderHook(() => useProblems({ filter: "all" }));

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "error" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-2", severity: "warning" }),
        );
      });

      expect(result.current.problems).toHaveLength(2);
    });

    it("should filter to only errors when filter is 'errors'", () => {
      const { result } = renderHook(() => useProblems({ filter: "errors" }));

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "error" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-2", severity: "warning" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-3", severity: "error" }),
        );
      });

      expect(result.current.problems).toHaveLength(2);
      expect(result.current.problems.every((p) => p.severity === "error")).toBe(
        true,
      );
    });

    it("should filter to only warnings when filter is 'warnings'", () => {
      const { result } = renderHook(() => useProblems({ filter: "warnings" }));

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "error" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-2", severity: "warning" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-3", severity: "warning" }),
        );
      });

      expect(result.current.problems).toHaveLength(2);
      expect(
        result.current.problems.every((p) => p.severity === "warning"),
      ).toBe(true);
    });

    it("should maintain correct counts regardless of filter", () => {
      const { result } = renderHook(() => useProblems({ filter: "errors" }));

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", severity: "error" }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-2", severity: "warning" }),
        );
      });

      // Filter only shows errors
      expect(result.current.problems).toHaveLength(1);
      // But counts include all problems
      expect(result.current.errorCount).toBe(1);
      expect(result.current.warningCount).toBe(1);
    });
  });

  describe("sorting", () => {
    it("should sort problems by timestamp descending (newest first)", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "old", timestamp: 1000 }),
        );
        result.current.addProblem(
          createMockProblem({ id: "new", timestamp: 3000 }),
        );
        result.current.addProblem(
          createMockProblem({ id: "middle", timestamp: 2000 }),
        );
      });

      expect(result.current.problems[0].id).toBe("new");
      expect(result.current.problems[1].id).toBe("middle");
      expect(result.current.problems[2].id).toBe("old");
    });
  });

  describe("problem types", () => {
    it("should handle session errors", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({
            id: "session-error",
            source: "session",
            message: "Session expired",
          }),
        );
      });

      expect(result.current.problems[0].source).toBe("session");
    });

    it("should handle MCP errors", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({
            id: "mcp-error",
            source: "mcp",
            message: "Tool invocation failed",
          }),
        );
      });

      expect(result.current.problems[0].source).toBe("mcp");
    });

    it("should handle validation errors", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({
            id: "validation-error",
            source: "validation",
            message: "Invalid input format",
          }),
        );
      });

      expect(result.current.problems[0].source).toBe("validation");
    });

    it("should handle API errors", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(
          createMockProblem({
            id: "api-error",
            source: "api",
            message: "Request failed with status 500",
          }),
        );
      });

      expect(result.current.problems[0].source).toBe("api");
    });
  });

  describe("callback stability", () => {
    it("should have stable addProblem reference", () => {
      const { result, rerender } = renderHook(() => useProblems());

      const firstAddProblem = result.current.addProblem;

      rerender();

      expect(result.current.addProblem).toBe(firstAddProblem);
    });

    it("should have stable dismissProblem reference", () => {
      const { result, rerender } = renderHook(() => useProblems());

      const firstDismiss = result.current.dismissProblem;

      rerender();

      expect(result.current.dismissProblem).toBe(firstDismiss);
    });

    it("should have stable clearProblems reference", () => {
      const { result, rerender } = renderHook(() => useProblems());

      const firstClear = result.current.clearProblems;

      rerender();

      expect(result.current.clearProblems).toBe(firstClear);
    });
  });

  describe("edge cases", () => {
    it("should handle problems with same timestamp", () => {
      const { result } = renderHook(() => useProblems());
      const timestamp = Date.now();

      act(() => {
        result.current.addProblem(
          createMockProblem({ id: "problem-1", timestamp }),
        );
        result.current.addProblem(
          createMockProblem({ id: "problem-2", timestamp }),
        );
      });

      expect(result.current.problems).toHaveLength(2);
    });

    it("should handle dismissing already dismissed problem", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ id: "problem-1" }));
      });

      act(() => {
        result.current.dismissProblem("problem-1");
      });

      act(() => {
        result.current.dismissProblem("problem-1");
      });

      expect(result.current.problems).toHaveLength(0);
    });

    it("should handle adding problem after clear", () => {
      const { result } = renderHook(() => useProblems());

      act(() => {
        result.current.addProblem(createMockProblem({ id: "problem-1" }));
      });

      act(() => {
        result.current.clearProblems();
      });

      act(() => {
        result.current.addProblem(createMockProblem({ id: "problem-2" }));
      });

      expect(result.current.problems).toHaveLength(1);
      expect(result.current.problems[0].id).toBe("problem-2");
    });
  });
});
