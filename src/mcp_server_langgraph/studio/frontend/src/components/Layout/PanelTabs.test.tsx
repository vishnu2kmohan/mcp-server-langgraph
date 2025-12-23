/**
 * PanelTabs Component Tests
 *
 * Tests for JupyterLab-style tabbed panels within sidebars.
 * Allows multiple views to be accessible via tabs.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  PanelTabs,
  PanelTab,
  PanelTabList,
  PanelTabContent,
} from "./PanelTabs";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PanelTabs", () => {
  const defaultTabs = [
    {
      id: "tab1",
      label: "Tab 1",
      content: <div data-testid="content-1">Content 1</div>,
    },
    {
      id: "tab2",
      label: "Tab 2",
      content: <div data-testid="content-2">Content 2</div>,
    },
    {
      id: "tab3",
      label: "Tab 3",
      content: <div data-testid="content-3">Content 3</div>,
    },
  ];

  describe("rendering", () => {
    it("renders all tab labels", () => {
      render(<PanelTabs tabs={defaultTabs} />);

      expect(screen.getByText("Tab 1")).toBeInTheDocument();
      expect(screen.getByText("Tab 2")).toBeInTheDocument();
      expect(screen.getByText("Tab 3")).toBeInTheDocument();
    });

    it("renders first tab content by default", () => {
      render(<PanelTabs tabs={defaultTabs} />);

      expect(screen.getByTestId("content-1")).toBeInTheDocument();
      expect(screen.queryByTestId("content-2")).not.toBeInTheDocument();
    });

    it("renders specified default tab content", () => {
      render(<PanelTabs tabs={defaultTabs} defaultActiveId="tab2" />);

      expect(screen.queryByTestId("content-1")).not.toBeInTheDocument();
      expect(screen.getByTestId("content-2")).toBeInTheDocument();
    });
  });

  describe("tab selection", () => {
    it("switches content when tab is clicked", () => {
      render(<PanelTabs tabs={defaultTabs} />);

      // Initially shows tab 1
      expect(screen.getByTestId("content-1")).toBeInTheDocument();

      // Click tab 2
      fireEvent.click(screen.getByText("Tab 2"));

      // Now shows tab 2
      expect(screen.queryByTestId("content-1")).not.toBeInTheDocument();
      expect(screen.getByTestId("content-2")).toBeInTheDocument();
    });

    it("highlights active tab", () => {
      render(<PanelTabs tabs={defaultTabs} />);

      const tab1 = screen.getByText("Tab 1").closest("button");
      expect(tab1).toHaveAttribute("aria-selected", "true");

      fireEvent.click(screen.getByText("Tab 2"));

      const tab2 = screen.getByText("Tab 2").closest("button");
      expect(tab1).toHaveAttribute("aria-selected", "false");
      expect(tab2).toHaveAttribute("aria-selected", "true");
    });

    it("calls onTabChange when tab changes", () => {
      const onTabChange = vi.fn();
      render(<PanelTabs tabs={defaultTabs} onTabChange={onTabChange} />);

      fireEvent.click(screen.getByText("Tab 2"));
      expect(onTabChange).toHaveBeenCalledWith("tab2");
    });
  });

  describe("controlled mode", () => {
    it("respects controlled activeId prop", () => {
      const { rerender } = render(
        <PanelTabs tabs={defaultTabs} activeId="tab1" />,
      );

      expect(screen.getByTestId("content-1")).toBeInTheDocument();

      rerender(<PanelTabs tabs={defaultTabs} activeId="tab3" />);

      expect(screen.queryByTestId("content-1")).not.toBeInTheDocument();
      expect(screen.getByTestId("content-3")).toBeInTheDocument();
    });
  });

  describe("closable tabs", () => {
    it("shows close button for closable tabs", () => {
      const closableTabs = [
        { id: "tab1", label: "Tab 1", content: <div>1</div>, closable: true },
        { id: "tab2", label: "Tab 2", content: <div>2</div>, closable: false },
      ];
      render(<PanelTabs tabs={closableTabs} />);

      // Tab 1 should have close button
      const tab1Container = screen.getByText("Tab 1").closest("div");
      expect(
        tab1Container?.querySelector("[aria-label='Close tab']"),
      ).toBeInTheDocument();

      // Tab 2 should not have close button
      const tab2Container = screen.getByText("Tab 2").closest("div");
      expect(
        tab2Container?.querySelector("[aria-label='Close tab']"),
      ).not.toBeInTheDocument();
    });

    it("calls onTabClose when close button is clicked", () => {
      const onTabClose = vi.fn();
      const closableTabs = [
        { id: "tab1", label: "Tab 1", content: <div>1</div>, closable: true },
        { id: "tab2", label: "Tab 2", content: <div>2</div> },
      ];
      render(<PanelTabs tabs={closableTabs} onTabClose={onTabClose} />);

      const closeButton = screen.getByLabelText("Close tab");
      fireEvent.click(closeButton);

      expect(onTabClose).toHaveBeenCalledWith("tab1");
    });
  });

  describe("icons", () => {
    it("renders tab icons when provided", () => {
      const tabsWithIcons = [
        {
          id: "tab1",
          label: "Tab 1",
          content: <div>1</div>,
          icon: <span data-testid="icon-1">Icon</span>,
        },
      ];
      render(<PanelTabs tabs={tabsWithIcons} />);

      expect(screen.getByTestId("icon-1")).toBeInTheDocument();
    });
  });

  describe("keyboard navigation", () => {
    it("navigates tabs with arrow keys", () => {
      render(<PanelTabs tabs={defaultTabs} />);

      const tab1 = screen.getByText("Tab 1").closest("button");
      tab1?.focus();

      // Press right arrow
      fireEvent.keyDown(tab1!, { key: "ArrowRight" });
      expect(document.activeElement).toBe(
        screen.getByText("Tab 2").closest("button"),
      );

      // Press right arrow again
      fireEvent.keyDown(document.activeElement!, { key: "ArrowRight" });
      expect(document.activeElement).toBe(
        screen.getByText("Tab 3").closest("button"),
      );

      // Press left arrow
      fireEvent.keyDown(document.activeElement!, { key: "ArrowLeft" });
      expect(document.activeElement).toBe(
        screen.getByText("Tab 2").closest("button"),
      );
    });

    it("wraps around when navigating past edges", () => {
      render(<PanelTabs tabs={defaultTabs} />);

      const tab1 = screen.getByText("Tab 1").closest("button");
      tab1?.focus();

      // Press left arrow from first tab
      fireEvent.keyDown(tab1!, { key: "ArrowLeft" });
      expect(document.activeElement).toBe(
        screen.getByText("Tab 3").closest("button"),
      );
    });
  });
});

describe("PanelTabList", () => {
  it("renders children tabs", () => {
    render(
      <PanelTabList>
        <PanelTab id="1" isActive={true}>
          Tab 1
        </PanelTab>
        <PanelTab id="2" isActive={false}>
          Tab 2
        </PanelTab>
      </PanelTabList>,
    );

    expect(screen.getByText("Tab 1")).toBeInTheDocument();
    expect(screen.getByText("Tab 2")).toBeInTheDocument();
  });
});

describe("PanelTab", () => {
  it("applies active styling", () => {
    render(
      <PanelTab id="1" isActive={true}>
        Active Tab
      </PanelTab>,
    );

    const tab = screen.getByText("Active Tab").closest("button");
    expect(tab).toHaveAttribute("aria-selected", "true");
  });

  it("applies inactive styling", () => {
    render(
      <PanelTab id="1" isActive={false}>
        Inactive Tab
      </PanelTab>,
    );

    const tab = screen.getByText("Inactive Tab").closest("button");
    expect(tab).toHaveAttribute("aria-selected", "false");
  });
});

describe("PanelTabContent", () => {
  it("renders children content", () => {
    render(
      <PanelTabContent>
        <div data-testid="test-content">Test Content</div>
      </PanelTabContent>,
    );

    expect(screen.getByTestId("test-content")).toBeInTheDocument();
  });
});
