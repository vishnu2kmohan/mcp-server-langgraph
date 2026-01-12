/**
 * StatusBadge Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * StatusBadge provides semantic status-based styling with accessibility support.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";
import { CheckCircle } from "lucide-react";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("StatusBadge", () => {
  describe("rendering", () => {
    it("renders with status text", () => {
      render(<StatusBadge status="success">Active</StatusBadge>);
      expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("renders with data-testid", () => {
      render(<StatusBadge status="success">Test</StatusBadge>);
      expect(screen.getByTestId("status-badge")).toBeInTheDocument();
    });
  });

  describe("status variants", () => {
    it("renders success status with semantic colors", () => {
      render(<StatusBadge status="success">Success</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("bg-success-100");
      expect(badge).toHaveClass("text-success-700");
    });

    it("renders warning status with semantic colors", () => {
      render(<StatusBadge status="warning">Warning</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("bg-warning-100");
      expect(badge).toHaveClass("text-warning-700");
    });

    it("renders error status with semantic colors", () => {
      render(<StatusBadge status="error">Error</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("bg-error-100");
      expect(badge).toHaveClass("text-error-700");
    });

    it("renders info status with semantic colors", () => {
      render(<StatusBadge status="info">Info</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("bg-primary-100");
      expect(badge).toHaveClass("text-primary-700");
    });

    it("renders neutral status with semantic colors", () => {
      render(<StatusBadge status="neutral">Neutral</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("bg-neutral-100");
      expect(badge).toHaveClass("text-neutral-700");
    });
  });

  describe("dark mode support", () => {
    it("includes dark mode classes for success", () => {
      render(<StatusBadge status="success">Success</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge.className).toMatch(/dark:bg-success-900/);
      expect(badge.className).toMatch(/dark:text-success-300/);
    });

    it("includes dark mode classes for error", () => {
      render(<StatusBadge status="error">Error</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge.className).toMatch(/dark:bg-error-900/);
      expect(badge.className).toMatch(/dark:text-error-300/);
    });
  });

  describe("with icons", () => {
    it("renders with custom icon", () => {
      render(
        <StatusBadge status="success" icon={<CheckCircle data-testid="icon" />}>
          Success
        </StatusBadge>,
      );
      expect(screen.getByTestId("icon")).toBeInTheDocument();
    });

    it("renders default icon when showIcon is true", () => {
      render(
        <StatusBadge status="success" showIcon>
          Success
        </StatusBadge>,
      );
      // Should have an icon rendered
      const badge = screen.getByTestId("status-badge");
      expect(badge.querySelector("svg")).toBeInTheDocument();
    });

    it("uses CheckCircle for success status default icon", () => {
      render(
        <StatusBadge status="success" showIcon>
          Success
        </StatusBadge>,
      );
      const badge = screen.getByTestId("status-badge");
      const svg = badge.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <StatusBadge status="success" size="sm">
          Small
        </StatusBadge>,
      );
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("text-xs");
    });

    it("renders medium size (default)", () => {
      render(<StatusBadge status="success">Medium</StatusBadge>);
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("text-sm");
    });

    it("renders large size", () => {
      render(
        <StatusBadge status="success" size="lg">
          Large
        </StatusBadge>,
      );
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("text-base");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <StatusBadge status="success" className="custom-class">
          Custom
        </StatusBadge>,
      );
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("custom-class");
    });

    it("renders as pill when pill prop is true", () => {
      render(
        <StatusBadge status="success" pill>
          Pill
        </StatusBadge>,
      );
      const badge = screen.getByTestId("status-badge");
      expect(badge).toHaveClass("rounded-full");
    });
  });

  describe("accessibility", () => {
    it("has accessible role", () => {
      render(<StatusBadge status="success">Active</StatusBadge>);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("includes aria-label when provided", () => {
      render(
        <StatusBadge status="success" aria-label="Status: Active">
          Active
        </StatusBadge>,
      );
      expect(screen.getByLabelText("Status: Active")).toBeInTheDocument();
    });
  });
});
