/**
 * InboundElicitationModal Tests
 *
 * TDD tests for the inbound elicitation modal component.
 * This modal handles server-initiated elicitation JSON-RPC requests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InboundElicitationModal } from "./InboundElicitationModal";
import type {
  PendingElicitation,
  JSONRPCError as _JSONRPCError,
} from "@/types/mcp";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("InboundElicitationModal", () => {
  const mockOnRespond = vi.fn();
  const mockOnCancel = vi.fn();

  const defaultRequest: PendingElicitation = {
    id: 123,
    serverId: "test-server",
    message: "Please provide your name",
    requestedSchema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Your full name" },
      },
      required: ["name"],
    },
    createdAt: Date.now(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders the modal with server message", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Please provide your name")).toBeInTheDocument();
    });

    it("renders form fields from schema", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    });

    it("renders server ID for context", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/test-server/)).toBeInTheDocument();
    });

    it("marks required fields appropriately", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const nameInput = screen.getByLabelText(/name/i);
      expect(nameInput).toHaveAttribute("required");
    });
  });

  describe("form submission", () => {
    it("calls onRespond with form data on submit", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, "John Doe");

      const submitButton = screen.getByRole("button", {
        name: /submit|respond/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnRespond).toHaveBeenCalledWith({ name: "John Doe" });
      });
    });

    it("disables submit button when required fields are empty", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const submitButton = screen.getByRole("button", {
        name: /submit|respond/i,
      });
      expect(submitButton).toBeDisabled();
    });

    it("enables submit button when required fields are filled", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, "John Doe");

      const submitButton = screen.getByRole("button", {
        name: /submit|respond/i,
      });
      expect(submitButton).toBeEnabled();
    });
  });

  describe("cancellation", () => {
    it("calls onCancel when cancel button is clicked", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const cancelButton = screen.getByRole("button", {
        name: /cancel|decline/i,
      });
      await user.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });

    it("calls onCancel when backdrop is clicked", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const backdrop = screen.getByTestId("modal-backdrop");
      await user.click(backdrop);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe("accessibility", () => {
    it("has proper dialog role", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has accessible title", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("heading", { name: /elicitation request/i }),
      ).toBeInTheDocument();
    });

    it("focuses first input on mount", async () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toHaveFocus();
      });
    });
  });

  describe("schema types", () => {
    it("renders text input for string type", () => {
      render(
        <TestProvider>
          <InboundElicitationModal
            request={defaultRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const input = screen.getByLabelText(/name/i);
      expect(input).toHaveAttribute("type", "text");
    });

    it("renders number input for number type", () => {
      const numberRequest: PendingElicitation = {
        ...defaultRequest,
        requestedSchema: {
          type: "object",
          properties: {
            age: { type: "number", description: "Your age" },
          },
        },
      };

      render(
        <TestProvider>
          <InboundElicitationModal
            request={numberRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const input = screen.getByLabelText(/age/i);
      expect(input).toHaveAttribute("type", "number");
    });

    it("renders checkbox for boolean type", () => {
      const booleanRequest: PendingElicitation = {
        ...defaultRequest,
        requestedSchema: {
          type: "object",
          properties: {
            agree: { type: "boolean", description: "Do you agree?" },
          },
        },
      };

      render(
        <TestProvider>
          <InboundElicitationModal
            request={booleanRequest}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toBeInTheDocument();
    });
  });

  describe("JSON-RPC ID handling", () => {
    it("works with numeric ID", () => {
      const request = { ...defaultRequest, id: 123 };

      render(
        <TestProvider>
          <InboundElicitationModal
            request={request}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("works with string ID", () => {
      const request = { ...defaultRequest, id: "request-456" };

      render(
        <TestProvider>
          <InboundElicitationModal
            request={request}
            onRespond={mockOnRespond}
            onCancel={mockOnCancel}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });
});
