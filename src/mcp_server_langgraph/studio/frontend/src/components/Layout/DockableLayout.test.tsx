/**
 * DockableLayout Component Tests
 *
 * Tests for the DevTools-style dockable panel layout.
 * Implements resizable panels for chat workspace.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import {
  DockableLayout,
  DockablePanel,
  DockablePanelGroup,
  DockableResizeHandle,
} from "./DockableLayout";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DockableLayout", () => {
  describe("rendering", () => {
    it("renders children", () => {
      render(
        <DockableLayout>
          <div data-testid="child">Content</div>
        </DockableLayout>,
      );
      expect(screen.getByTestId("child")).toBeInTheDocument();
    });

    it("applies container styling", () => {
      render(<DockableLayout data-testid="layout">Content</DockableLayout>);
      expect(screen.getByTestId("layout")).toHaveClass("h-full");
    });
  });

  describe("direction", () => {
    it("renders horizontal layout by default", () => {
      render(
        <DockableLayout data-testid="layout">
          <DockablePanelGroup direction="horizontal">
            <DockablePanel>Panel 1</DockablePanel>
            <DockablePanel>Panel 2</DockablePanel>
          </DockablePanelGroup>
        </DockableLayout>,
      );
      expect(screen.getByText("Panel 1")).toBeInTheDocument();
      expect(screen.getByText("Panel 2")).toBeInTheDocument();
    });

    it("renders vertical layout", () => {
      render(
        <DockableLayout>
          <DockablePanelGroup direction="vertical">
            <DockablePanel>Top</DockablePanel>
            <DockablePanel>Bottom</DockablePanel>
          </DockablePanelGroup>
        </DockableLayout>,
      );
      expect(screen.getByText("Top")).toBeInTheDocument();
      expect(screen.getByText("Bottom")).toBeInTheDocument();
    });
  });
});

describe("DockablePanelGroup", () => {
  it("renders children panels", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel>First</DockablePanel>
          <DockablePanel>Second</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("accepts autoSaveId for persistence", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal" autoSaveId="test-layout">
          <DockablePanel>Panel</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByText("Panel")).toBeInTheDocument();
  });
});

describe("DockablePanel", () => {
  it("renders with default size", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel defaultSize={30}>Sized Panel</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByText("Sized Panel")).toBeInTheDocument();
  });

  it("renders with min/max size constraints", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel minSize={10} maxSize={50}>
            Constrained Panel
          </DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByText("Constrained Panel")).toBeInTheDocument();
  });

  it("can be collapsible", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel collapsible collapsedSize={0}>
            Collapsible Panel
          </DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByText("Collapsible Panel")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel className="custom-panel" data-testid="panel">
            Styled Panel
          </DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByTestId("panel")).toHaveClass("custom-panel");
  });
});

describe("DockableResizeHandle", () => {
  it("renders between panels", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel>Left</DockablePanel>
          <DockableResizeHandle data-testid="handle" />
          <DockablePanel>Right</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByTestId("handle")).toBeInTheDocument();
  });

  it("has correct aria attributes", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel>Left</DockablePanel>
          <DockableResizeHandle data-testid="handle" />
          <DockablePanel>Right</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    const handle = screen.getByTestId("handle");
    expect(handle).toHaveAttribute("role", "separator");
  });

  it("shows visual indicator on hover", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel>Left</DockablePanel>
          <DockableResizeHandle data-testid="handle" />
          <DockablePanel>Right</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    const handle = screen.getByTestId("handle");
    expect(handle).toHaveClass("hover:bg-primary-500");
  });

  it("applies horizontal styling", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel>Left</DockablePanel>
          <DockableResizeHandle data-testid="handle" />
          <DockablePanel>Right</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    const handle = screen.getByTestId("handle");
    expect(handle).toHaveClass("w-1");
  });

  it("applies vertical styling", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="vertical">
          <DockablePanel>Top</DockablePanel>
          <DockableResizeHandle data-testid="handle" />
          <DockablePanel>Bottom</DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    const handle = screen.getByTestId("handle");
    expect(handle).toHaveClass("h-1");
  });
});

describe("Nested layouts", () => {
  it("supports nested panel groups", () => {
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel defaultSize={25}>Sidebar</DockablePanel>
          <DockableResizeHandle />
          <DockablePanel defaultSize={75}>
            <DockablePanelGroup direction="vertical">
              <DockablePanel defaultSize={70}>Main</DockablePanel>
              <DockableResizeHandle />
              <DockablePanel defaultSize={30}>Console</DockablePanel>
            </DockablePanelGroup>
          </DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );

    expect(screen.getByText("Sidebar")).toBeInTheDocument();
    expect(screen.getByText("Main")).toBeInTheDocument();
    expect(screen.getByText("Console")).toBeInTheDocument();
  });
});

describe("Panel collapse/expand", () => {
  it("supports onCollapse callback", () => {
    const onCollapse = vi.fn();
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel collapsible onCollapse={onCollapse}>
            Collapsible
          </DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByText("Collapsible")).toBeInTheDocument();
  });

  it("supports onExpand callback", () => {
    const onExpand = vi.fn();
    render(
      <DockableLayout>
        <DockablePanelGroup direction="horizontal">
          <DockablePanel collapsible onExpand={onExpand}>
            Expandable
          </DockablePanel>
        </DockablePanelGroup>
      </DockableLayout>,
    );
    expect(screen.getByText("Expandable")).toBeInTheDocument();
  });
});
