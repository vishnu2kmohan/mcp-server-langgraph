/**
 * Table Component Tests
 *
 * TDD tests for the shared Table UI component.
 * Tests compound component pattern, accessibility, and design system compliance.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableHeaderCell,
  TableCell,
} from "./Table";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Table", () => {
  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("renders a basic table with all compound components", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Item 1</TableCell>
                <TableCell>Active</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      expect(screen.getByRole("table")).toBeInTheDocument();
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Status")).toBeInTheDocument();
      expect(screen.getByText("Item 1")).toBeInTheDocument();
      expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("renders with custom className on Table", () => {
      render(
        <TestProvider>
          <Table className="custom-class">
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const table = screen.getByRole("table");
      expect(table).toHaveClass("custom-class");
    });

    it("renders empty table without errors", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Column</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody />
          </Table>
        </TestProvider>,
      );

      expect(screen.getByRole("table")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("has correct table role", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      expect(screen.getByRole("table")).toBeInTheDocument();
    });

    it("header cells have scope='col' attribute", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Item</TableCell>
                <TableCell>Active</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const headers = screen.getAllByRole("columnheader");
      headers.forEach((header) => {
        expect(header).toHaveAttribute("scope", "col");
      });
    });

    it("supports aria-label on Table", () => {
      render(
        <TestProvider>
          <Table aria-label="User list">
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      expect(screen.getByRole("table")).toHaveAttribute(
        "aria-label",
        "User list",
      );
    });

    it("supports aria-describedby on Table", () => {
      render(
        <TestProvider>
          <>
            <p id="table-desc">A list of active users</p>
            <Table aria-describedby="table-desc">
              <TableBody>
                <TableRow>
                  <TableCell>Content</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </>
        </TestProvider>,
      );

      expect(screen.getByRole("table")).toHaveAttribute(
        "aria-describedby",
        "table-desc",
      );
    });
  });

  // ===========================================================================
  // Design System Tests
  // ===========================================================================

  describe("design system compliance", () => {
    it("applies default styling to Table", () => {
      render(
        <TestProvider>
          <Table data-testid="table">
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const table = screen.getByTestId("table");
      expect(table).toHaveClass("w-full");
      expect(table).toHaveClass("text-sm");
    });

    it("applies design system colors to header", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead data-testid="thead">
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const thead = screen.getByTestId("thead");
      expect(thead).toHaveClass("bg-neutral-1");
      expect(thead).toHaveClass("border-b");
      expect(thead).toHaveClass("border-neutral-5");
    });

    it("applies consistent padding to header cells", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell data-testid="header-cell">
                  Name
                </TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const headerCell = screen.getByTestId("header-cell");
      expect(headerCell).toHaveClass("px-4");
      expect(headerCell).toHaveClass("py-3");
    });

    it("applies consistent padding to data cells", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell data-testid="data-cell">Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const dataCell = screen.getByTestId("data-cell");
      expect(dataCell).toHaveClass("px-4");
      expect(dataCell).toHaveClass("py-3");
    });

    it("applies row dividers using design system tokens", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody data-testid="tbody">
              <TableRow>
                <TableCell>Row 1</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Row 2</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const tbody = screen.getByTestId("tbody");
      expect(tbody).toHaveClass("divide-y");
      expect(tbody).toHaveClass("divide-neutral-5");
    });
  });

  // ===========================================================================
  // Variant Tests
  // ===========================================================================

  describe("variants", () => {
    it("supports 'compact' size variant with smaller padding", () => {
      render(
        <TestProvider>
          <Table size="compact">
            <TableHead>
              <TableRow>
                <TableHeaderCell data-testid="header-cell">
                  Name
                </TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell data-testid="data-cell">Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const headerCell = screen.getByTestId("header-cell");
      const dataCell = screen.getByTestId("data-cell");
      expect(headerCell).toHaveClass("px-2");
      expect(headerCell).toHaveClass("py-1.5");
      expect(dataCell).toHaveClass("px-2");
      expect(dataCell).toHaveClass("py-1.5");
    });

    it("supports 'striped' variant for alternating row colors", () => {
      render(
        <TestProvider>
          <Table striped>
            <TableBody data-testid="tbody">
              <TableRow>
                <TableCell>Row 1</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Row 2</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const tbody = screen.getByTestId("tbody");
      // The striped class uses a CSS selector that targets tbody when parent table has data-striped
      expect(tbody.className).toMatch(
        /\[table\[data-striped\]>&\]:even:\[&>tr\]:bg-neutral-2/,
      );
    });

    it("supports 'hoverable' variant for row hover states", () => {
      render(
        <TestProvider>
          <Table hoverable>
            <TableBody>
              <TableRow data-testid="row">
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const row = screen.getByTestId("row");
      expect(row).toHaveClass("hover:bg-neutral-a6");
    });

    it("supports 'bordered' variant for cell borders", () => {
      render(
        <TestProvider>
          <Table bordered>
            <TableBody>
              <TableRow>
                <TableCell data-testid="cell">Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const cell = screen.getByTestId("cell");
      expect(cell).toHaveClass("border");
      expect(cell).toHaveClass("border-neutral-5");
    });
  });

  // ===========================================================================
  // Interactive Row Tests
  // ===========================================================================

  describe("interactive rows", () => {
    it("applies clickable styles when TableRow has onClick", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody>
              <TableRow data-testid="row" onClick={() => {}}>
                <TableCell>Clickable</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const row = screen.getByTestId("row");
      expect(row).toHaveClass("cursor-pointer");
    });

    it("applies selected state to TableRow", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody>
              <TableRow data-testid="row" selected>
                <TableCell>Selected</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const row = screen.getByTestId("row");
      expect(row).toHaveClass("bg-primary-1");
    });
  });

  // ===========================================================================
  // Dark Mode Tests
  // ===========================================================================

  describe("dark mode", () => {
    it("includes dark mode classes for row dividers", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody data-testid="tbody">
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const tbody = screen.getByTestId("tbody");
      expect(tbody.className).toMatch(/dark:divide-neutral-6/);
    });

    it("includes dark mode classes for header", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead data-testid="thead">
              <TableRow>
                <TableHeaderCell>Name</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const thead = screen.getByTestId("thead");
      expect(thead.className).toMatch(/dark:border-neutral-6/);
    });
  });

  // ===========================================================================
  // Responsive Tests
  // ===========================================================================

  describe("responsive", () => {
    it("supports responsive wrapper for horizontal scroll", () => {
      const { container } = render(
        <TestProvider>
          <div className="overflow-x-auto">
            <Table>
              <TableBody>
                <TableRow>
                  <TableCell>Content</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </TestProvider>,
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass("overflow-x-auto");
    });
  });

  // ===========================================================================
  // Header Cell Alignment Tests
  // ===========================================================================

  describe("header cell alignment", () => {
    it("supports left alignment (default)", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell data-testid="header">Name</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const header = screen.getByTestId("header");
      expect(header).toHaveClass("text-left");
    });

    it("supports center alignment", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell data-testid="header" align="center">
                  Status
                </TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const header = screen.getByTestId("header");
      expect(header).toHaveClass("text-center");
    });

    it("supports right alignment", () => {
      render(
        <TestProvider>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell data-testid="header" align="right">
                  Amount
                </TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const header = screen.getByTestId("header");
      expect(header).toHaveClass("text-right");
    });
  });

  // ===========================================================================
  // Data Cell Alignment Tests
  // ===========================================================================

  describe("data cell alignment", () => {
    it("supports left alignment (default)", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell data-testid="cell">Content</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const cell = screen.getByTestId("cell");
      expect(cell).toHaveClass("text-left");
    });

    it("supports center alignment", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell data-testid="cell" align="center">
                  Content
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const cell = screen.getByTestId("cell");
      expect(cell).toHaveClass("text-center");
    });

    it("supports right alignment", () => {
      render(
        <TestProvider>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell data-testid="cell" align="right">
                  $100.00
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TestProvider>,
      );

      const cell = screen.getByTestId("cell");
      expect(cell).toHaveClass("text-right");
    });
  });
});
