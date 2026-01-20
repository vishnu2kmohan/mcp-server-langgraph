/**
 * FormField Component Tests
 *
 * Tests for the accessible form field wrapper component.
 * WCAG 2.2 compliance: 3.3.1 (Error Identification), 3.3.2 (Labels),
 * 3.3.3 (Error Suggestion), 1.4.1 (Use of Color).
 *
 * TDD: These tests were written FIRST before implementation.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { FormField } from "./FormField";
import { Input } from "./Input";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FormField", () => {
  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("renders with label and child input", () => {
      render(
        <FormField label="Email" name="email">
          <Input />
        </FormField>
      );

      expect(screen.getByLabelText("Email")).toBeInTheDocument();
    });

    it("renders label with correct htmlFor attribute", () => {
      render(
        <FormField label="Username" name="username">
          <Input />
        </FormField>
      );

      const label = screen.getByText("Username");
      expect(label).toHaveAttribute("for", "username");
    });

    it("sets id on child input matching name", () => {
      render(
        <FormField label="Password" name="password">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("id", "password");
    });

    it("sets name attribute on child input", () => {
      render(
        <FormField label="Email" name="email">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("name", "email");
    });
  });

  // ===========================================================================
  // Required Field Tests
  // ===========================================================================

  describe("required field", () => {
    it("shows visual required indicator (*)", () => {
      render(
        <FormField label="Email" name="email" required>
          <Input />
        </FormField>
      );

      expect(screen.getByText("*")).toBeInTheDocument();
    });

    it("hides visual indicator from screen readers", () => {
      render(
        <FormField label="Email" name="email" required>
          <Input />
        </FormField>
      );

      const asterisk = screen.getByText("*");
      expect(asterisk).toHaveAttribute("aria-hidden", "true");
    });

    it("provides screen reader text for required", () => {
      render(
        <FormField label="Email" name="email" required>
          <Input />
        </FormField>
      );

      expect(screen.getByText("(required)")).toHaveClass("sr-only");
    });

    it("sets aria-required on child input", () => {
      render(
        <FormField label="Email" name="email" required>
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("aria-required", "true");
    });
  });

  // ===========================================================================
  // Hint Text Tests
  // ===========================================================================

  describe("hint text", () => {
    it("renders hint text when provided", () => {
      render(
        <FormField label="Password" name="password" hint="Must be 8+ characters">
          <Input />
        </FormField>
      );

      expect(screen.getByText("Must be 8+ characters")).toBeInTheDocument();
    });

    it("associates hint with input via aria-describedby", () => {
      render(
        <FormField label="Password" name="password" hint="Must be 8+ characters">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("aria-describedby", "password-hint");
    });

    it("hint has correct id for association", () => {
      render(
        <FormField label="Password" name="password" hint="Must be 8+ characters">
          <Input />
        </FormField>
      );

      const hint = screen.getByText("Must be 8+ characters");
      expect(hint).toHaveAttribute("id", "password-hint");
    });

    it("does not show hint when error is present", () => {
      render(
        <FormField
          label="Password"
          name="password"
          hint="Must be 8+ characters"
          error="Password is too short"
        >
          <Input />
        </FormField>
      );

      expect(screen.queryByText("Must be 8+ characters")).not.toBeInTheDocument();
      expect(screen.getByText("Password is too short")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Error State Tests
  // ===========================================================================

  describe("error state", () => {
    it("renders error message when provided", () => {
      render(
        <FormField label="Email" name="email" error="Invalid email address">
          <Input />
        </FormField>
      );

      expect(screen.getByText("Invalid email address")).toBeInTheDocument();
    });

    it("error has role=alert for screen readers", () => {
      render(
        <FormField label="Email" name="email" error="Invalid email address">
          <Input />
        </FormField>
      );

      const error = screen.getByRole("alert");
      expect(error).toHaveTextContent("Invalid email address");
    });

    it("error has aria-live=assertive for immediate announcement", () => {
      render(
        <FormField label="Email" name="email" error="Invalid email address">
          <Input />
        </FormField>
      );

      const error = screen.getByRole("alert");
      expect(error).toHaveAttribute("aria-live", "assertive");
    });

    it("sets aria-invalid on child input when error", () => {
      render(
        <FormField label="Email" name="email" error="Invalid email address">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("aria-invalid", "true");
    });

    it("associates error with input via aria-describedby", () => {
      render(
        <FormField label="Email" name="email" error="Invalid email address">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).toHaveAttribute("aria-describedby", "email-error");
    });

    it("error has correct id for association", () => {
      render(
        <FormField label="Email" name="email" error="Invalid email address">
          <Input />
        </FormField>
      );

      const error = screen.getByRole("alert");
      expect(error).toHaveAttribute("id", "email-error");
    });

    it("displays error icon for visual indication (WCAG 1.4.1)", () => {
      render(
        <FormField label="Email" name="email" error="Invalid email address">
          <Input />
        </FormField>
      );

      // Error should have an icon, not just color
      const errorContainer = screen.getByRole("alert");
      expect(errorContainer.querySelector("svg")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("label is associated with input for screen readers", () => {
      render(
        <FormField label="Full Name" name="fullName">
          <Input />
        </FormField>
      );

      const input = screen.getByLabelText("Full Name");
      expect(input).toBeInTheDocument();
    });

    it("no aria-describedby when no hint or error", () => {
      render(
        <FormField label="Email" name="email">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).not.toHaveAttribute("aria-describedby");
    });

    it("no aria-invalid when no error", () => {
      render(
        <FormField label="Email" name="email">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).not.toHaveAttribute("aria-invalid");
    });
  });

  // ===========================================================================
  // Styling Tests
  // ===========================================================================

  describe("styling", () => {
    it("applies error styling class to child input when error", () => {
      render(
        <FormField label="Email" name="email" error="Invalid">
          <Input data-testid="input" />
        </FormField>
      );

      const input = screen.getByTestId("input");
      expect(input).toHaveClass("border-error-7");
    });

    it("has proper spacing between elements", () => {
      const { container } = render(
        <FormField label="Email" name="email" hint="Hint text">
          <Input />
        </FormField>
      );

      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass("space-y-1.5");
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("customization", () => {
    it("accepts custom className for wrapper", () => {
      const { container } = render(
        <FormField label="Email" name="email" className="custom-wrapper">
          <Input />
        </FormField>
      );

      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass("custom-wrapper");
    });
  });
});
