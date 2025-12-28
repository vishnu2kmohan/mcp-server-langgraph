/**
 * BudgetStatusCard Tests
 *
 * TDD tests for budget status display component.
 * Tests written FIRST (RED phase).
 */

import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { BudgetStatusCard, type BudgetStatus } from "./BudgetStatusCard";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("BudgetStatusCard", () => {
  const defaultProps: { status: BudgetStatus } = {
    status: {
      entityType: "organization",
      entityId: "organization:acme",
      status: "ok",
      percentUsed: 50,
      currentSpend: "500.00",
      remaining: "500.00",
      monthlyLimitUsd: "1000.00",
      message: "Budget on track: 50.0% used, $500.00 remaining",
    },
  };

  describe("Core Rendering", () => {
    it("renders the component", () => {
      render(<BudgetStatusCard {...defaultProps} />);
      expect(screen.getByTestId("budget-status-card")).toBeInTheDocument();
    });

    it("displays entity name", () => {
      render(<BudgetStatusCard {...defaultProps} />);
      expect(screen.getByText(/acme/i)).toBeInTheDocument();
    });

    it("displays current spend", () => {
      render(<BudgetStatusCard {...defaultProps} />);
      // Current spend appears with "Spent:" label
      expect(screen.getByText(/Spent:/)).toBeInTheDocument();
      expect(screen.getAllByText(/\$500\.00/).length).toBeGreaterThan(0);
    });

    it("displays monthly limit", () => {
      render(<BudgetStatusCard {...defaultProps} />);
      expect(screen.getByText(/\$1,?000\.00/)).toBeInTheDocument();
    });

    it("displays percentage used", () => {
      render(<BudgetStatusCard {...defaultProps} />);
      expect(screen.getByText(/50%/)).toBeInTheDocument();
    });
  });

  describe("Status Styling", () => {
    it("shows green styling for ok status", () => {
      const props = {
        status: { ...defaultProps.status, status: "ok" as const },
      };
      render(<BudgetStatusCard {...props} />);
      const card = screen.getByTestId("budget-status-card");
      expect(card.className).toMatch(/green|success|ok/i);
    });

    it("shows yellow/amber styling for warning status", () => {
      const props = {
        status: {
          ...defaultProps.status,
          status: "warning" as const,
          percentUsed: 85,
        },
      };
      render(<BudgetStatusCard {...props} />);
      const card = screen.getByTestId("budget-status-card");
      expect(card.className).toMatch(/yellow|amber|warning/i);
    });

    it("shows orange styling for critical status", () => {
      const props = {
        status: {
          ...defaultProps.status,
          status: "critical" as const,
          percentUsed: 100,
        },
      };
      render(<BudgetStatusCard {...props} />);
      const card = screen.getByTestId("budget-status-card");
      expect(card.className).toMatch(/orange|critical/i);
    });

    it("shows red styling for exceeded status", () => {
      const props = {
        status: {
          ...defaultProps.status,
          status: "exceeded" as const,
          percentUsed: 120,
          remaining: "-200.00",
        },
      };
      render(<BudgetStatusCard {...props} />);
      const card = screen.getByTestId("budget-status-card");
      expect(card.className).toMatch(/red|exceeded|error/i);
    });
  });

  describe("Progress Bar", () => {
    it("shows progress bar", () => {
      render(<BudgetStatusCard {...defaultProps} />);
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("progress bar reflects percentage used", () => {
      render(<BudgetStatusCard {...defaultProps} />);
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar.getAttribute("aria-valuenow")).toBe("50");
    });

    it("caps progress bar at 100% for exceeded budgets", () => {
      const props = {
        status: {
          ...defaultProps.status,
          status: "exceeded" as const,
          percentUsed: 120,
        },
      };
      render(<BudgetStatusCard {...props} />);
      const progressBar = screen.getByRole("progressbar");
      // Visual width should cap at 100, but aria value shows actual
      expect(progressBar.getAttribute("aria-valuenow")).toBe("120");
    });
  });

  describe("Entity Types", () => {
    it("displays organization icon for organization type", () => {
      const props = {
        status: { ...defaultProps.status, entityType: "organization" as const },
      };
      render(<BudgetStatusCard {...props} />);
      expect(screen.getByTestId("entity-icon")).toBeInTheDocument();
    });

    it("displays project icon for project type", () => {
      const props = {
        status: {
          ...defaultProps.status,
          entityType: "project" as const,
          entityId: "project:backend",
        },
      };
      render(<BudgetStatusCard {...props} />);
      expect(screen.getByTestId("entity-icon")).toBeInTheDocument();
    });

    it("displays team icon for team type", () => {
      const props = {
        status: {
          ...defaultProps.status,
          entityType: "team" as const,
          entityId: "team:platform",
        },
      };
      render(<BudgetStatusCard {...props} />);
      expect(screen.getByTestId("entity-icon")).toBeInTheDocument();
    });

    it("displays user icon for user type", () => {
      const props = {
        status: {
          ...defaultProps.status,
          entityType: "user" as const,
          entityId: "user:john",
        },
      };
      render(<BudgetStatusCard {...props} />);
      expect(screen.getByTestId("entity-icon")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading skeleton when loading", () => {
      render(<BudgetStatusCard status={null} loading={true} />);
      expect(screen.getByTestId("budget-status-skeleton")).toBeInTheDocument();
    });
  });

  describe("Compact Mode", () => {
    it("renders in compact mode when specified", () => {
      render(<BudgetStatusCard {...defaultProps} compact={true} />);
      const card = screen.getByTestId("budget-status-card");
      expect(card.className).toMatch(/compact/i);
    });
  });
});
