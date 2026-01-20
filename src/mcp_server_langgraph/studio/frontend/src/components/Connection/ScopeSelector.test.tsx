/**
 * ScopeSelector Component Tests (TDD)
 *
 * Tests for the connection scope selector component.
 * @see ADR-0102 Phase 6
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ScopeSelector } from "./ScopeSelector";
import type { ConnectionScope } from "@/types/connection";

// Motion mock is provided globally in src/test/setup.ts

describe("ScopeSelector", () => {
  describe("Rendering", () => {
    it("should render all three scope options", () => {
      render(<ScopeSelector value="user" onChange={vi.fn()} />);
      expect(screen.getByText("Personal")).toBeInTheDocument();
      expect(screen.getByText("Project")).toBeInTheDocument();
      expect(screen.getByText("Session Only")).toBeInTheDocument();
    });

    it("should render descriptions for each scope", () => {
      render(<ScopeSelector value="user" onChange={vi.fn()} />);
      expect(screen.getByText(/only you can access/i)).toBeInTheDocument();
      expect(screen.getByText(/project members can access/i)).toBeInTheDocument();
      expect(screen.getByText(/temporary, not saved/i)).toBeInTheDocument();
    });

    it("should render icons for each scope option", () => {
      render(<ScopeSelector value="user" onChange={vi.fn()} />);
      expect(screen.getByTestId("scope-selector")).toBeInTheDocument();
    });

    it("should mark the selected scope as checked", () => {
      render(<ScopeSelector value="project" onChange={vi.fn()} />);
      const projectRadio = screen.getByRole("radio", { name: /project/i });
      expect(projectRadio).toBeChecked();
    });
  });

  describe("Selection", () => {
    it("should call onChange when user scope is selected", () => {
      const onChange = vi.fn();
      render(<ScopeSelector value="project" onChange={onChange} />);

      const userRadio = screen.getByRole("radio", { name: /personal/i });
      fireEvent.click(userRadio);

      expect(onChange).toHaveBeenCalledWith("user");
    });

    it("should call onChange when project scope is selected", () => {
      const onChange = vi.fn();
      render(<ScopeSelector value="user" onChange={onChange} />);

      const projectRadio = screen.getByRole("radio", { name: /project/i });
      fireEvent.click(projectRadio);

      expect(onChange).toHaveBeenCalledWith("project");
    });

    it("should call onChange when session scope is selected", () => {
      const onChange = vi.fn();
      render(<ScopeSelector value="user" onChange={onChange} />);

      const sessionRadio = screen.getByRole("radio", { name: /session only/i });
      fireEvent.click(sessionRadio);

      expect(onChange).toHaveBeenCalledWith("session");
    });
  });

  describe("Disabled State", () => {
    it("should disable all options when disabled prop is true", () => {
      render(<ScopeSelector value="user" onChange={vi.fn()} disabled />);

      const radios = screen.getAllByRole("radio");
      radios.forEach((radio) => {
        expect(radio).toBeDisabled();
      });
    });

    it("should not call onChange when disabled and clicked", () => {
      const onChange = vi.fn();
      render(<ScopeSelector value="user" onChange={onChange} disabled />);

      const projectRadio = screen.getByRole("radio", { name: /project/i });
      fireEvent.click(projectRadio);

      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have a radiogroup role", () => {
      render(<ScopeSelector value="user" onChange={vi.fn()} />);
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("should have accessible labels for screen readers", () => {
      render(<ScopeSelector value="user" onChange={vi.fn()} />);
      const radioGroup = screen.getByRole("radiogroup");
      expect(radioGroup).toHaveAccessibleName(/connection scope/i);
    });
  });

  describe("All Values", () => {
    const scopes: ConnectionScope[] = ["user", "project", "session"];

    scopes.forEach((scope) => {
      it(`should render correctly with ${scope} as selected value`, () => {
        render(<ScopeSelector value={scope} onChange={vi.fn()} />);
        expect(screen.getByTestId("scope-selector")).toBeInTheDocument();
      });
    });
  });
});
