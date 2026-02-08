/**
 * EmptyState Component Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * The EmptyState component implements the Fogg Behavior Model:
 * - Motivation: Why the user should act
 * - Ability: How easy it is to act
 * - Trigger: CTA button/action
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { EmptyState, type EmptyStateContext } from "./EmptyState";

import { TestProvider } from "@/test-utils";

describe("EmptyState", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders with required props", () => {
      render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions yet"
            motivation="Start a conversation to see your sessions here"
            trigger={<button>Start Chat</button>}
          />
        </TestProvider>,
      );

      expect(screen.getByText("No sessions yet")).toBeInTheDocument();
      expect(
        screen.getByText("Start a conversation to see your sessions here"),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Start Chat" }),
      ).toBeInTheDocument();
    });

    it("renders with optional ability text", () => {
      render(
        <TestProvider>
          <EmptyState
            context="workflows"
            title="No workflows"
            motivation="Build automated workflows"
            ability="Takes about 2 minutes"
            trigger={<button>Create Workflow</button>}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Takes about 2 minutes")).toBeInTheDocument();
    });

    it("renders with optional description", () => {
      render(
        <TestProvider>
          <EmptyState
            context="projects"
            title="No projects"
            motivation="Organize your work"
            description="Projects help you group related sessions and workflows together."
            trigger={<button>New Project</button>}
          />
        </TestProvider>,
      );

      expect(
        screen.getByText(
          "Projects help you group related sessions and workflows together.",
        ),
      ).toBeInTheDocument();
    });

    it("renders context-appropriate icon when no custom icon provided", () => {
      const { container } = render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
          />
        </TestProvider>,
      );

      // Should have an icon element
      expect(
        container.querySelector("[data-testid='empty-state-icon']"),
      ).toBeInTheDocument();
    });

    it("renders custom icon when provided", () => {
      const CustomIcon = () => <svg data-testid="custom-icon" />;

      render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
            icon={<CustomIcon />}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
    });
  });

  describe("context-specific rendering", () => {
    const contexts: EmptyStateContext[] = [
      "sessions",
      "projects",
      "workflows",
      "traces",
      "messages",
      "files",
      "alerts",
      "connections",
    ];

    contexts.forEach((context) => {
      it(`renders correctly for ${context} context`, () => {
        const { container } = render(
          <TestProvider>
            <EmptyState
              context={context}
              title={`No ${context}`}
              motivation="Take action"
              trigger={<button>Action</button>}
            />
          </TestProvider>,
        );

        expect(
          container.querySelector(`[data-context="${context}"]`),
        ).toBeInTheDocument();
      });
    });
  });

  describe("accessibility", () => {
    it("has proper ARIA structure", () => {
      render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
          />
        </TestProvider>,
      );

      const emptyState = screen.getByRole("region");
      expect(emptyState).toHaveAttribute(
        "aria-label",
        "Empty state: No sessions",
      );
    });

    it("icon is hidden from screen readers", () => {
      const { container } = render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
          />
        </TestProvider>,
      );

      const iconContainer = container.querySelector(
        "[data-testid='empty-state-icon']",
      );
      expect(iconContainer).toHaveAttribute("aria-hidden", "true");
    });
  });

  describe("variants", () => {
    it("renders default variant", () => {
      const { container } = render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
          />
        </TestProvider>,
      );

      expect(
        container.querySelector("[data-variant='default']"),
      ).toBeInTheDocument();
    });

    it("renders compact variant with smaller spacing", () => {
      const { container } = render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
            variant="compact"
          />
        </TestProvider>,
      );

      expect(
        container.querySelector("[data-variant='compact']"),
      ).toBeInTheDocument();
    });

    it("renders inline variant", () => {
      const { container } = render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
            variant="inline"
          />
        </TestProvider>,
      );

      expect(
        container.querySelector("[data-variant='inline']"),
      ).toBeInTheDocument();
    });
  });

  describe("secondary action", () => {
    it("renders secondary action when provided", () => {
      render(
        <TestProvider>
          <EmptyState
            context="workflows"
            title="No workflows"
            motivation="Build automated workflows"
            trigger={<button>Create Workflow</button>}
            secondaryTrigger={<button>Import Workflow</button>}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: "Create Workflow" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Import Workflow" }),
      ).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("shows loading spinner when isLoading is true", () => {
      render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
            isLoading={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("empty-state-loading")).toBeInTheDocument();
    });

    it("hides trigger when loading", () => {
      render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
            isLoading={true}
          />
        </TestProvider>,
      );

      expect(
        screen.queryByRole("button", { name: "Start" }),
      ).not.toBeInTheDocument();
    });
  });

  describe("data-testid", () => {
    it("has correct data-testid", () => {
      render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("empty-state-sessions")).toBeInTheDocument();
    });

    it("uses custom testId when provided", () => {
      render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
            testId="custom-empty-state"
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("custom-empty-state")).toBeInTheDocument();
    });
  });

  describe("className extension", () => {
    it("accepts additional className", () => {
      const { container } = render(
        <TestProvider>
          <EmptyState
            context="sessions"
            title="No sessions"
            motivation="Start chatting"
            trigger={<button>Start</button>}
            className="custom-class"
          />
        </TestProvider>,
      );

      expect(container.firstChild).toHaveClass("custom-class");
    });
  });
});
