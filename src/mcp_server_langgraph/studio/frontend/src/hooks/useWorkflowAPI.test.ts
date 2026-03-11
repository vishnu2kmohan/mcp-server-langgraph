/**
 * useWorkflowAPI Tests
 *
 * TDD tests for the workflow API hook wrapper.
 * This thin wrapper allows tests to mock workflow-related API hooks
 * without loading the entire RTK Query module.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock the API module to prevent OOM during test loading
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useGetWorkflowSuggestionsMutation: vi.fn(() => [
      vi.fn(),
      { isLoading: false },
    ]),
    useListWorkflowExecutionsQuery: vi.fn(() => ({
      data: undefined,
      isLoading: false,
      error: null,
    })),
  };
});
// Import after mock
import {
  useGetWorkflowSuggestionsMutation,
  useListWorkflowExecutionsQuery,
} from "./useWorkflowAPI";

describe("useWorkflowAPI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("useGetWorkflowSuggestionsMutation", () => {
    it("should export the mutation hook", () => {
      expect(useGetWorkflowSuggestionsMutation).toBeDefined();
      expect(typeof useGetWorkflowSuggestionsMutation).toBe("function");
    });

    it("should return trigger function and result object", () => {
      const result = useGetWorkflowSuggestionsMutation();
      expect(Array.isArray(result)).toBe(true);
      expect(result).toHaveLength(2);
      expect(typeof result[0]).toBe("function");
      expect(typeof result[1]).toBe("object");
    });
  });

  describe("useListWorkflowExecutionsQuery", () => {
    it("should export the query hook", () => {
      expect(useListWorkflowExecutionsQuery).toBeDefined();
      expect(typeof useListWorkflowExecutionsQuery).toBe("function");
    });

    it("should return query result object", () => {
      const result = useListWorkflowExecutionsQuery("workflow-1");
      expect(result).toHaveProperty("isLoading");
      expect(result.isLoading).toBe(false);
    });
  });
});
