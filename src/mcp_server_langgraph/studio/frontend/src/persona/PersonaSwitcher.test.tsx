/**
 * PersonaSwitcher Tests - Phase 2
 *
 * Tests for persona/sub-persona selection component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PersonaSwitcher, type Persona } from "./PersonaSwitcher";

// =============================================================================
// Test Data
// =============================================================================

const mockPersonas: Persona[] = [
  {
    id: "admin",
    name: "Admin",
    role: "admin",
    description: "Full system access",
    icon: "shield",
    color: "red",
  },
  {
    id: "security-admin",
    name: "Security Admin",
    role: "admin",
    description: "Security-focused administration",
    icon: "shield-alert",
    color: "orange",
    parentId: "admin",
  },
  {
    id: "auditor",
    name: "Auditor",
    role: "admin",
    description: "Audit and compliance",
    icon: "clipboard-check",
    color: "yellow",
    parentId: "admin",
  },
  {
    id: "alice-builder",
    name: "Alice Builder",
    role: "developer",
    description: "Workflow development",
    icon: "code",
    color: "blue",
  },
  {
    id: "alice-analyst",
    name: "Alice Analyst",
    role: "developer",
    description: "Data analysis",
    icon: "bar-chart",
    color: "purple",
    parentId: "alice-builder",
  },
  {
    id: "bob",
    name: "Bob",
    role: "user",
    description: "Standard user access",
    icon: "user",
    color: "green",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("PersonaSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render switcher container", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      expect(screen.getByTestId("persona-switcher")).toBeInTheDocument();
    });

    it("should display current persona name", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      expect(screen.getByText("Admin")).toBeInTheDocument();
    });

    it("should show dropdown trigger button", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      expect(screen.getByTestId("persona-trigger")).toBeInTheDocument();
    });
  });

  describe("Dropdown", () => {
    it("should open dropdown when trigger clicked", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      expect(screen.getByTestId("persona-dropdown")).toBeInTheDocument();
    });

    it("should display all personas in dropdown", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      expect(screen.getByText("Security Admin")).toBeInTheDocument();
      expect(screen.getByText("Alice Builder")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
    });

    it("should close dropdown when clicking outside", () => {
      render(
        <div>
          <div data-testid="outside">Outside</div>
          <PersonaSwitcher
            personas={mockPersonas}
            currentPersona={mockPersonas[0]}
            onSwitch={() => {}}
          />
        </div>,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      expect(screen.getByTestId("persona-dropdown")).toBeInTheDocument();
      fireEvent.mouseDown(screen.getByTestId("outside"));
      expect(screen.queryByTestId("persona-dropdown")).not.toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should call onSwitch when persona selected", () => {
      const onSwitch = vi.fn();
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={onSwitch}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      fireEvent.click(screen.getByText("Bob"));
      expect(onSwitch).toHaveBeenCalledWith(mockPersonas[5]);
    });

    it("should highlight current persona in dropdown", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      const adminItem = screen.getByTestId("persona-item-admin");
      expect(adminItem).toHaveClass("selected");
    });

    it("should close dropdown after selection", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      fireEvent.click(screen.getByText("Bob"));
      expect(screen.queryByTestId("persona-dropdown")).not.toBeInTheDocument();
    });
  });

  describe("Sub-personas", () => {
    it("should show sub-persona indicator for personas with children", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      // Admin should have sub-personas (Security Admin, Auditor)
      const adminItem = screen.getByTestId("persona-item-admin");
      expect(adminItem).toHaveAttribute("data-has-children", "true");
    });

    it("should indent sub-personas in dropdown", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      const subPersonaItem = screen.getByTestId("persona-item-security-admin");
      expect(subPersonaItem).toHaveClass("sub-persona");
    });
  });

  describe("Role Grouping", () => {
    it("should group personas by role", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
          groupByRole
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      expect(screen.getByTestId("role-group-admin")).toBeInTheDocument();
      expect(screen.getByTestId("role-group-developer")).toBeInTheDocument();
      expect(screen.getByTestId("role-group-user")).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("should close dropdown on Escape", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      fireEvent.keyDown(screen.getByTestId("persona-dropdown"), {
        key: "Escape",
      });
      expect(screen.queryByTestId("persona-dropdown")).not.toBeInTheDocument();
    });

    it("should navigate with arrow keys", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      const dropdown = screen.getByTestId("persona-dropdown");
      // First arrow down focuses the first item (index 0), then second focuses index 1
      fireEvent.keyDown(dropdown, { key: "ArrowDown" });
      fireEvent.keyDown(dropdown, { key: "ArrowDown" });
      // Second item should now be focused
      expect(screen.getByTestId("persona-item-security-admin")).toHaveClass(
        "focused",
      );
    });
  });

  describe("Accessibility", () => {
    it("should have accessible trigger button", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      expect(
        screen.getByRole("button", { name: /Admin/i }),
      ).toBeInTheDocument();
    });

    it("should have listbox role on dropdown", () => {
      render(
        <PersonaSwitcher
          personas={mockPersonas}
          currentPersona={mockPersonas[0]}
          onSwitch={() => {}}
        />,
      );
      fireEvent.click(screen.getByTestId("persona-trigger"));
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });
  });
});
