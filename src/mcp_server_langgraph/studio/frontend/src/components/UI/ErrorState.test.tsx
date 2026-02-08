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

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ErrorState } from "./ErrorState";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ErrorState", () => {
  describe("Display", () => {
    it("should display the error message", () => {
      render(
        <TestProvider>
          <ErrorState message="Failed to load data" onRetry={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByText("Failed to load data")).toBeInTheDocument();
    });

    it("should display default message when none provided", () => {
      render(
        <TestProvider>
          <ErrorState onRetry={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should display error icon", () => {
      render(
        <TestProvider>
          <ErrorState message="Error" onRetry={() => {}} />
        </TestProvider>,
      );
      expect(document.querySelector("svg")).toBeInTheDocument();
    });

    it("should display retry button", () => {
      render(
        <TestProvider>
          <ErrorState message="Error" onRetry={() => {}} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should not display retry button when onRetry is not provided", () => {
      render(
        <TestProvider>
          <ErrorState message="Error" />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /retry/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Retry Functionality", () => {
    it("should call onRetry when retry button is clicked", () => {
      const onRetry = vi.fn();
      render(
        <TestProvider>
          <ErrorState message="Error" onRetry={onRetry} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /retry/i }));

      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe("Title", () => {
    it("should display custom title when provided", () => {
      render(
        <TestProvider>
          <ErrorState
            title="Load Failed"
            message="Details"
            onRetry={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByText("Load Failed")).toBeInTheDocument();
    });

    it("should display default title when none provided", () => {
      render(
        <TestProvider>
          <ErrorState message="Details" onRetry={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByText("Error")).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("should apply compact styling", () => {
      const { container } = render(
        <TestProvider>
          <ErrorState message="Error" onRetry={() => {}} variant="compact" />
        </TestProvider>,
      );
      expect(container.querySelector(".py-8")).toBeInTheDocument();
    });

    it("should apply full height styling by default", () => {
      const { container } = render(
        <TestProvider>
          <ErrorState message="Error" onRetry={() => {}} />
        </TestProvider>,
      );
      expect(container.querySelector(".h-64")).toBeInTheDocument();
    });

    it("should apply full-screen styling when specified", () => {
      const { container } = render(
        <TestProvider>
          <ErrorState message="Error" onRetry={() => {}} variant="fullscreen" />
        </TestProvider>,
      );
      expect(container.querySelector(".h-full")).toBeInTheDocument();
    });
  });

  describe("Custom Button Text", () => {
    it("should use custom retry button text", () => {
      render(
        <TestProvider>
          <ErrorState
            message="Error"
            onRetry={() => {}}
            retryText="Try Again"
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /try again/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible role for error container", () => {
      render(
        <TestProvider>
          <ErrorState message="Error" onRetry={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });
});
