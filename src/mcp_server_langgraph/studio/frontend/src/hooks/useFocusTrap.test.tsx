/**
 * useFocusTrap Tests (Sprint 3.3)
 *
 * Tests for the focus trap hook that traps keyboard focus within modal dialogs.
 * Required for WCAG 2.1 AA compliance (Focus Trap requirement for modal dialogs).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { useFocusTrap } from "./useFocusTrap";

import { TestProvider } from "@/test-utils";

// Test component that uses the hook
function TestModal({
  isActive,
  onClose,
}: {
  isActive: boolean;
  onClose?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, isActive);

  return (
    <div>
      <button data-testid="outside-button">Outside</button>
      <div ref={ref} data-testid="modal-container">
        <button data-testid="first-button">First</button>
        <input data-testid="middle-input" placeholder="Middle" />
        <button data-testid="last-button" onClick={onClose}>
          Last
        </button>
      </div>
    </div>
  );
}

// Test component with dynamic isActive state
function TestModalWithToggle() {
  const [isActive, setIsActive] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, isActive);

  return (
    <div>
      <button
        data-testid="toggle-button"
        onClick={() => setIsActive(!isActive)}
      >
        Toggle
      </button>
      <div ref={ref} data-testid="modal-container">
        <button data-testid="first-button">First</button>
        <button data-testid="last-button">Last</button>
      </div>
    </div>
  );
}

describe("useFocusTrap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("focus initialization", () => {
    it("should focus first focusable element when activated", async () => {
      render(
        <TestProvider>
          <TestModal isActive={true} />
        </TestProvider>,
      );

      // First focusable element inside the trap should be focused
      expect(screen.getByTestId("first-button")).toHaveFocus();
    });

    it("should not trap focus when isActive is false", async () => {
      render(
        <TestProvider>
          <TestModal isActive={false} />
        </TestProvider>,
      );

      // Should not auto-focus first element
      expect(screen.getByTestId("first-button")).not.toHaveFocus();
    });
  });

  describe("Tab key cycling", () => {
    it("should cycle focus from last element to first on Tab", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <TestModal isActive={true} />
        </TestProvider>,
      );

      // Focus is on first-button initially
      expect(screen.getByTestId("first-button")).toHaveFocus();

      // Tab through to middle input
      await user.tab();
      expect(screen.getByTestId("middle-input")).toHaveFocus();

      // Tab to last button
      await user.tab();
      expect(screen.getByTestId("last-button")).toHaveFocus();

      // Tab should cycle back to first button
      await user.tab();
      expect(screen.getByTestId("first-button")).toHaveFocus();
    });

    it("should cycle focus from first element to last on Shift+Tab", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <TestModal isActive={true} />
        </TestProvider>,
      );

      // Focus is on first-button initially
      expect(screen.getByTestId("first-button")).toHaveFocus();

      // Shift+Tab should cycle to last button
      await user.tab({ shift: true });
      expect(screen.getByTestId("last-button")).toHaveFocus();
    });
  });

  describe("activation/deactivation", () => {
    it("should trap focus when activated and release when deactivated", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <TestModalWithToggle />
        </TestProvider>,
      );

      // Initially not active, no focus trap
      const toggleButton = screen.getByTestId("toggle-button");
      const firstButton = screen.getByTestId("first-button");
      const lastButton = screen.getByTestId("last-button");

      // Activate the trap
      await user.click(toggleButton);

      // First element should be focused
      expect(firstButton).toHaveFocus();

      // Tab to last
      await user.tab();
      expect(lastButton).toHaveFocus();

      // Tab should cycle back to first
      await user.tab();
      expect(firstButton).toHaveFocus();
    });
  });

  describe("edge cases", () => {
    it("should handle empty container gracefully", async () => {
      function EmptyModal() {
        const ref = useRef<HTMLDivElement>(null);
        useFocusTrap(ref, true);
        return <div ref={ref} data-testid="empty-modal"></div>;
      }

      // Should not throw when rendered with empty container
      expect(() =>
        render(
          <TestProvider>
            <EmptyModal />
          </TestProvider>,
        ),
      ).not.toThrow();
    });

    it("should handle null ref gracefully", async () => {
      function NullRefModal() {
        const ref = useRef<HTMLDivElement>(null);
        // Intentionally not attaching ref to any element
        useFocusTrap(ref, true);
        return <div data-testid="modal-without-ref">Content</div>;
      }

      // Should not throw when ref is not attached
      expect(() =>
        render(
          <TestProvider>
            <NullRefModal />
          </TestProvider>,
        ),
      ).not.toThrow();
    });
  });

  describe("focusable elements detection", () => {
    it("should include buttons, inputs, selects, textareas, and links", async () => {
      function ComprehensiveModal() {
        const ref = useRef<HTMLDivElement>(null);
        useFocusTrap(ref, true);
        return (
          <div ref={ref}>
            <button data-testid="button">Button</button>
            <input data-testid="input" />
            <select data-testid="select">
              <option>Option</option>
            </select>
            <textarea data-testid="textarea" />
            <a href="#" data-testid="link">
              Link
            </a>
          </div>
        );
      }

      const user = userEvent.setup();
      render(
        <TestProvider>
          <ComprehensiveModal />
        </TestProvider>,
      );

      // Should focus first element (button)
      expect(screen.getByTestId("button")).toHaveFocus();

      // Tab through all focusable elements
      await user.tab();
      expect(screen.getByTestId("input")).toHaveFocus();

      await user.tab();
      expect(screen.getByTestId("select")).toHaveFocus();

      await user.tab();
      expect(screen.getByTestId("textarea")).toHaveFocus();

      await user.tab();
      expect(screen.getByTestId("link")).toHaveFocus();

      // Cycle back to first
      await user.tab();
      expect(screen.getByTestId("button")).toHaveFocus();
    });

    it("should skip elements with tabindex=-1", async () => {
      function ModalWithHiddenElement() {
        const ref = useRef<HTMLDivElement>(null);
        useFocusTrap(ref, true);
        return (
          <div ref={ref}>
            <button data-testid="first">First</button>
            <button data-testid="hidden" tabIndex={-1}>
              Hidden
            </button>
            <button data-testid="last">Last</button>
          </div>
        );
      }

      const user = userEvent.setup();
      render(
        <TestProvider>
          <ModalWithHiddenElement />
        </TestProvider>,
      );

      expect(screen.getByTestId("first")).toHaveFocus();

      // Tab should skip hidden and go directly to last
      await user.tab();
      expect(screen.getByTestId("last")).toHaveFocus();

      // Cycle back to first
      await user.tab();
      expect(screen.getByTestId("first")).toHaveFocus();
    });
  });
});
