/**
 * UserManager Tests
 *
 * Tests for user management component with role assignments.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UserManager } from "./UserManager";

describe("UserManager", () => {
  const mockUsers = [
    {
      id: "user-1",
      email: "admin@example.com",
      name: "Admin User",
      roles: ["admin", "developer"],
      organizationId: "org-1",
      lastLogin: new Date("2024-12-10T10:30:00"),
      isActive: true,
    },
    {
      id: "user-2",
      email: "dev@example.com",
      name: "Developer User",
      roles: ["developer"],
      organizationId: "org-1",
      lastLogin: new Date("2024-12-11T14:00:00"),
      isActive: true,
    },
    {
      id: "user-3",
      email: "inactive@example.com",
      name: "Inactive User",
      roles: ["user"],
      organizationId: "org-1",
      lastLogin: new Date("2024-01-01T00:00:00"),
      isActive: false,
    },
  ];

  const defaultProps = {
    users: mockUsers,
    isLoading: false,
    onUpdateRoles: vi.fn(),
    onDeactivate: vi.fn(),
    onActivate: vi.fn(),
    onInvite: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render user manager title", () => {
      render(<UserManager {...defaultProps} />);

      expect(screen.getByText("User Management")).toBeInTheDocument();
    });

    it("should render list of users", () => {
      render(<UserManager {...defaultProps} />);

      expect(screen.getByText("Admin User")).toBeInTheDocument();
      expect(screen.getByText("Developer User")).toBeInTheDocument();
      expect(screen.getByText("Inactive User")).toBeInTheDocument();
    });

    it("should display user emails", () => {
      render(<UserManager {...defaultProps} />);

      expect(screen.getByText("admin@example.com")).toBeInTheDocument();
      expect(screen.getByText("dev@example.com")).toBeInTheDocument();
    });

    it("should display user roles as badges", () => {
      render(<UserManager {...defaultProps} />);

      // Admin user has admin and developer roles
      const adminBadges = screen.getAllByText("admin");
      expect(adminBadges.length).toBeGreaterThan(0);
    });

    it("should show active/inactive status", () => {
      render(<UserManager {...defaultProps} />);

      const activeIndicators = screen.getAllByTestId("status-active");
      const inactiveIndicators = screen.getAllByTestId("status-inactive");

      expect(activeIndicators.length).toBe(2);
      expect(inactiveIndicators.length).toBe(1);
    });

    it("should render invite button", () => {
      render(<UserManager {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /invite user/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Role Management", () => {
    it("should open role editor when manage roles is clicked", () => {
      render(<UserManager {...defaultProps} />);

      const manageRolesButtons = screen.getAllByRole("button", {
        name: /manage roles/i,
      });
      fireEvent.click(manageRolesButtons[0]);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      // Use heading role to find modal title specifically
      expect(
        screen.getByRole("heading", { name: "Manage Roles" }),
      ).toBeInTheDocument();
    });

    it("should display available roles in editor", () => {
      render(<UserManager {...defaultProps} />);

      const manageRolesButtons = screen.getAllByRole("button", {
        name: /manage roles/i,
      });
      fireEvent.click(manageRolesButtons[1]); // Developer user

      expect(screen.getByLabelText("admin")).toBeInTheDocument();
      expect(screen.getByLabelText("developer")).toBeInTheDocument();
      expect(screen.getByLabelText("user")).toBeInTheDocument();
    });

    it("should call onUpdateRoles when roles are updated", async () => {
      render(<UserManager {...defaultProps} />);

      const manageRolesButtons = screen.getAllByRole("button", {
        name: /manage roles/i,
      });
      fireEvent.click(manageRolesButtons[1]); // Developer user

      // Add admin role
      const adminCheckbox = screen.getByLabelText("admin");
      fireEvent.click(adminCheckbox);

      const saveButton = screen.getByRole("button", { name: /save roles/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(defaultProps.onUpdateRoles).toHaveBeenCalledWith(
          "user-2",
          expect.arrayContaining(["admin", "developer"]),
        );
      });
    });
  });

  describe("User Activation", () => {
    it("should call onDeactivate for active users", async () => {
      render(<UserManager {...defaultProps} />);

      const deactivateButtons = screen.getAllByRole("button", {
        name: /deactivate/i,
      });
      fireEvent.click(deactivateButtons[0]);

      // Confirm deactivation
      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(defaultProps.onDeactivate).toHaveBeenCalledWith("user-1");
      });
    });

    it("should call onActivate for inactive users", async () => {
      render(<UserManager {...defaultProps} />);

      // Use exact match to avoid matching "Deactivate" buttons
      const activateButton = screen.getByRole("button", { name: "Activate" });
      fireEvent.click(activateButton);

      await waitFor(() => {
        expect(defaultProps.onActivate).toHaveBeenCalledWith("user-3");
      });
    });
  });

  describe("Invite User", () => {
    it("should open invite modal when invite button is clicked", () => {
      render(<UserManager {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /invite user/i }));

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      // Use heading role to find modal title specifically
      expect(
        screen.getByRole("heading", { name: "Invite User" }),
      ).toBeInTheDocument();
    });

    it("should call onInvite with email and roles", async () => {
      render(<UserManager {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /invite user/i }));

      const emailInput = screen.getByLabelText("Email");
      fireEvent.change(emailInput, { target: { value: "new@example.com" } });

      const developerCheckbox = screen.getByLabelText("developer");
      fireEvent.click(developerCheckbox);

      const inviteButton = screen.getByRole("button", { name: /send invite/i });
      fireEvent.click(inviteButton);

      await waitFor(() => {
        expect(defaultProps.onInvite).toHaveBeenCalledWith(
          "new@example.com",
          expect.arrayContaining(["developer"]),
        );
      });
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(<UserManager {...defaultProps} isLoading={true} />);

      expect(screen.getByTestId("user-loading")).toBeInTheDocument();
    });
  });

  describe("Search", () => {
    it("should render search input", () => {
      render(<UserManager {...defaultProps} />);

      expect(screen.getByPlaceholderText(/search users/i)).toBeInTheDocument();
    });

    it("should filter users by name or email", () => {
      render(<UserManager {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search users/i);
      fireEvent.change(searchInput, { target: { value: "admin" } });

      expect(screen.getByText("Admin User")).toBeInTheDocument();
      expect(screen.queryByText("Developer User")).not.toBeInTheDocument();
    });
  });

  describe("Last Login", () => {
    it("should display last login time", () => {
      render(<UserManager {...defaultProps} />);

      // Check that dates are displayed in some format
      expect(screen.getByText(/12\/10\/2024/)).toBeInTheDocument();
    });
  });
});
