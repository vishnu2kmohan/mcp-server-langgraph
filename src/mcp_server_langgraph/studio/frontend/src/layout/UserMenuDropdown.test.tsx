/**
 * UserMenuDropdown Tests
 *
 * TDD tests for the user menu dropdown component that provides
 * access to profile, settings, persona switching, and logout.
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UserMenuDropdown } from "./UserMenuDropdown";
import { TestProvider } from "../test-utils";

// =============================================================================
// Test Setup
// =============================================================================

// Mock react-router
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock storage utility
vi.mock("../utils/storage", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    clearAuthTokens: vi.fn(),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// Tests
// =============================================================================

describe("UserMenuDropdown", () => {
  describe("Rendering", () => {
    it("should not render when closed", () => {
      render(
        <TestProvider>
          <UserMenuDropdown isOpen={false} onClose={vi.fn()} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("user-menu-dropdown")).not.toBeInTheDocument();
    });

    it("should render when open", () => {
      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={vi.fn()} />
        </TestProvider>,
      );

      expect(screen.getByTestId("user-menu-dropdown")).toBeInTheDocument();
    });

    it("should display user info section", () => {
      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={vi.fn()} />
        </TestProvider>,
      );

      // Should show current persona
      expect(screen.getByRole("menu")).toBeInTheDocument();
    });

    it("should display menu items (Profile, Settings, Sign Out)", () => {
      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={vi.fn()} />
        </TestProvider>,
      );

      expect(screen.getByTestId("menu-item-profile")).toBeInTheDocument();
      expect(screen.getByTestId("menu-item-settings")).toBeInTheDocument();
      expect(screen.getByTestId("menu-item-logout")).toBeInTheDocument();
    });
  });

  describe("Navigation", () => {
    it("should navigate to settings when Profile is clicked", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={onClose} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("menu-item-profile"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/v2/settings");
      expect(onClose).toHaveBeenCalled();
    });

    it("should navigate to settings when Settings is clicked", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={onClose} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("menu-item-settings"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/v2/settings");
      expect(onClose).toHaveBeenCalled();
    });

    it("should navigate to login and clear tokens when Sign Out is clicked", async () => {
      const { clearAuthTokens } = await import("../utils/storage");
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={onClose} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("menu-item-logout"));

      expect(clearAuthTokens).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith("/login");
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Persona Switcher", () => {
    it("should display persona switcher button", () => {
      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={vi.fn()} />
        </TestProvider>,
      );

      expect(screen.getByTestId("persona-switcher-button")).toBeInTheDocument();
      expect(screen.getByText("Switch Persona")).toBeInTheDocument();
    });

    it("should toggle persona options when switcher is clicked", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={vi.fn()} />
        </TestProvider>,
      );

      // Initially, persona options should not be visible
      expect(screen.queryByTestId("persona-option-admin")).not.toBeInTheDocument();

      // Click to show options
      await user.click(screen.getByTestId("persona-switcher-button"));

      // Now options should be visible
      expect(screen.getByTestId("persona-option-admin")).toBeInTheDocument();
      expect(screen.getByTestId("persona-option-auditor")).toBeInTheDocument();
      expect(screen.getByTestId("persona-option-alice-builder")).toBeInTheDocument();
    });

    it("should navigate to persona-specific route when persona is selected", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={onClose} />
        </TestProvider>,
      );

      // Open persona switcher
      await user.click(screen.getByTestId("persona-switcher-button"));

      // Select admin persona
      await user.click(screen.getByTestId("persona-option-admin"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/v2/admin");
      expect(onClose).toHaveBeenCalled();
    });

    it("should navigate to correct default view for each persona", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      const expectedRoutes: Record<string, string> = {
        admin: "/studio/v2/admin",
        "security-admin": "/studio/v2/compliance",
        auditor: "/studio/v2/admin/audit-logs",
        "alice-builder": "/studio/v2/chat",
        "alice-analyst": "/studio/v2/observability",
        "alice-devops": "/studio/v2/connections",
        "compliance-officer": "/studio/v2/compliance",
        bob: "/studio/v2/chat",
      };

      for (const [personaId, expectedRoute] of Object.entries(expectedRoutes)) {
        mockNavigate.mockClear();
        onClose.mockClear();

        const { unmount } = render(
          <TestProvider>
            <UserMenuDropdown isOpen={true} onClose={onClose} />
          </TestProvider>,
        );

        await user.click(screen.getByTestId("persona-switcher-button"));
        await user.click(screen.getByTestId(`persona-option-${personaId}`));

        expect(mockNavigate).toHaveBeenCalledWith(expectedRoute);

        unmount();
      }
    });
  });

  describe("Keyboard Navigation", () => {
    it("should close dropdown when Escape key is pressed", async () => {
      const onClose = vi.fn();

      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={onClose} />
        </TestProvider>,
      );

      fireEvent.keyDown(document, { key: "Escape" });

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Click Outside", () => {
    it("should close dropdown when clicking outside with anchorRef provided", async () => {
      const onClose = vi.fn();

      // Create a wrapper component that provides an anchorRef
      function TestWrapper() {
        const anchorRef = React.useRef<HTMLButtonElement>(null);
        return (
          <>
            <button ref={anchorRef} data-testid="anchor-button">
              Open Menu
            </button>
            <div data-testid="outside-element">Outside</div>
            <UserMenuDropdown
              isOpen={true}
              onClose={onClose}
              anchorRef={anchorRef}
            />
          </>
        );
      }

      render(
        <TestProvider>
          <TestWrapper />
        </TestProvider>,
      );

      // Click on an element outside both the dropdown and anchor
      fireEvent.mouseDown(screen.getByTestId("outside-element"));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });

    it("should NOT close dropdown when clicking inside the anchor", async () => {
      const onClose = vi.fn();

      function TestWrapper() {
        const anchorRef = React.useRef<HTMLButtonElement>(null);
        return (
          <>
            <button ref={anchorRef} data-testid="anchor-button">
              Open Menu
            </button>
            <UserMenuDropdown
              isOpen={true}
              onClose={onClose}
              anchorRef={anchorRef}
            />
          </>
        );
      }

      render(
        <TestProvider>
          <TestWrapper />
        </TestProvider>,
      );

      // Click on the anchor itself should NOT close
      fireEvent.mouseDown(screen.getByTestId("anchor-button"));

      // Wait a bit and verify onClose was NOT called
      await new Promise((r) => setTimeout(r, 100));
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA attributes", () => {
      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={vi.fn()} />
        </TestProvider>,
      );

      const menu = screen.getByRole("menu");
      expect(menu).toHaveAttribute("aria-label", "User menu");
    });

    it("should have menu item role on all buttons", () => {
      render(
        <TestProvider>
          <UserMenuDropdown isOpen={true} onClose={vi.fn()} />
        </TestProvider>,
      );

      const menuItems = screen.getAllByRole("menuitem");
      // Should include: persona switcher, Profile, Settings, Sign Out
      expect(menuItems.length).toBeGreaterThanOrEqual(4);
    });
  });
});
