/**
 * AuthGuard Tests
 *
 * Tests for authentication route guard.
 * Uses Redux for auth state.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { AuthGuard } from "./AuthGuard";
import authReducer, {
  initialAuthState,
  AuthSliceState,
} from "../../store/slices/authSlice";
import type { User } from "../../types/auth";

// Create test store with auth state
const createTestStore = (authState: Partial<AuthSliceState> = {}) => {
  return configureStore({
    reducer: {
      auth: authReducer,
    },
    preloadedState: {
      auth: {
        ...initialAuthState,
        ...authState,
      },
    },
  });
};

// Helper to render with store
const renderWithStore = (
  authState: Partial<AuthSliceState>,
  children: React.ReactNode,
  initialPath: string = "/",
) => {
  const store = createTestStore(authState);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={[initialPath]}
        >
          {children}
        </MemoryRouter>
      </Provider>,
    ),
  };
};

describe("AuthGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show loading state during initialization", () => {
    // Arrange & Act
    renderWithStore(
      { user: null, isInitializing: true },
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    );

    // Assert
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("should redirect to login when not authenticated", () => {
    // Arrange & Act
    renderWithStore(
      { user: null, isInitializing: false },
      <Routes>
        <Route
          path="/protected"
          element={
            <AuthGuard>
              <div>Protected Content</div>
            </AuthGuard>
          }
        />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>,
      "/protected",
    );

    // Assert
    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("should render children when authenticated", () => {
    // Arrange
    const user: User = {
      id: "1",
      username: "test",
      email: "test@example.com",
      roles: [],
      persona: "user",
    };

    // Act
    renderWithStore(
      { user, isInitializing: false },
      <AuthGuard>
        <div>Protected Content</div>
      </AuthGuard>,
    );

    // Assert
    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("should redirect to custom login path when specified", () => {
    // Arrange & Act
    renderWithStore(
      { user: null, isInitializing: false },
      <Routes>
        <Route
          path="/protected"
          element={
            <AuthGuard loginPath="/auth/signin">
              <div>Protected Content</div>
            </AuthGuard>
          }
        />
        <Route path="/auth/signin" element={<div>Custom Login</div>} />
      </Routes>,
      "/protected",
    );

    // Assert
    expect(screen.getByText("Custom Login")).toBeInTheDocument();
  });
});
