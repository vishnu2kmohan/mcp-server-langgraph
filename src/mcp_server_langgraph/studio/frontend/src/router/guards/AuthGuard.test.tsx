/**
 * AuthGuard Tests
 *
 * Tests for authentication route guard.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthGuard } from './AuthGuard';
import * as stores from '../../stores';

// Mock the auth store
vi.mock('../../stores', () => ({
  useAuthStore: vi.fn(),
}));

const mockUseAuthStore = stores.useAuthStore as ReturnType<typeof vi.fn>;

describe('AuthGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading state during initialization', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: null,
        isInitializing: true,
      })
    );

    // Act
    render(
      <MemoryRouter>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should redirect to login when not authenticated', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: null,
        isInitializing: false,
      })
    );

    // Act
    render(
      <MemoryRouter initialEntries={['/protected']}>
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
        </Routes>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should render children when authenticated', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: { id: '1', username: 'test', email: 'test@example.com', roles: [], persona: 'user' },
        isInitializing: false,
      })
    );

    // Act
    render(
      <MemoryRouter>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('should redirect to custom login path when specified', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: null,
        isInitializing: false,
      })
    );

    // Act
    render(
      <MemoryRouter initialEntries={['/protected']}>
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
        </Routes>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText('Custom Login')).toBeInTheDocument();
  });
});
