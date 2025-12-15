/**
 * ErrorState Component Tests
 *
 * TDD tests for the standardized error state component.
 * Tests cover:
 * - Error message display
 * - Retry button functionality
 * - Custom styling options
 * - Icon display
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorState } from "./ErrorState";

describe("ErrorState", () => {
  describe("Display", () => {
    it("should display the error message", () => {
      render(<ErrorState message="Failed to load data" onRetry={() => {}} />);
      expect(screen.getByText("Failed to load data")).toBeInTheDocument();
    });

    it("should display default message when none provided", () => {
      render(<ErrorState onRetry={() => {}} />);
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should display error icon", () => {
      render(<ErrorState message="Error" onRetry={() => {}} />);
      expect(document.querySelector("svg")).toBeInTheDocument();
    });

    it("should display retry button", () => {
      render(<ErrorState message="Error" onRetry={() => {}} />);
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should not display retry button when onRetry is not provided", () => {
      render(<ErrorState message="Error" />);
      expect(
        screen.queryByRole("button", { name: /retry/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Retry Functionality", () => {
    it("should call onRetry when retry button is clicked", () => {
      const onRetry = vi.fn();
      render(<ErrorState message="Error" onRetry={onRetry} />);

      fireEvent.click(screen.getByRole("button", { name: /retry/i }));

      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe("Title", () => {
    it("should display custom title when provided", () => {
      render(
        <ErrorState title="Load Failed" message="Details" onRetry={() => {}} />,
      );
      expect(screen.getByText("Load Failed")).toBeInTheDocument();
    });

    it("should display default title when none provided", () => {
      render(<ErrorState message="Details" onRetry={() => {}} />);
      expect(screen.getByText("Error")).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("should apply compact styling", () => {
      const { container } = render(
        <ErrorState message="Error" onRetry={() => {}} variant="compact" />,
      );
      expect(container.querySelector(".py-8")).toBeInTheDocument();
    });

    it("should apply full height styling by default", () => {
      const { container } = render(
        <ErrorState message="Error" onRetry={() => {}} />,
      );
      expect(container.querySelector(".h-64")).toBeInTheDocument();
    });

    it("should apply full-screen styling when specified", () => {
      const { container } = render(
        <ErrorState message="Error" onRetry={() => {}} variant="fullscreen" />,
      );
      expect(container.querySelector(".h-full")).toBeInTheDocument();
    });
  });

  describe("Custom Button Text", () => {
    it("should use custom retry button text", () => {
      render(
        <ErrorState message="Error" onRetry={() => {}} retryText="Try Again" />,
      );
      expect(
        screen.getByRole("button", { name: /try again/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible role for error container", () => {
      render(<ErrorState message="Error" onRetry={() => {}} />);
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });
});
