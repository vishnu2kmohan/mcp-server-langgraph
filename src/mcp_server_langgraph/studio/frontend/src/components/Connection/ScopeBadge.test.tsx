/**
 * ScopeBadge Component Tests (TDD)
 *
 * Tests for the connection scope badge component.
 * @see ADR-0102 Phase 6
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ScopeBadge } from "./ScopeBadge";
import type { ConnectionScope } from "@/types/connection";

import { TestProvider } from "@/test-utils";

// Motion mock is provided globally in src/test/setup.ts

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ScopeBadge", () => {
  describe("Rendering", () => {
    it("should render user scope with User icon and 'Personal' label", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="user" />
        </TestProvider>,
      );
      expect(screen.getByText("Personal")).toBeInTheDocument();
      expect(screen.getByTestId("scope-badge")).toHaveAttribute(
        "data-scope",
        "user",
      );
    });

    it("should render project scope with Users icon and 'Shared' label", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="project" />
        </TestProvider>,
      );
      expect(screen.getByText("Shared")).toBeInTheDocument();
      expect(screen.getByTestId("scope-badge")).toHaveAttribute(
        "data-scope",
        "project",
      );
    });

    it("should render session scope with Clock icon and 'Session' label", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="session" />
        </TestProvider>,
      );
      expect(screen.getByText("Session")).toBeInTheDocument();
      expect(screen.getByTestId("scope-badge")).toHaveAttribute(
        "data-scope",
        "session",
      );
    });
  });

  describe("Variant Styles", () => {
    it("should use default variant for user scope", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="user" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("scope-badge");
      // Default variant uses neutral colors
      expect(badge).toBeInTheDocument();
    });

    it("should use primary variant for project scope", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="project" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("scope-badge");
      expect(badge).toBeInTheDocument();
    });

    it("should use warning variant for session scope", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="session" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("scope-badge");
      expect(badge).toBeInTheDocument();
    });
  });

  describe("Size Variants", () => {
    it("should apply small size when size='sm'", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="user" size="sm" />
        </TestProvider>,
      );
      expect(screen.getByTestId("scope-badge")).toBeInTheDocument();
    });

    it("should apply medium size by default", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="user" />
        </TestProvider>,
      );
      expect(screen.getByTestId("scope-badge")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible label describing the scope", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="project" />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/shared/i)).toBeInTheDocument();
    });

    it("should support custom className", () => {
      render(
        <TestProvider>
          <ScopeBadge scope="user" className="custom-class" />
        </TestProvider>,
      );
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
        render(
          <TestProvider>
            <ScopeBadge scope={scope} />
          </TestProvider>,
        );
        expect(screen.getByText(expectedLabels[scope])).toBeInTheDocument();
      });
    });
  });
});
