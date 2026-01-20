/**
 * ScopeBadge Component Tests (TDD)
 *
 * Tests for the connection scope badge component.
 * @see ADR-0102 Phase 6
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ScopeBadge } from "./ScopeBadge";
import type { ConnectionScope } from "@/types/connection";

// Motion mock is provided globally in src/test/setup.ts

describe("ScopeBadge", () => {
  describe("Rendering", () => {
    it("should render user scope with User icon and 'Personal' label", () => {
      render(<ScopeBadge scope="user" />);
      expect(screen.getByText("Personal")).toBeInTheDocument();
      expect(screen.getByTestId("scope-badge")).toHaveAttribute(
        "data-scope",
        "user"
      );
    });

    it("should render project scope with Users icon and 'Shared' label", () => {
      render(<ScopeBadge scope="project" />);
      expect(screen.getByText("Shared")).toBeInTheDocument();
      expect(screen.getByTestId("scope-badge")).toHaveAttribute(
        "data-scope",
        "project"
      );
    });

    it("should render session scope with Clock icon and 'Session' label", () => {
      render(<ScopeBadge scope="session" />);
      expect(screen.getByText("Session")).toBeInTheDocument();
      expect(screen.getByTestId("scope-badge")).toHaveAttribute(
        "data-scope",
        "session"
      );
    });
  });

  describe("Variant Styles", () => {
    it("should use default variant for user scope", () => {
      render(<ScopeBadge scope="user" />);
      const badge = screen.getByTestId("scope-badge");
      // Default variant uses neutral colors
      expect(badge).toBeInTheDocument();
    });

    it("should use primary variant for project scope", () => {
      render(<ScopeBadge scope="project" />);
      const badge = screen.getByTestId("scope-badge");
      expect(badge).toBeInTheDocument();
    });

    it("should use warning variant for session scope", () => {
      render(<ScopeBadge scope="session" />);
      const badge = screen.getByTestId("scope-badge");
      expect(badge).toBeInTheDocument();
    });
  });

  describe("Size Variants", () => {
    it("should apply small size when size='sm'", () => {
      render(<ScopeBadge scope="user" size="sm" />);
      expect(screen.getByTestId("scope-badge")).toBeInTheDocument();
    });

    it("should apply medium size by default", () => {
      render(<ScopeBadge scope="user" />);
      expect(screen.getByTestId("scope-badge")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible label describing the scope", () => {
      render(<ScopeBadge scope="project" />);
      expect(screen.getByLabelText(/shared/i)).toBeInTheDocument();
    });

    it("should support custom className", () => {
      render(<ScopeBadge scope="user" className="custom-class" />);
      const badge = screen.getByTestId("scope-badge");
      expect(badge).toHaveClass("custom-class");
    });
  });

  describe("All Scopes", () => {
    const scopes: ConnectionScope[] = ["user", "project", "session"];
    const expectedLabels = {
      user: "Personal",
      project: "Shared",
      session: "Session",
    };

    scopes.forEach((scope) => {
      it(`should render ${scope} scope correctly`, () => {
        render(<ScopeBadge scope={scope} />);
        expect(screen.getByText(expectedLabels[scope])).toBeInTheDocument();
      });
    });
  });
});
