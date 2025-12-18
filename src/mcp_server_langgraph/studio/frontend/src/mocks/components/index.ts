/**
 * Component Mocks Index
 *
 * Centralized exports for all component mocks used in tests.
 * These mocks replace third-party components that have issues
 * in the JSDOM test environment.
 */

// react-resizable-panels mock
export {
  mockReactResizablePanels,
  createMockPanelHandle,
  setupResizablePanelsMock,
  type MockPanelHandle,
} from "./react-resizable-panels";
