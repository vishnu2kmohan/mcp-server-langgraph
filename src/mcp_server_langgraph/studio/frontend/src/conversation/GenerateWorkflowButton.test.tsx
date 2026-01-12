/**
 * GenerateWorkflowButton Component Tests
 *
 * Tests for the button that generates workflows from chat sessions.
 * Uses centralized /from-chat endpoint (NO JS DUPLICATION).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock react-router navigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the hooks
vi.mock("../hooks/useGenerateWorkflowFromChat", () => ({
  useGenerateWorkflowFromChat: vi.fn(),
}));

vi.mock("../api", () => ({
  useGetFeatureFlagsQuery: vi.fn(),
}));

import { useGenerateWorkflowFromChat } from "../hooks/useGenerateWorkflowFromChat";
import { useGetFeatureFlagsQuery } from "../api";
import { GenerateWorkflowButton } from "./GenerateWorkflowButton";

describe("GenerateWorkflowButton", () => {
  const mockGenerate = vi.fn();
  const mockReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock for useGenerateWorkflowFromChat
    (useGenerateWorkflowFromChat as ReturnType<typeof vi.fn>).mockReturnValue({
      generate: mockGenerate,
      isGenerating: false,
      result: null,
      error: null,
      reset: mockReset,
    });

    // Default mock for feature flags - feature enabled
    (useGetFeatureFlagsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { workflow_from_chat: true },
      isLoading: false,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  describe("rendering", () => {
    it("should render the button when feature is enabled", () => {
      render(<GenerateWorkflowButton sessionId="session-123" />);

      const button = screen.getByTestId("generate-workflow-button");
      expect(button).toBeInTheDocument();
    });

    it("should not render when feature is disabled", () => {
      (useGetFeatureFlagsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: { workflow_from_chat: false },
        isLoading: false,
      });

      render(<GenerateWorkflowButton sessionId="session-123" />);

      expect(
        screen.queryByTestId("generate-workflow-button"),
      ).not.toBeInTheDocument();
    });

    it("should show tooltip with description", async () => {
      render(<GenerateWorkflowButton sessionId="session-123" />);

      const button = screen.getByTestId("generate-workflow-button");
      expect(button).toHaveAttribute(
        "aria-label",
        "Generate workflow from this chat",
      );
    });

    it("should show loading state when generating", () => {
      (useGenerateWorkflowFromChat as ReturnType<typeof vi.fn>).mockReturnValue(
        {
          generate: mockGenerate,
          isGenerating: true,
          result: null,
          error: null,
          reset: mockReset,
        },
      );

      render(<GenerateWorkflowButton sessionId="session-123" />);

      const button = screen.getByTestId("generate-workflow-button");
      expect(button).toBeDisabled();
    });
  });

  describe("interaction", () => {
    it("should call generate when clicked", async () => {
      const user = userEvent.setup();
      mockGenerate.mockResolvedValue({
        workflow: { id: "wf-123" },
        confidence: 0.85,
        suggestions: [],
        prompt_metadata: {
          name: "workflow_generator",
          version: "v1",
          hash: "abc",
          model: "claude-opus-4-5",
        },
      });

      render(<GenerateWorkflowButton sessionId="session-123" />);

      const button = screen.getByTestId("generate-workflow-button");
      await user.click(button);

      expect(mockGenerate).toHaveBeenCalledWith({
        session_id: "session-123",
      });
    });

    it("should be disabled during generation", () => {
      (useGenerateWorkflowFromChat as ReturnType<typeof vi.fn>).mockReturnValue(
        {
          generate: mockGenerate,
          isGenerating: true,
          result: null,
          error: null,
          reset: mockReset,
        },
      );

      render(<GenerateWorkflowButton sessionId="session-123" />);

      const button = screen.getByTestId("generate-workflow-button");
      expect(button).toBeDisabled();
    });

    it("should be disabled when no sessionId provided", () => {
      render(<GenerateWorkflowButton sessionId="" />);

      const button = screen.getByTestId("generate-workflow-button");
      expect(button).toBeDisabled();
    });
  });

  describe("error handling", () => {
    it("should show error state when generation fails", () => {
      (useGenerateWorkflowFromChat as ReturnType<typeof vi.fn>).mockReturnValue(
        {
          generate: mockGenerate,
          isGenerating: false,
          result: null,
          error: "Generation failed",
          reset: mockReset,
        },
      );

      render(<GenerateWorkflowButton sessionId="session-123" />);

      // Button should show error styling
      const button = screen.getByTestId("generate-workflow-button");
      expect(button).toHaveAttribute("data-error", "true");
    });
  });

  describe("callbacks", () => {
    it("should pass onSuccess callback to the hook", () => {
      const onSuccess = vi.fn();

      render(
        <GenerateWorkflowButton
          sessionId="session-123"
          onSuccess={onSuccess}
        />,
      );

      // Verify the hook was called with navigateOnSuccess and the callback
      expect(useGenerateWorkflowFromChat).toHaveBeenCalledWith(
        expect.objectContaining({
          navigateOnSuccess: true,
          onSuccess,
        }),
      );
    });

    it("should pass onError callback to the hook", () => {
      const onError = vi.fn();

      render(
        <GenerateWorkflowButton sessionId="session-123" onError={onError} />,
      );

      // Verify the hook was called with the error callback
      expect(useGenerateWorkflowFromChat).toHaveBeenCalledWith(
        expect.objectContaining({
          onError,
        }),
      );
    });
  });
});
