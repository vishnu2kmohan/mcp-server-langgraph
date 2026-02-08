/**
 * InboundSamplingModal Tests
 *
 * TDD tests for the inbound sampling modal component.
 * This modal handles server-initiated sampling/createMessage JSON-RPC requests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InboundSamplingModal } from "./InboundSamplingModal";
import type {
  PendingSamplingRequest,
  SamplingResponse as _SamplingResponse,
} from "@/types/mcp";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("InboundSamplingModal", () => {
  const mockOnApprove = vi.fn();
  const mockOnReject = vi.fn();

  const defaultRequest: PendingSamplingRequest = {
    id: 456,
    serverId: "test-server",
    messages: [
      {
        role: "user",
        content: { type: "text", text: "What is the weather today?" },
      },
    ],
    maxTokens: 1000,
    createdAt: Date.now(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders the modal with sampling request", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText(/sampling request/i)).toBeInTheDocument();
    });

    it("displays the message history", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(
        screen.getByText("What is the weather today?"),
      ).toBeInTheDocument();
    });

    it("renders server ID for context", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/test-server/)).toBeInTheDocument();
    });

    it("shows max tokens limit", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/1000/)).toBeInTheDocument();
    });

    it("shows system prompt when present", () => {
      const requestWithSystem: PendingSamplingRequest = {
        ...defaultRequest,
        systemPrompt: "You are a helpful weather assistant.",
      };

      render(
        <TestProvider>
          <InboundSamplingModal
            request={requestWithSystem}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(
        screen.getByText("You are a helpful weather assistant."),
      ).toBeInTheDocument();
    });
  });

  describe("response input", () => {
    it("renders a text input for manual response", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("textbox", { name: /response/i }),
      ).toBeInTheDocument();
    });

    it("allows entering response text", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox", { name: /response/i });
      await user.type(input, "The weather is sunny today.");

      expect(input).toHaveValue("The weather is sunny today.");
    });
  });

  describe("approval flow", () => {
    it("calls onApprove with SamplingResponse on approve", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox", { name: /response/i });
      await user.type(input, "The weather is sunny today.");

      const approveButton = screen.getByRole("button", {
        name: /approve|submit/i,
      });
      await user.click(approveButton);

      await waitFor(() => {
        expect(mockOnApprove).toHaveBeenCalledWith(
          expect.objectContaining({
            role: "assistant",
            content: { type: "text", text: "The weather is sunny today." },
            stopReason: "endTurn",
          }),
        );
      });
    });

    it("disables approve button when response is empty", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      const approveButton = screen.getByRole("button", {
        name: /approve|submit/i,
      });
      expect(approveButton).toBeDisabled();
    });

    it("enables approve button when response is entered", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox", { name: /response/i });
      await user.type(input, "Response text");

      const approveButton = screen.getByRole("button", {
        name: /approve|submit/i,
      });
      expect(approveButton).toBeEnabled();
    });
  });

  describe("rejection flow", () => {
    it("calls onReject when reject button is clicked", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      const rejectButton = screen.getByRole("button", {
        name: /reject|cancel/i,
      });
      await user.click(rejectButton);

      expect(mockOnReject).toHaveBeenCalled();
    });

    it("calls onReject when backdrop is clicked", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      const backdrop = screen.getByTestId("modal-backdrop");
      await user.click(backdrop);

      expect(mockOnReject).toHaveBeenCalled();
    });
  });

  describe("message display", () => {
    it("displays multiple messages in conversation order", () => {
      const multiMessageRequest: PendingSamplingRequest = {
        ...defaultRequest,
        messages: [
          {
            role: "user",
            content: { type: "text", text: "Hello" },
          },
          {
            role: "assistant",
            content: { type: "text", text: "Hi there!" },
          },
          {
            role: "user",
            content: { type: "text", text: "What's the weather?" },
          },
        ],
      };

      render(
        <TestProvider>
          <InboundSamplingModal
            request={multiMessageRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
      expect(screen.getByText("What's the weather?")).toBeInTheDocument();
    });

    it("differentiates user and assistant messages visually", () => {
      const request: PendingSamplingRequest = {
        ...defaultRequest,
        messages: [
          { role: "user", content: { type: "text", text: "User message" } },
          {
            role: "assistant",
            content: { type: "text", text: "Assistant message" },
          },
        ],
      };

      render(
        <TestProvider>
          <InboundSamplingModal
            request={request}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      // User and assistant messages should have different styling
      const userMessage = screen.getByText("User message");
      const assistantMessage = screen.getByText("Assistant message");

      expect(userMessage.closest("[data-role]")).toHaveAttribute(
        "data-role",
        "user",
      );
      expect(assistantMessage.closest("[data-role]")).toHaveAttribute(
        "data-role",
        "assistant",
      );
    });
  });

  describe("model preferences", () => {
    it("displays model hints when present", () => {
      const requestWithPrefs: PendingSamplingRequest = {
        ...defaultRequest,
        modelPreferences: {
          hints: [{ name: "claude-3-opus" }],
          intelligencePriority: 1,
        },
      };

      render(
        <TestProvider>
          <InboundSamplingModal
            request={requestWithPrefs}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/claude-3-opus/i)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has proper dialog role", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has accessible title", () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("heading", { name: /sampling request/i }),
      ).toBeInTheDocument();
    });

    it("focuses response input on mount", async () => {
      render(
        <TestProvider>
          <InboundSamplingModal
            request={defaultRequest}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(
          screen.getByRole("textbox", { name: /response/i }),
        ).toHaveFocus();
      });
    });
  });

  describe("JSON-RPC ID handling", () => {
    it("works with numeric ID", () => {
      const request = { ...defaultRequest, id: 789 };

      render(
        <TestProvider>
          <InboundSamplingModal
            request={request}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("works with string ID", () => {
      const request = { ...defaultRequest, id: "sampling-request-123" };

      render(
        <TestProvider>
          <InboundSamplingModal
            request={request}
            onApprove={mockOnApprove}
            onReject={mockOnReject}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });
});
