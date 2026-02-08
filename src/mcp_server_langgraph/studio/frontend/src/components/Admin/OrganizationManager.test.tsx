/**
 * OrganizationManager Tests
 *
 * Tests for organization management component with CRUD operations.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { OrganizationManager } from "./OrganizationManager";

import { TestProvider } from "@/test-utils";

describe("OrganizationManager", () => {
  const mockOrganizations = [
    {
      id: "org-1",
      name: "Acme Corp",
      slug: "acme-corp",
      memberCount: 25,
      createdAt: new Date("2024-01-15"),
      tier: "enterprise" as const,
    },
    {
      id: "org-2",
      name: "Startup Inc",
      slug: "startup-inc",
      memberCount: 5,
      createdAt: new Date("2024-06-01"),
      tier: "team" as const,
    },
  ];

  const defaultProps = {
    organizations: mockOrganizations,
    isLoading: false,
    onCreate: vi.fn(),
    onUpdate: vi.fn(),
    onDelete: vi.fn(),
    onSelect: vi.fn(),
    selectedOrgId: null as string | null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render organization manager title", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Organizations")).toBeInTheDocument();
    });

    it("should render list of organizations", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
      expect(screen.getByText("Startup Inc")).toBeInTheDocument();
    });

    it("should display member count for each organization", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("25 members")).toBeInTheDocument();
      expect(screen.getByText("5 members")).toBeInTheDocument();
    });

    it("should display organization tier", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Enterprise")).toBeInTheDocument();
      expect(screen.getByText("Team")).toBeInTheDocument();
    });

    it("should render create button", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /create organization/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should call onSelect when organization is clicked", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const orgRow = screen
        .getByText("Acme Corp")
        .closest('[data-testid="org-row"]');
      fireEvent.click(orgRow!);

      expect(defaultProps.onSelect).toHaveBeenCalledWith("org-1");
    });

    it("should highlight selected organization", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} selectedOrgId="org-1" />
        </TestProvider>,
      );

      const orgRow = screen
        .getByText("Acme Corp")
        .closest('[data-testid="org-row"]');
      expect(orgRow).toHaveClass("bg-primary-1");
    });
  });

  describe("Create Organization", () => {
    it("should open create modal when create button is clicked", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(
        screen.getByRole("button", { name: /create organization/i }),
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      // Use heading role to find the modal title specifically
      expect(
        screen.getByRole("heading", { name: "Create Organization" }),
      ).toBeInTheDocument();
    });

    it("should call onCreate with form data", async () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(
        screen.getByRole("button", { name: /create organization/i }),
      );

      const nameInput = screen.getByLabelText("Organization Name");
      fireEvent.change(nameInput, { target: { value: "New Org" } });

      const submitButton = screen.getByRole("button", { name: /create$/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(defaultProps.onCreate).toHaveBeenCalledWith(
          expect.objectContaining({ name: "New Org" }),
        );
      });
    });
  });

  describe("Edit Organization", () => {
    it("should open edit modal when edit button is clicked", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      fireEvent.click(editButtons[0]);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Edit Organization")).toBeInTheDocument();
    });

    it("should pre-populate form with organization data", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      fireEvent.click(editButtons[0]);

      const nameInput = screen.getByLabelText("Organization Name");
      expect(nameInput).toHaveValue("Acme Corp");
    });

    it("should call onUpdate with updated data", async () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      fireEvent.click(editButtons[0]);

      const nameInput = screen.getByLabelText("Organization Name");
      fireEvent.change(nameInput, { target: { value: "Updated Acme" } });

      const saveButton = screen.getByRole("button", { name: /save/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(defaultProps.onUpdate).toHaveBeenCalledWith(
          "org-1",
          expect.objectContaining({ name: "Updated Acme" }),
        );
      });
    });
  });

  describe("Delete Organization", () => {
    it("should show confirmation dialog when delete is clicked", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });

    it("should call onDelete when confirmed", async () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(defaultProps.onDelete).toHaveBeenCalledWith("org-1");
      });
    });

    it("should not call onDelete when cancelled", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      expect(defaultProps.onDelete).not.toHaveBeenCalled();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} isLoading={true} />
        </TestProvider>,
      );

      expect(screen.getByTestId("org-loading")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no organizations", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} organizations={[]} />
        </TestProvider>,
      );

      expect(screen.getByText(/no organizations/i)).toBeInTheDocument();
    });
  });

  describe("Search and Filter", () => {
    it("should render search input", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText(/search organizations/i),
      ).toBeInTheDocument();
    });

    it("should filter organizations by name", () => {
      render(
        <TestProvider>
          <OrganizationManager {...defaultProps} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText(/search organizations/i);
      fireEvent.change(searchInput, { target: { value: "Acme" } });

      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
      expect(screen.queryByText("Startup Inc")).not.toBeInTheDocument();
    });
  });
});
