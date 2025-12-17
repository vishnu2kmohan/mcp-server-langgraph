/**
 * SplitContainer Component Tests
 *
 * TDD tests for the recursive split layout container.
 * Tests cover:
 * - Basic rendering of tab groups
 * - Horizontal split rendering
 * - Vertical split rendering
 * - Nested splits (tree structure)
 * - Split drop zone indicators
 * - Resizable split panels
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

// Mock react-resizable-panels
vi.mock("react-resizable-panels", () => ({
  Panel: ({
    children,
    className,
    defaultSize,
  }: {
    children: React.ReactNode;
    className?: string;
    defaultSize?: number;
  }) => (
    <div
      data-testid="resizable-panel"
      data-default-size={defaultSize}
      className={className}
    >
      {children}
    </div>
  ),
  PanelGroup: ({
    children,
    direction,
    className,
  }: {
    children: React.ReactNode;
    direction: string;
    className?: string;
  }) => (
    <div
      data-testid="panel-group"
      data-direction={direction}
      className={className}
    >
      {children}
    </div>
  ),
  PanelResizeHandle: ({ className }: { className?: string }) => (
    <div data-testid="resize-handle" className={className} />
  ),
}));

// Import after mocks
import { SplitContainer } from "./SplitContainer";
import workspaceReducer, {
  type WorkspaceState,
  type DockLayout,
  type TabState,
} from "../../store/slices/workspaceSlice";

// Default workspace state for tests
const defaultWorkspaceState: WorkspaceState = {
  version: 1,
  leftSidebarWidth: 280,
  leftSidebarCollapsed: false,
  rightSidebarWidth: 280,
  rightSidebarCollapsed: false,
  bottomPanelHeight: 200,
  bottomPanelCollapsed: true,
  activeActivityId: "conversations",
  dockLayout: { type: "tab-group", tabIds: [] },
  tabs: [],
  activeTabId: null,
  focusMode: false,
  expandedGroups: [],
  expandedPropertySections: [],
  bottomPanelActiveTab: "activity",
  scrollPositions: {},
  lastUpdated: 0,
};

// Create a test store
function createTestStore(
  overrides: {
    workspace?: Partial<WorkspaceState>;
  } = {},
) {
  return configureStore({
    reducer: {
      workspace: workspaceReducer,
    },
    preloadedState: {
      workspace: { ...defaultWorkspaceState, ...overrides.workspace },
    },
  });
}

// Render helper with providers
function renderWithProviders(
  ui: React.ReactElement,
  options: {
    store?: ReturnType<typeof createTestStore>;
    workspaceOverrides?: Partial<WorkspaceState>;
  } = {},
) {
  const store =
    options.store ??
    createTestStore({
      workspace: options.workspaceOverrides ?? {},
    });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("SplitContainer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render the split container", () => {
      const layout: DockLayout = { type: "tab-group", tabIds: [] };
      renderWithProviders(<SplitContainer layout={layout} />);
      expect(screen.getByTestId("split-container")).toBeInTheDocument();
    });

    it("should render tab group layout", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "chat", title: "Chat 2" },
      ];
      const layout: DockLayout = {
        type: "tab-group",
        tabIds: ["tab-1", "tab-2"],
      };

      renderWithProviders(<SplitContainer layout={layout} />, {
        workspaceOverrides: { tabs, activeTabId: "tab-1" },
      });

      expect(screen.getByTestId("tab-group")).toBeInTheDocument();
    });
  });

  describe("horizontal splits", () => {
    it("should render horizontal split with two panels", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const layout: DockLayout = {
        type: "horizontal-split",
        sizes: [50, 50],
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
      };

      renderWithProviders(<SplitContainer layout={layout} />, {
        workspaceOverrides: { tabs, activeTabId: "tab-1" },
      });

      const panelGroup = screen.getByTestId("panel-group");
      expect(panelGroup).toHaveAttribute("data-direction", "horizontal");
      expect(screen.getAllByTestId("resizable-panel")).toHaveLength(2);
      expect(screen.getByTestId("resize-handle")).toBeInTheDocument();
    });

    it("should apply sizes to horizontal split panels", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const layout: DockLayout = {
        type: "horizontal-split",
        sizes: [30, 70],
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
      };

      renderWithProviders(<SplitContainer layout={layout} />, {
        workspaceOverrides: { tabs, activeTabId: "tab-1" },
      });

      const panels = screen.getAllByTestId("resizable-panel");
      expect(panels[0]).toHaveAttribute("data-default-size", "30");
      expect(panels[1]).toHaveAttribute("data-default-size", "70");
    });
  });

  describe("vertical splits", () => {
    it("should render vertical split with two panels", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const layout: DockLayout = {
        type: "vertical-split",
        sizes: [50, 50],
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
      };

      renderWithProviders(<SplitContainer layout={layout} />, {
        workspaceOverrides: { tabs, activeTabId: "tab-1" },
      });

      const panelGroup = screen.getByTestId("panel-group");
      expect(panelGroup).toHaveAttribute("data-direction", "vertical");
    });
  });

  describe("nested splits (tree structure)", () => {
    it("should render nested splits correctly", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
        { id: "tab-3", type: "settings", title: "Settings" },
      ];

      // Nested layout: horizontal split with left panel and right vertical split
      const layout: DockLayout = {
        type: "horizontal-split",
        sizes: [50, 50],
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          {
            type: "vertical-split",
            sizes: [50, 50],
            children: [
              { type: "tab-group", tabIds: ["tab-2"] },
              { type: "tab-group", tabIds: ["tab-3"] },
            ],
          },
        ],
      };

      renderWithProviders(<SplitContainer layout={layout} />, {
        workspaceOverrides: { tabs, activeTabId: "tab-1" },
      });

      // Should have 2 panel groups (outer horizontal, inner vertical)
      const panelGroups = screen.getAllByTestId("panel-group");
      expect(panelGroups).toHaveLength(2);

      // First should be horizontal, second should be vertical
      expect(panelGroups[0]).toHaveAttribute("data-direction", "horizontal");
      expect(panelGroups[1]).toHaveAttribute("data-direction", "vertical");
    });

    it("should render deeply nested splits", () => {
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "chat", title: "Chat 2" },
        { id: "tab-3", type: "chat", title: "Chat 3" },
        { id: "tab-4", type: "chat", title: "Chat 4" },
      ];

      // 3 levels deep
      const layout: DockLayout = {
        type: "horizontal-split",
        sizes: [50, 50],
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          {
            type: "vertical-split",
            sizes: [50, 50],
            children: [
              { type: "tab-group", tabIds: ["tab-2"] },
              {
                type: "horizontal-split",
                sizes: [50, 50],
                children: [
                  { type: "tab-group", tabIds: ["tab-3"] },
                  { type: "tab-group", tabIds: ["tab-4"] },
                ],
              },
            ],
          },
        ],
      };

      renderWithProviders(<SplitContainer layout={layout} />, {
        workspaceOverrides: { tabs, activeTabId: "tab-1" },
      });

      // Should have 3 panel groups
      const panelGroups = screen.getAllByTestId("panel-group");
      expect(panelGroups).toHaveLength(3);
    });
  });

  describe("split drop zones", () => {
    it("should show drop zones when dragging tab", () => {
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(
        <SplitContainer layout={layout} isDragging={true} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      // Should show 4 drop zones (top, right, bottom, left)
      const dropZones = screen.getAllByTestId(/drop-zone-/);
      expect(dropZones).toHaveLength(4);
    });

    it("should not show drop zones when not dragging", () => {
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(
        <SplitContainer layout={layout} isDragging={false} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      expect(screen.queryByTestId(/drop-zone-/)).not.toBeInTheDocument();
    });

    it("should highlight drop zone on hover", () => {
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(
        <SplitContainer layout={layout} isDragging={true} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      const leftDropZone = screen.getByTestId("drop-zone-left");
      fireEvent.dragOver(leftDropZone);

      expect(leftDropZone).toHaveClass("bg-primary-500/20");
    });

    it("should call onSplit when dropping on zone", () => {
      const onSplit = vi.fn();
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(
        <SplitContainer layout={layout} isDragging={true} onSplit={onSplit} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      const leftDropZone = screen.getByTestId("drop-zone-left");

      // Simulate drop
      const dataTransfer = { getData: () => "tab-2" };
      fireEvent.drop(leftDropZone, { dataTransfer });

      expect(onSplit).toHaveBeenCalledWith({
        direction: "horizontal",
        position: "before",
        sourceTabId: "tab-2",
      });
    });

    it("should show split indicator icon on drop zone hover", () => {
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(
        <SplitContainer layout={layout} isDragging={true} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      // All drop zones should have indicator icons
      expect(screen.getByTestId("drop-zone-left")).toBeInTheDocument();
      expect(screen.getByTestId("drop-zone-right")).toBeInTheDocument();
      expect(screen.getByTestId("drop-zone-top")).toBeInTheDocument();
      expect(screen.getByTestId("drop-zone-bottom")).toBeInTheDocument();
    });

    it("should show visual preview border when hovering over drop zone", () => {
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(
        <SplitContainer layout={layout} isDragging={true} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      const rightDropZone = screen.getByTestId("drop-zone-right");
      fireEvent.dragOver(rightDropZone);

      // Should show visual indicator border
      expect(rightDropZone).toHaveClass("bg-primary-500/20");
    });
  });

  describe("resize callbacks", () => {
    it("should call onResize when panel is resized", () => {
      const onResize = vi.fn();
      const tabs: TabState[] = [
        { id: "tab-1", type: "chat", title: "Chat 1" },
        { id: "tab-2", type: "workflow", title: "Workflow 1" },
      ];
      const layout: DockLayout = {
        type: "horizontal-split",
        sizes: [50, 50],
        children: [
          { type: "tab-group", tabIds: ["tab-1"] },
          { type: "tab-group", tabIds: ["tab-2"] },
        ],
      };

      renderWithProviders(
        <SplitContainer layout={layout} onResize={onResize} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      expect(screen.getByTestId("resize-handle")).toBeInTheDocument();
    });
  });

  describe("content rendering", () => {
    it("should render custom content via renderTabContent prop", () => {
      const renderTabContent = vi.fn((tab: TabState) => (
        <div data-testid={`content-${tab.id}`}>Content for {tab.title}</div>
      ));

      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(
        <SplitContainer layout={layout} renderTabContent={renderTabContent} />,
        { workspaceOverrides: { tabs, activeTabId: "tab-1" } },
      );

      expect(renderTabContent).toHaveBeenCalled();
      expect(screen.getByTestId("content-tab-1")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper ARIA structure", () => {
      const tabs: TabState[] = [{ id: "tab-1", type: "chat", title: "Chat 1" }];
      const layout: DockLayout = { type: "tab-group", tabIds: ["tab-1"] };

      renderWithProviders(<SplitContainer layout={layout} />, {
        workspaceOverrides: { tabs, activeTabId: "tab-1" },
      });

      expect(screen.getByTestId("split-container")).toBeInTheDocument();
    });
  });
});
