/**
 * Tests for Breadcrumb component
 *
 * TDD RED Phase: Tests written before implementation
 *
 * The Breadcrumb component:
 * - Renders a list of navigation items with separators
 * - Makes non-current items clickable (Link)
 * - Current item is not clickable (span)
 * - Accessible with proper ARIA attributes
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import type { BreadcrumbItem } from "../hooks/useBreadcrumb";

// Import after creating the component
import { Breadcrumb } from "./Breadcrumb";

// Helper to render with router
function renderWithRouter(ui: React.ReactElement, initialEntries = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>,
  );
}

describe("Breadcrumb", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render nothing when items array is empty", () => {
      renderWithRouter(<Breadcrumb items={[]} />);

      expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    });

    it("should render a single item without separator", () => {
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: true },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      expect(screen.getByText("Projects")).toBeInTheDocument();
      expect(screen.queryByText("/")).not.toBeInTheDocument();
    });

    it("should render multiple items with separators", () => {
      const items: BreadcrumbItem[] = [
        { label: "Agent Studio", path: "/studio", isCurrent: false },
        { label: "Projects", path: "/studio/projects", isCurrent: false },
        {
          label: "Project Details",
          path: "/studio/projects/123",
          isCurrent: true,
        },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      expect(screen.getByText("Agent Studio")).toBeInTheDocument();
      expect(screen.getByText("Projects")).toBeInTheDocument();
      expect(screen.getByText("Project Details")).toBeInTheDocument();

      // Should have 2 separators for 3 items
      const separators = screen.getAllByText("/");
      expect(separators).toHaveLength(2);
    });

    it("should render current item as span (not clickable)", () => {
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: false },
        {
          label: "Project Details",
          path: "/studio/projects/123",
          isCurrent: true,
        },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      // Current item should be a span with aria-current
      const currentItem = screen.getByText("Project Details");
      expect(currentItem.tagName).toBe("SPAN");
      expect(currentItem).toHaveAttribute("aria-current", "page");
    });

    it("should render non-current items as links", () => {
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: false },
        {
          label: "Project Details",
          path: "/studio/projects/123",
          isCurrent: true,
        },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      // Non-current item should be a link
      const link = screen.getByRole("link", { name: "Projects" });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/studio/projects");
    });
  });

  describe("accessibility", () => {
    it("should have nav element with aria-label", () => {
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: true },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      const nav = screen.getByRole("navigation");
      expect(nav).toHaveAttribute("aria-label", "Breadcrumb");
    });

    it("should render as ordered list for proper semantics", () => {
      const items: BreadcrumbItem[] = [
        { label: "Agent Studio", path: "/studio", isCurrent: false },
        { label: "Projects", path: "/studio/projects", isCurrent: true },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      const list = screen.getByRole("list");
      expect(list).toBeInTheDocument();

      const listItems = screen.getAllByRole("listitem");
      expect(listItems).toHaveLength(2);
    });

    it("should hide separators from screen readers", () => {
      const items: BreadcrumbItem[] = [
        { label: "Agent Studio", path: "/studio", isCurrent: false },
        { label: "Projects", path: "/studio/projects", isCurrent: true },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      const separators = screen.getAllByText("/");
      separators.forEach((separator) => {
        expect(separator).toHaveAttribute("aria-hidden", "true");
      });
    });
  });

  describe("navigation", () => {
    it("should navigate when clicking non-current item", async () => {
      const user = userEvent.setup();
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: false },
        {
          label: "Project Details",
          path: "/studio/projects/123",
          isCurrent: true,
        },
      ];

      renderWithRouter(<Breadcrumb items={items} />, ["/studio/projects/123"]);

      const link = screen.getByRole("link", { name: "Projects" });
      await user.click(link);

      // Link should exist and be clickable (navigation happens via router)
      expect(link).toHaveAttribute("href", "/studio/projects");
    });
  });

  describe("styling", () => {
    it("should apply custom className", () => {
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: true },
      ];

      renderWithRouter(<Breadcrumb items={items} className="custom-class" />);

      const nav = screen.getByRole("navigation");
      expect(nav).toHaveClass("custom-class");
    });

    it("should apply different styles to current vs non-current items", () => {
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: false },
        {
          label: "Project Details",
          path: "/studio/projects/123",
          isCurrent: true,
        },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      const link = screen.getByRole("link", { name: "Projects" });
      const current = screen.getByText("Project Details");

      // Links should have hover/underline styles (via className or data attribute)
      expect(link).toHaveClass("hover:underline");

      // Current should have different styling (no hover)
      expect(current).not.toHaveClass("hover:underline");
    });
  });

  describe("data-testid attributes", () => {
    it("should have data-testid on nav element", () => {
      const items: BreadcrumbItem[] = [
        { label: "Projects", path: "/studio/projects", isCurrent: true },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      expect(screen.getByTestId("breadcrumb-nav")).toBeInTheDocument();
    });

    it("should have data-testid on breadcrumb items", () => {
      const items: BreadcrumbItem[] = [
        { label: "Agent Studio", path: "/studio", isCurrent: false },
        { label: "Projects", path: "/studio/projects", isCurrent: true },
      ];

      renderWithRouter(<Breadcrumb items={items} />);

      expect(screen.getByTestId("breadcrumb-item-0")).toBeInTheDocument();
      expect(screen.getByTestId("breadcrumb-item-1")).toBeInTheDocument();
    });
  });
});
