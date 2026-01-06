/**
 * Shared fixtures and test utilities for ConnectedCanvasPanel tests
 *
 * This file contains common test data, mocks, and render helpers
 * used across all ConnectedCanvasPanel test shards.
 */
import React from "react";
import { render as _render } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter, Routes, Route, Outlet } from "react-router";
import { vi } from "vitest";
import canvasReducer from "../../store/slices/canvasSlice";
import type { CanvasArtifact } from "../../types/artifacts";
import type { ChatLoaderData } from "../../router/loaders";

// =============================================================================
// Mock Loader Data
// =============================================================================

export const mockSessionLoaderData: ChatLoaderData = {
  sessionId: "session-123",
  messages: [],
  artifacts: [],
};

// =============================================================================
// Mock Artifacts
// =============================================================================

export const createMockArtifact = (
  overrides: Partial<CanvasArtifact> = {},
): CanvasArtifact => ({
  id: "artifact-1",
  type: "code",
  title: "Test Artifact",
  sessionId: "session-123",
  version: 1,
  content: "console.log('hello');",
  contentType: "code",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  editMetadata: {
    editedBy: "user",
    language: "javascript",
  },
  ...overrides,
});

// =============================================================================
// Store Creation
// =============================================================================

interface TestStorePreloadedState {
  canvas?: Partial<ReturnType<typeof canvasReducer>>;
}

export const createTestStore = (preloadedState?: TestStorePreloadedState) => {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
    },
    preloadedState: preloadedState
      ? {
          canvas: {
            ...canvasReducer(undefined, { type: "@@INIT" }),
            ...preloadedState.canvas,
          } as ReturnType<typeof canvasReducer>,
        }
      : undefined,
  });
};

// =============================================================================
// Test Wrapper
// =============================================================================

interface WrapperProps {
  children: React.ReactNode;
}

export const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: WrapperProps) {
    return (
      <Provider store={store}>
        <MemoryRouter>
          <Routes>
            <Route
              path="/"
              element={
                <div data-testid="router-wrapper">
                  {children}
                  <Outlet />
                </div>
              }
            >
              <Route
                path="nested"
                element={<div data-testid="nested-route">Nested Content</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>
      </Provider>
    );
  };
};

// =============================================================================
// Test Utilities
// =============================================================================

export const flushPromises = () =>
  new Promise<void>((resolve) => setTimeout(resolve, 10));

// =============================================================================
// Mock Setup Functions
// =============================================================================

export const setupSuccessfulFetchMock = () => {
  return vi.spyOn(global, "fetch").mockImplementation(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      statusText: "OK",
      json: () => Promise.resolve({ id: "artifact-1", version: 2 }),
    } as Response),
  );
};

export const setupFailedFetchMock = () => {
  return vi.spyOn(global, "fetch").mockImplementation((url) => {
    const urlStr = typeof url === "string" ? url : url.toString();
    if (urlStr.includes("/api/v1/artifacts/")) {
      return Promise.resolve({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      } as Response);
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ suggestions: [] }),
    } as Response);
  });
};

export const setupNetworkErrorFetchMock = () => {
  return vi.spyOn(global, "fetch").mockImplementation((url) => {
    const urlStr = typeof url === "string" ? url : url.toString();
    if (urlStr.includes("/api/v1/artifacts/")) {
      return Promise.reject(new Error("Network error"));
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ suggestions: [] }),
    } as Response);
  });
};

export const setupAuthTokenMock = () => {
  const originalGetItem = Storage.prototype.getItem;
  Storage.prototype.getItem = vi.fn((key) => {
    if (key === "access_token") return "test-token";
    return null;
  });
  return () => {
    Storage.prototype.getItem = originalGetItem;
  };
};
