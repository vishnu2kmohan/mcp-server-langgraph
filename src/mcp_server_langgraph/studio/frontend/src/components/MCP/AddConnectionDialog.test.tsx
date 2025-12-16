/**
 * AddConnectionDialog Tests
 *
 * TDD tests for the MCP connection dialog modal.
 * Tests cover:
 * - Dialog open/close behavior
 * - Form fields: name, description, URL, transport, auth type
 * - Transport-specific fields (stdio: command, args, env)
 * - Auth-specific fields (oauth2, api_key)
 * - Form validation
 * - Submit behavior
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
// biome-ignore lint/correctness/noUnusedImports: waitFor is used in async form submission tests
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AddConnectionDialog } from "./AddConnectionDialog";

describe("AddConnectionDialog", () => {
  const mockOnClose = vi.fn();
  const mockOnSubmit = vi.fn();

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onSubmit: mockOnSubmit,
    isLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Dialog Behavior", () => {
    it("should render when isOpen is true", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Add MCP Connection")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(<AddConnectionDialog {...defaultProps} isOpen={false} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should call onClose when close button is clicked", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const closeButton = screen.getByRole("button", { name: /close/i });
      await userEvent.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("should call onClose when Cancel button is clicked", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await userEvent.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("Form Fields", () => {
    it("should have name input field", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    });

    it("should have description textarea field", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    });

    it("should have URL input field", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByLabelText(/url/i)).toBeInTheDocument();
    });

    it("should have transport protocol selector", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByLabelText(/transport/i)).toBeInTheDocument();
    });

    it("should have authentication type selector", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByLabelText(/authentication/i)).toBeInTheDocument();
    });
  });

  describe("Transport Protocol Selection", () => {
    it("should default to Streamable HTTP transport", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const transportSelect = screen.getByLabelText(
        /transport/i,
      ) as HTMLSelectElement;
      expect(transportSelect.value).toBe("streamable_http");
    });

    it("should have Streamable HTTP option", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByText(/streamable http/i)).toBeInTheDocument();
    });

    it("should have stdio option", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(
        screen.getByRole("option", { name: /stdio/i }),
      ).toBeInTheDocument();
    });

    it("should show command field when stdio transport is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const transportSelect = screen.getByLabelText(/transport/i);
      await userEvent.selectOptions(transportSelect, "stdio");

      expect(screen.getByLabelText(/command/i)).toBeInTheDocument();
    });

    it("should show args field when stdio transport is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const transportSelect = screen.getByLabelText(/transport/i);
      await userEvent.selectOptions(transportSelect, "stdio");

      expect(screen.getByLabelText(/arguments/i)).toBeInTheDocument();
    });

    it("should hide stdio fields when streamable_http is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      // Initially should not show command field
      expect(screen.queryByLabelText(/command/i)).not.toBeInTheDocument();
    });
  });

  describe("Authentication Type Selection", () => {
    it("should default to no authentication", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const authSelect = screen.getByLabelText(
        /authentication/i,
      ) as HTMLSelectElement;
      expect(authSelect.value).toBe("none");
    });

    it("should have None option", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByRole("option", { name: /none/i })).toBeInTheDocument();
    });

    it("should have API Key option", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(
        screen.getByRole("option", { name: /api key/i }),
      ).toBeInTheDocument();
    });

    it("should have OAuth2 option", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(
        screen.getByRole("option", { name: /oauth2/i }),
      ).toBeInTheDocument();
    });

    it("should show API key field when api_key auth is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const authSelect = screen.getByLabelText(/authentication/i);
      await userEvent.selectOptions(authSelect, "api_key");

      expect(screen.getByLabelText(/api key/i)).toBeInTheDocument();
    });

    it("should show OAuth2 client ID field when oauth2 auth is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const authSelect = screen.getByLabelText(/authentication/i);
      await userEvent.selectOptions(authSelect, "oauth2");

      expect(screen.getByLabelText(/client id/i)).toBeInTheDocument();
    });

    it("should show OAuth2 scopes field when oauth2 auth is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const authSelect = screen.getByLabelText(/authentication/i);
      await userEvent.selectOptions(authSelect, "oauth2");

      expect(screen.getByLabelText(/scopes/i)).toBeInTheDocument();
    });
  });

  describe("Form Validation", () => {
    it("should require name field", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("should require URL field", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, "Test Server");

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      expect(screen.getByText(/url is required/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("should require command field for stdio transport", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, "Test Server");

      const urlInput = screen.getByLabelText(/url/i);
      await userEvent.type(urlInput, "stdio://local");

      const transportSelect = screen.getByLabelText(/transport/i);
      await userEvent.selectOptions(transportSelect, "stdio");

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      expect(screen.getByText(/command is required/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("should validate URL format for streamable_http transport", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, "Test Server");

      const urlInput = screen.getByLabelText(/url/i);
      await userEvent.type(urlInput, "not-a-valid-url");

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      expect(screen.getByText(/valid url/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe("Form Submission", () => {
    it("should call onSubmit with form data when valid", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, "Zapier MCP");

      const descInput = screen.getByLabelText(/description/i);
      await userEvent.type(descInput, "Zapier MCP integration");

      const urlInput = screen.getByLabelText(/url/i);
      await userEvent.type(urlInput, "https://mcp.zapier.com");

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1);
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "Zapier MCP",
            description: "Zapier MCP integration",
            url: "https://mcp.zapier.com",
            transport: "streamable_http",
            auth_type: "none",
          }),
        );
      });
    });

    it("should include stdio fields when stdio transport is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, "Local Python Server");

      const urlInput = screen.getByLabelText(/url/i);
      await userEvent.type(urlInput, "stdio://python-mcp");

      const transportSelect = screen.getByLabelText(/transport/i);
      await userEvent.selectOptions(transportSelect, "stdio");

      const commandInput = screen.getByLabelText(/command/i);
      await userEvent.type(commandInput, "python");

      const argsInput = screen.getByLabelText(/arguments/i);
      await userEvent.type(argsInput, "-m mcp_server");

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "Local Python Server",
            transport: "stdio",
            command: "python",
            args: ["-m", "mcp_server"],
          }),
        );
      });
    });

    it("should include api_key when api_key auth is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, "API Server");

      const urlInput = screen.getByLabelText(/url/i);
      await userEvent.type(urlInput, "https://api.example.com");

      const authSelect = screen.getByLabelText(/authentication/i);
      await userEvent.selectOptions(authSelect, "api_key");

      const apiKeyInput = screen.getByLabelText(/api key/i);
      await userEvent.type(apiKeyInput, "sk-test-12345");

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            auth_type: "api_key",
            api_key: "sk-test-12345",
          }),
        );
      });
    });

    it("should include oauth2 config when oauth2 auth is selected", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await userEvent.type(nameInput, "OAuth Server");

      const urlInput = screen.getByLabelText(/url/i);
      await userEvent.type(urlInput, "https://oauth.example.com");

      const authSelect = screen.getByLabelText(/authentication/i);
      await userEvent.selectOptions(authSelect, "oauth2");

      const clientIdInput = screen.getByLabelText(/client id/i);
      await userEvent.type(clientIdInput, "client-123");

      const scopesInput = screen.getByLabelText(/scopes/i);
      await userEvent.type(scopesInput, "read write");

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            auth_type: "oauth2",
            oauth2_client_id: "client-123",
            oauth2_scopes: ["read", "write"],
          }),
        );
      });
    });
  });

  describe("Loading State", () => {
    it("should disable submit button when loading", () => {
      render(<AddConnectionDialog {...defaultProps} isLoading={true} />);

      const submitButton = screen.getByRole("button", { name: /add/i });
      expect(submitButton).toBeDisabled();
    });

    it("should show loading indicator when loading", () => {
      render(<AddConnectionDialog {...defaultProps} isLoading={true} />);

      expect(
        screen.getByRole("button", { name: /adding/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible dialog role", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have labeled form fields", () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      expect(nameInput).toHaveAttribute("id");
    });

    it("should associate error messages with fields", async () => {
      render(<AddConnectionDialog {...defaultProps} />);

      const submitButton = screen.getByRole("button", { name: /add/i });
      await userEvent.click(submitButton);

      const nameInput = screen.getByLabelText(/name/i);
      expect(nameInput).toHaveAttribute("aria-invalid", "true");
    });
  });
});
