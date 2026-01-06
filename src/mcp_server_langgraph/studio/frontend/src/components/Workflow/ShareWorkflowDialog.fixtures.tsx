/**
 * ShareWorkflowDialog Test Fixtures
 *
 * Extracted from ShareWorkflowDialog.test.tsx for OOM prevention.
 * See: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md
 */
import { vi } from "vitest";
import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type React from "react";

// Mock navigator.clipboard
export const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};

// Mock RTK Query hooks
export const mockAddShareUnwrap = vi.fn();
export const mockRemoveShareUnwrap = vi.fn();
export const mockUpdatePublicUnwrap = vi.fn();

export const mockAddShare = vi.fn(() => ({ unwrap: mockAddShareUnwrap }));
export const mockRemoveShare = vi.fn(() => ({ unwrap: mockRemoveShareUnwrap }));
export const mockUpdatePublic = vi.fn(() => ({
  unwrap: mockUpdatePublicUnwrap,
}));

// Default shares data - camelCase per ADR-0091 Phase 6
export const defaultSharesData = {
  shares: [
    {
      userId: "user-1",
      email: "alice@example.com",
      permission: "edit" as const,
    },
    {
      userId: "user-2",
      email: "bob@example.com",
      permission: "view" as const,
    },
  ],
  isPublic: false,
  shareLink: null,
};

// Create a minimal store for testing
export const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

// Helper to render with Redux provider
export const renderWithProvider = (component: React.ReactNode) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

// Mock workflow for tests
export const mockWorkflow = {
  id: "wf-1",
  name: "Test Workflow",
};

// Setup default mock returns
export function setupDefaultMocks() {
  mockAddShareUnwrap.mockResolvedValue({ success: true });
  mockRemoveShareUnwrap.mockResolvedValue(undefined);
  mockUpdatePublicUnwrap.mockResolvedValue({
    isPublic: true,
    shareLink: "https://example.com/share/abc123",
  });
}
