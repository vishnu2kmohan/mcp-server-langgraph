/**
 * FormErrorSummary Component Tests
 *
 * Tests for the form error summary component that displays
 * all validation errors at the top of complex forms.
 *
 * TDD: These tests were written FIRST before implementation.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormErrorSummary } from "./FormErrorSummary";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FormErrorSummary", () => {
  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("renders nothing when no errors", () => {
      const { container } = render(<FormErrorSummary errors={{}} />);
      expect(container.firstChild).toBeNull();
    });

    it("renders when errors are present", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email address" }} />
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("renders all error messages", () => {
      render(
        <FormErrorSummary
          errors={{
            email: "Invalid email address",
            password: "Password is too short",
            username: "Username is already taken",
          }}
        />
      );

      expect(screen.getByText("Invalid email address")).toBeInTheDocument();
      expect(screen.getByText("Password is too short")).toBeInTheDocument();
      expect(screen.getByText("Username is already taken")).toBeInTheDocument();
    });

    it("renders heading text", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      expect(
        screen.getByText("Please fix the following errors:")
      ).toBeInTheDocument();
    });

    it("renders error icon for visual indication", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      const alert = screen.getByRole("alert");
      expect(alert.querySelector("svg")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("has role=alert for screen readers", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("has aria-live=polite for non-intrusive announcement", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveAttribute("aria-live", "polite");
    });

    it("renders errors as a list for screen reader navigation", () => {
      render(
        <FormErrorSummary
          errors={{
            email: "Invalid email",
            password: "Too short",
          }}
        />
      );

      expect(screen.getByRole("list")).toBeInTheDocument();
      expect(screen.getAllByRole("listitem")).toHaveLength(2);
    });

    it("error links are anchor elements for keyboard navigation", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "#email");
    });
  });

  // ===========================================================================
  // Navigation Tests
  // ===========================================================================

  describe("field navigation", () => {
    it("error messages link to their corresponding fields", () => {
      render(
        <FormErrorSummary
          errors={{
            email: "Invalid email",
            password: "Too short",
          }}
        />
      );

      const links = screen.getAllByRole("link");
      expect(links[0]).toHaveAttribute("href", "#email");
      expect(links[1]).toHaveAttribute("href", "#password");
    });

    it("clicking error link focuses the field", async () => {
      const user = userEvent.setup();

      // Set up a mock field to focus
      const mockFocus = vi.fn();
      const mockElement = { focus: mockFocus };
      vi.spyOn(document, "getElementById").mockReturnValue(
        mockElement as unknown as HTMLElement
      );

      render(
        <>
          <FormErrorSummary errors={{ email: "Invalid email" }} />
        </>
      );

      const link = screen.getByRole("link");
      await user.click(link);

      expect(document.getElementById).toHaveBeenCalledWith("email");
      expect(mockFocus).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Styling Tests
  // ===========================================================================

  describe("styling", () => {
    it("has error background styling", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("bg-error-2");
    });

    it("has error border styling", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("border-error-6");
    });

    it("has error text color", () => {
      render(
        <FormErrorSummary errors={{ email: "Invalid email" }} />
      );

      const heading = screen.getByText("Please fix the following errors:");
      expect(heading).toHaveClass("text-error-11");
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <FormErrorSummary
          errors={{ email: "Invalid email" }}
          className="custom-class"
        />
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("custom-class");
    });

    it("accepts custom heading text", () => {
      render(
        <FormErrorSummary
          errors={{ email: "Invalid email" }}
          heading="There are errors in your form:"
        />
      );

      expect(
        screen.getByText("There are errors in your form:")
      ).toBeInTheDocument();
    });
  });
});
