/**
 * useWorkflowValidation Hook Tests
 *
 * Tests for the debounced workflow validation hook.
 * Uses centralized /validate endpoint (NO JS DUPLICATION).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Mock the RTK Query API
vi.mock("../api", () => ({
  useValidateWorkflowMutation: vi.fn(),
}));

// Mock the debounce hook
vi.mock("./useDebounce", () => ({
  useDebouncedCallback: vi.fn((callback, _delay) => {
    const fn = callback as ((workflowId: string) => void) & {
      cancel: () => void;
      flush: () => void;
    };
    fn.cancel = vi.fn();
    fn.flush = vi.fn();
    return fn;
  }),
}));

import { useValidateWorkflowMutation } from "../api";
import { useWorkflowValidation } from "./useWorkflowValidation";

describe("useWorkflowValidation", () => {
  const mockValidateWorkflow = vi.fn();
  const mockUnwrap = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Setup mock mutation
    mockValidateWorkflow.mockReturnValue({
      unwrap: mockUnwrap,
    });

    (useValidateWorkflowMutation as ReturnType<typeof vi.fn>).mockReturnValue([
      mockValidateWorkflow,
      { isLoading: false },
    ]);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("initialization", () => {
    it("should return null validation result initially", () => {
      const { result } = renderHook(() => useWorkflowValidation());

      expect(result.current.validationResult).toBeNull();
      expect(result.current.isValidating).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should provide validate function", () => {
      const { result } = renderHook(() => useWorkflowValidation());

      expect(typeof result.current.validate).toBe("function");
    });

    it("should provide validateNow function", () => {
      const { result } = renderHook(() => useWorkflowValidation());

      expect(typeof result.current.validateNow).toBe("function");
    });

    it("should provide cancel function", () => {
      const { result } = renderHook(() => useWorkflowValidation());

      expect(typeof result.current.cancel).toBe("function");
    });

    it("should provide reset function", () => {
      const { result } = renderHook(() => useWorkflowValidation());

      expect(typeof result.current.reset).toBe("function");
    });
  });

  describe("validateNow", () => {
    it("should call validation API with workflow ID", async () => {
      const mockResult = {
        valid: true,
        errors: [],
        warnings: [],
      };
      mockUnwrap.mockResolvedValue(mockResult);

      const { result } = renderHook(() => useWorkflowValidation());

      await act(async () => {
        await result.current.validateNow("workflow-123");
      });

      expect(mockValidateWorkflow).toHaveBeenCalledWith({
        workflow_id: "workflow-123",
      });
    });

    it("should update validation result on success", async () => {
      const mockResult = {
        valid: true,
        errors: [],
        warnings: ["Unknown node type detected"],
      };
      mockUnwrap.mockResolvedValue(mockResult);

      const { result } = renderHook(() => useWorkflowValidation());

      await act(async () => {
        await result.current.validateNow("workflow-123");
      });

      expect(result.current.validationResult).toEqual(mockResult);
      expect(result.current.error).toBeNull();
    });

    it("should handle validation errors", async () => {
      const mockResult = {
        valid: false,
        errors: ["Missing start node", "Orphan node detected"],
        warnings: [],
      };
      mockUnwrap.mockResolvedValue(mockResult);

      const { result } = renderHook(() => useWorkflowValidation());

      await act(async () => {
        await result.current.validateNow("workflow-456");
      });

      expect(result.current.validationResult?.valid).toBe(false);
      expect(result.current.validationResult?.errors).toContain(
        "Missing start node",
      );
    });

    it("should set error on API failure", async () => {
      mockUnwrap.mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() => useWorkflowValidation());

      await act(async () => {
        try {
          await result.current.validateNow("workflow-789");
        } catch {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe("Network error");
      expect(result.current.validationResult).toBeNull();
    });
  });

  describe("reset", () => {
    it("should clear validation result", async () => {
      const mockResult = {
        valid: true,
        errors: [],
        warnings: [],
      };
      mockUnwrap.mockResolvedValue(mockResult);

      const { result } = renderHook(() => useWorkflowValidation());

      // First validate
      await act(async () => {
        await result.current.validateNow("workflow-123");
      });

      expect(result.current.validationResult).not.toBeNull();

      // Then reset
      act(() => {
        result.current.reset();
      });

      expect(result.current.validationResult).toBeNull();
      expect(result.current.error).toBeNull();
    });
  });

  describe("isValidating state", () => {
    it("should reflect loading state from mutation", () => {
      (useValidateWorkflowMutation as ReturnType<typeof vi.fn>).mockReturnValue(
        [mockValidateWorkflow, { isLoading: true }],
      );

      const { result } = renderHook(() => useWorkflowValidation());

      expect(result.current.isValidating).toBe(true);
    });
  });
});
