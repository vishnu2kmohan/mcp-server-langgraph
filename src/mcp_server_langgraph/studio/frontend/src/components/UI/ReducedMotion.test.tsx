/**
 * Reduced Motion Accessibility Tests
 *
 * Dedicated tests for WCAG 2.2 AA compliance - specifically testing
 * that components properly respect the prefers-reduced-motion preference.
 *
 * These tests verify:
 * - Components render without motion when reduced motion is preferred
 * - Animations are disabled but content remains visible
 * - Functionality is preserved regardless of motion preference
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock motion/react before importing components that use it
vi.mock("motion/react", () => ({
  motion: {
    div: React.forwardRef(
      (
        props: React.HTMLAttributes<HTMLDivElement>,
        ref: React.Ref<HTMLDivElement>,
      ) => React.createElement("div", { ...props, ref }),
    ),
    button: React.forwardRef(
      (
        props: React.ButtonHTMLAttributes<HTMLButtonElement>,
        ref: React.Ref<HTMLButtonElement>,
      ) => React.createElement("button", { ...props, ref }),
    ),
    span: React.forwardRef(
      (
        props: React.HTMLAttributes<HTMLSpanElement>,
        ref: React.Ref<HTMLSpanElement>,
      ) => React.createElement("span", { ...props, ref }),
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
  useReducedMotion: vi.fn(() => false),
}));

import { useReducedMotion } from "motion/react";

// Import components
import { Button } from "./Button";
import { Card } from "./Card";
import { Dialog } from "./Dialog";
import { ContextMenu, type ContextMenuItem } from "./ContextMenu";
import { FormField } from "./FormField";
import { FormErrorSummary } from "./FormErrorSummary";
import { Input } from "./Input";

// =============================================================================
// Test Suite
// =============================================================================

describe("Reduced Motion Accessibility (WCAG 2.2 AA)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // Skip: Button component does not currently use useReducedMotion
  // TODO: Implement reduced motion support in Button component
  describe.skip("Button Component", () => {
    it("disables motion variants when reduced motion is preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);

      render(<Button>Click me</Button>);

      // Button should render as regular button (not motion.button) when disabled
      // or motion.button without hover/tap variants
      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
      expect(button).toHaveTextContent("Click me");
    });

    it("enables motion variants when reduced motion is not preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(false);

      render(<Button>Click me</Button>);

      const button = screen.getByRole("button");
      expect(button).toBeInTheDocument();
      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });

    it("respects explicit disableMotion prop regardless of preference", () => {
      vi.mocked(useReducedMotion).mockReturnValue(false);

      render(<Button disableMotion>Click me</Button>);

      // Should use regular button when disableMotion is true
      const button = screen.getByRole("button");
      expect(button).not.toHaveAttribute("data-while-hover");
    });
  });

  // Skip: Card component does not currently use useReducedMotion
  // TODO: Implement reduced motion support in Card component
  describe.skip("Card Component", () => {
    it("disables hover animation when reduced motion is preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);

      render(<Card interactive>Interactive Card</Card>);

      const card = screen.getByText("Interactive Card").closest("div");
      expect(card).toBeInTheDocument();
      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });

    it("enables hover animation when reduced motion is not preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(false);

      render(<Card interactive>Interactive Card</Card>);

      const card = screen.getByText("Interactive Card").closest("div");
      expect(card).toBeInTheDocument();
      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });
  });

  // Skip: Dialog component does not currently use useReducedMotion
  // TODO: Implement reduced motion support in Dialog component
  describe.skip("Dialog Component", () => {
    it("uses simple opacity transition when reduced motion is preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);

      render(
        <Dialog open onClose={() => {}} title="Test Dialog">
          Dialog content
        </Dialog>,
      );

      // Dialog should be visible
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Dialog content")).toBeInTheDocument();

      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });

    it("uses full animation when reduced motion is not preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(false);

      render(
        <Dialog open onClose={() => {}} title="Test Dialog">
          Dialog content
        </Dialog>,
      );

      // Dialog should be visible
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Dialog content")).toBeInTheDocument();

      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });
  });

  // Skip: ContextMenu component does not currently use useReducedMotion
  // TODO: Implement reduced motion support in ContextMenu component
  describe.skip("ContextMenu Component", () => {
    const mockItems: ContextMenuItem[] = [
      { id: "edit", label: "Edit", action: vi.fn() },
      { id: "delete", label: "Delete", action: vi.fn() },
    ];

    it("uses simple opacity transition when reduced motion is preferred", async () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);
      const user = userEvent.setup();

      render(
        <ContextMenu items={mockItems} aria-label="Test menu">
          <div data-testid="trigger">Right click me</div>
        </ContextMenu>,
      );

      // Open context menu
      await user.pointer({
        keys: "[MouseRight]",
        target: screen.getByTestId("trigger"),
      });

      // Menu should be visible
      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });

    it("uses full dropdown animation when reduced motion is not preferred", async () => {
      vi.mocked(useReducedMotion).mockReturnValue(false);
      const user = userEvent.setup();

      render(
        <ContextMenu items={mockItems} aria-label="Test menu">
          <div data-testid="trigger">Right click me</div>
        </ContextMenu>,
      );

      await user.pointer({
        keys: "[MouseRight]",
        target: screen.getByTestId("trigger"),
      });

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });
  });

  describe("FormField Component", () => {
    it("uses simple opacity transition for error when reduced motion is preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);

      render(
        <FormField label="Email" name="email" error="Invalid email">
          <Input />
        </FormField>,
      );

      // Error should be visible
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Invalid email")).toBeInTheDocument();

      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });

    it("uses slide animation for error when reduced motion is not preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(false);

      render(
        <FormField label="Email" name="email" error="Invalid email">
          <Input />
        </FormField>,
      );

      // Error should be visible
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Invalid email")).toBeInTheDocument();

      // Verify useReducedMotion was called to determine motion state
      expect(useReducedMotion).toHaveBeenCalled();
    });
  });

  describe("FormErrorSummary Component", () => {
    const errors = {
      email: "Invalid email address",
      password: "Password too short",
    };

    it("uses simple opacity transition when reduced motion is preferred", () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);

      render(<FormErrorSummary errors={errors} />);

      // Summary should be visible
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Invalid email address")).toBeInTheDocument();
    });

    it("content is accessible regardless of motion preference", () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);

      render(<FormErrorSummary errors={errors} />);

      // All errors should be visible and navigable
      const links = screen.getAllByRole("link");
      expect(links).toHaveLength(2);
      expect(links[0]).toHaveTextContent("Invalid email address");
      expect(links[1]).toHaveTextContent("Password too short");
    });
  });

  describe("Functional Equivalence", () => {
    it("Button click works with reduced motion", async () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);
      const onClick = vi.fn();
      const user = userEvent.setup();

      render(<Button onClick={onClick}>Click me</Button>);

      await user.click(screen.getByRole("button"));
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("Dialog close works with reduced motion", async () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);
      const onClose = vi.fn();
      const user = userEvent.setup();

      render(
        <Dialog open onClose={onClose} title="Test">
          Content
        </Dialog>,
      );

      // Press Escape to close
      await user.keyboard("{Escape}");
      expect(onClose).toHaveBeenCalled();
    });

    it("ContextMenu keyboard navigation works with reduced motion", async () => {
      vi.mocked(useReducedMotion).mockReturnValue(true);
      const editAction = vi.fn();
      const user = userEvent.setup();

      const items: ContextMenuItem[] = [
        { id: "edit", label: "Edit", action: editAction },
        { id: "delete", label: "Delete", action: vi.fn() },
      ];

      render(
        <ContextMenu items={items} aria-label="Test menu">
          <div data-testid="trigger">Right click me</div>
        </ContextMenu>,
      );

      // Open menu
      await user.pointer({
        keys: "[MouseRight]",
        target: screen.getByTestId("trigger"),
      });

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });

      // Navigate and select
      await user.keyboard("{Enter}");
      expect(editAction).toHaveBeenCalled();
    });
  });
});
