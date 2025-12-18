/**
 * Mock for react-resizable-panels
 *
 * This mock provides a test-friendly implementation of react-resizable-panels
 * that avoids layout calculation errors in the JSDOM test environment.
 *
 * Usage in test files:
 *
 * ```typescript
 * import { vi } from "vitest";
 * import { mockReactResizablePanels } from "../mocks/components/react-resizable-panels";
 *
 * vi.mock("react-resizable-panels", () => mockReactResizablePanels);
 * ```
 *
 * Or use the convenience function:
 *
 * ```typescript
 * import { setupResizablePanelsMock } from "../mocks/components/react-resizable-panels";
 *
 * // In the test file (before imports of components using react-resizable-panels):
 * setupResizablePanelsMock();
 * ```
 */

import React from "react";
import { vi } from "vitest";

// =============================================================================
// Types
// =============================================================================

interface PanelProps {
  children?: React.ReactNode;
  "data-testid"?: string;
  [key: string]: unknown;
}

interface PanelGroupProps {
  children?: React.ReactNode;
  "data-testid"?: string;
  [key: string]: unknown;
}

interface PanelResizeHandleProps {
  children?: React.ReactNode;
  "data-testid"?: string;
  [key: string]: unknown;
}

// =============================================================================
// Mock Imperative Handle
// =============================================================================

/**
 * Mock imperative handle for Panel refs.
 * Provides mock implementations of collapse, expand, getSize, etc.
 */
export interface MockPanelHandle {
  collapse: ReturnType<typeof vi.fn>;
  expand: ReturnType<typeof vi.fn>;
  getSize: ReturnType<typeof vi.fn>;
  isCollapsed: ReturnType<typeof vi.fn>;
  isExpanded: ReturnType<typeof vi.fn>;
  resize: ReturnType<typeof vi.fn>;
}

export const createMockPanelHandle = (): MockPanelHandle => ({
  collapse: vi.fn(),
  expand: vi.fn(),
  getSize: vi.fn(() => 20),
  isCollapsed: vi.fn(() => false),
  isExpanded: vi.fn(() => true),
  resize: vi.fn(),
});

// =============================================================================
// Mock Components
// =============================================================================

/**
 * Mock PanelGroup component.
 * Renders a simple div with data-testid="panel-group".
 */
const MockPanelGroup = ({
  children,
  ...props
}: PanelGroupProps): React.ReactElement => {
  // Filter out react-resizable-panels specific props to avoid React warnings
  const {
    direction: _direction,
    onLayout: _onLayout,
    autoSaveId: _autoSaveId,
    storage: _storage,
    ...domProps
  } = props;
  return React.createElement(
    "div",
    { "data-testid": "panel-group", ...domProps },
    children,
  );
};

/**
 * Mock Panel component with forwardRef support.
 * Renders a simple div and provides mock imperative handle via ref.
 */
const MockPanel = React.forwardRef<MockPanelHandle, PanelProps>(
  ({ children, ...props }, ref) => {
    // Create a stable mock handle
    const handleRef = React.useRef<MockPanelHandle>(createMockPanelHandle());

    // Expose mock imperative handle to parent
    React.useImperativeHandle(ref, () => handleRef.current);

    // Filter out react-resizable-panels specific props
    const {
      collapsible: _collapsible,
      collapsedSize: _collapsedSize,
      defaultSize: _defaultSize,
      minSize: _minSize,
      maxSize: _maxSize,
      onCollapse: _onCollapse,
      onExpand: _onExpand,
      onResize: _onResize,
      order: _order,
      ...restProps
    } = props;

    // Extract only safe DOM props
    const domProps: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(restProps)) {
      if (
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      ) {
        domProps[key] = value;
      }
    }

    return React.createElement(
      "div",
      {
        "data-testid": props["data-testid"] || "panel",
        ...domProps,
      },
      children as React.ReactNode,
    );
  },
);
MockPanel.displayName = "MockPanel";

/**
 * Mock PanelResizeHandle component.
 * Renders a div with role="separator" for accessibility testing.
 */
const MockPanelResizeHandle = ({
  children,
  ...props
}: PanelResizeHandleProps): React.ReactElement => {
  // Filter out react-resizable-panels specific props
  const {
    hitAreaMargins: _hitAreaMargins,
    tabIndex: _tabIndex,
    onDragging: _onDragging,
    ...domProps
  } = props;
  return React.createElement(
    "div",
    {
      "data-testid": "resize-handle",
      role: "separator",
      ...domProps,
    },
    children,
  );
};

// =============================================================================
// Mock Export Object
// =============================================================================

/**
 * Complete mock for react-resizable-panels module.
 *
 * Use with vi.mock:
 * ```typescript
 * vi.mock("react-resizable-panels", () => mockReactResizablePanels);
 * ```
 */
export const mockReactResizablePanels = {
  PanelGroup: MockPanelGroup,
  Panel: MockPanel,
  PanelResizeHandle: MockPanelResizeHandle,
  // Re-export types as mock values for any type imports
  type: {},
};

// =============================================================================
// Convenience Setup Function
// =============================================================================

/**
 * Sets up the react-resizable-panels mock.
 * Call this at the top of test files that use components with resizable panels.
 *
 * Note: Due to how vitest hoisting works, you should prefer using
 * vi.mock() directly with the mock object:
 *
 * ```typescript
 * vi.mock("react-resizable-panels", () => mockReactResizablePanels);
 * ```
 */
export const setupResizablePanelsMock = (): void => {
  vi.mock("react-resizable-panels", () => mockReactResizablePanels);
};

export default mockReactResizablePanels;
