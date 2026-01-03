/**
 * useGenerateWorkflowFromChat Hook Tests
 *
 * Tests for the hook that generates workflows from chat session history.
 * Calls centralized /from-chat endpoint (NO JS DUPLICATION).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";

// Mock react-router navigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the RTK Query API
vi.mock("../api", () => ({
  useGenerateWorkflowFromChatMutation: vi.fn(),
}));

import { useGenerateWorkflowFromChatMutation } from "../api";
import { useGenerateWorkflowFromChat } from "./useGenerateWorkflowFromChat";

import type { GenerateWorkflowFromChatResponse } from "../types";

describe("useGenerateWorkflowFromChat", () => {
  const mockGenerateWorkflow = vi.fn();
  const mockUnwrap = vi.fn();

  const mockSuccessResponse: GenerateWorkflowFromChatResponse = {
    workflow: {
      id: "wf-123",
      name: "Generated Workflow",
      title: "Test Workflow",
      description: "A workflow generated from chat",
      nodes: [],
      edges: [],
      status: "draft",
      is_public: false,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    },
    confidence: 0.85,
    suggestions: ["Add error handling", "Consider retry logic"],
    prompt_metadata: {
      name: "workflow_generator",
      version: "v1",
      hash: "abc123",
      model: "claude-opus-4-5",
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Setup mock mutation
    mockGenerateWorkflow.mockReturnValue({
      unwrap: mockUnwrap,
    });

    (
      useGenerateWorkflowFromChatMutation as ReturnType<typeof vi.fn>
    ).mockReturnValue([mockGenerateWorkflow, { isLoading: false }]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  describe("initialization", () => {
    it("should return null result initially", () => {
      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      expect(result.current.result).toBeNull();
      expect(result.current.isGenerating).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should provide generate function", () => {
      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      expect(typeof result.current.generate).toBe("function");
    });

    it("should provide reset function", () => {
      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      expect(typeof result.current.reset).toBe("function");
    });
  });

  describe("generate", () => {
    it("should call API with session ID", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);

      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(mockGenerateWorkflow).toHaveBeenCalledWith({
        session_id: "session-456",
      });
    });

    it("should call API with refinement_mode", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);

      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      await act(async () => {
        await result.current.generate({
          session_id: "session-456",
          refinement_mode: "plan",
        });
      });

      expect(mockGenerateWorkflow).toHaveBeenCalledWith({
        session_id: "session-456",
        refinement_mode: "plan",
      });
    });

    it("should call API with template_id", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);

      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      await act(async () => {
        await result.current.generate({
          session_id: "session-456",
          template_id: "template-789",
        });
      });

      expect(mockGenerateWorkflow).toHaveBeenCalledWith({
        session_id: "session-456",
        template_id: "template-789",
      });
    });

    it("should update result on success", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);

      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(result.current.result).toEqual(mockSuccessResponse);
      expect(result.current.error).toBeNull();
    });

    it("should navigate to workflow editor on success when navigateOnSuccess is true", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({ navigateOnSuccess: true }),
      );

      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(mockNavigate).toHaveBeenCalledWith("/workflows/wf-123/edit");
    });

    it("should not navigate when navigateOnSuccess is false", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({ navigateOnSuccess: false }),
      );

      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should call onSuccess callback", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);
      const onSuccess = vi.fn();

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({
          navigateOnSuccess: false,
          onSuccess,
        }),
      );

      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(onSuccess).toHaveBeenCalledWith(mockSuccessResponse);
    });

    it("should set error on API failure", async () => {
      mockUnwrap.mockRejectedValue(new Error("Generation failed"));

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({ navigateOnSuccess: false }),
      );

      await act(async () => {
        try {
          await result.current.generate({ session_id: "session-456" });
        } catch {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe("Generation failed");
      expect(result.current.result).toBeNull();
    });

    it("should call onError callback on failure", async () => {
      const error = new Error("Generation failed");
      mockUnwrap.mockRejectedValue(error);
      const onError = vi.fn();

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({
          navigateOnSuccess: false,
          onError,
        }),
      );

      await act(async () => {
        try {
          await result.current.generate({ session_id: "session-456" });
        } catch {
          // Expected to throw
        }
      });

      expect(onError).toHaveBeenCalledWith(error);
    });

    it("should handle non-Error rejection", async () => {
      mockUnwrap.mockRejectedValue("String error");

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({ navigateOnSuccess: false }),
      );

      await act(async () => {
        try {
          await result.current.generate({ session_id: "session-456" });
        } catch {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe("Failed to generate workflow");
    });
  });

  describe("reset", () => {
    it("should clear result and error", async () => {
      mockUnwrap.mockResolvedValue(mockSuccessResponse);

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({ navigateOnSuccess: false }),
      );

      // First generate
      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(result.current.result).not.toBeNull();

      // Then reset
      act(() => {
        result.current.reset();
      });

      expect(result.current.result).toBeNull();
      expect(result.current.error).toBeNull();
    });
  });

  describe("isGenerating state", () => {
    it("should reflect loading state from mutation", () => {
      (
        useGenerateWorkflowFromChatMutation as ReturnType<typeof vi.fn>
      ).mockReturnValue([mockGenerateWorkflow, { isLoading: true }]);

      const { result } = renderHook(() => useGenerateWorkflowFromChat());

      expect(result.current.isGenerating).toBe(true);
    });
  });

  describe("navigation edge cases", () => {
    it("should not navigate if workflow has no id", async () => {
      const responseWithoutId = {
        ...mockSuccessResponse,
        workflow: { ...mockSuccessResponse.workflow, id: undefined },
      };
      mockUnwrap.mockResolvedValue(responseWithoutId);

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({ navigateOnSuccess: true }),
      );

      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should not navigate if workflow is null", async () => {
      const responseWithNullWorkflow = {
        ...mockSuccessResponse,
        workflow: null,
      };
      mockUnwrap.mockResolvedValue(responseWithNullWorkflow);

      const { result } = renderHook(() =>
        useGenerateWorkflowFromChat({ navigateOnSuccess: true }),
      );

      await act(async () => {
        await result.current.generate({ session_id: "session-456" });
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });
});
