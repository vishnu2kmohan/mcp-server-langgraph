/**
 * PersonaGuard Tests
 *
 * Tests for persona-based route guard.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { PersonaGuard } from './PersonaGuard';
import * as stores from '../../stores';

// Mock the auth store
vi.mock('../../stores', () => ({
  useAuthStore: vi.fn(),
}));

const mockUseAuthStore = stores.useAuthStore as ReturnType<typeof vi.fn>;

describe('PersonaGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render null when no user (let AuthGuard handle)', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: null,
      })
    );

    // Act
    const { container } = render(
      <MemoryRouter>
        <PersonaGuard allowedPersonas={['admin']}>
          <div>Admin Content</div>
        </PersonaGuard>
      </MemoryRouter>
    );

    // Assert
    expect(container.innerHTML).toBe('');
  });

  it('should render children when user has allowed persona', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: { id: '1', username: 'admin', persona: 'admin' },
      })
    );

    // Act
    render(
      <MemoryRouter>
        <PersonaGuard allowedPersonas={['admin']}>
          <div>Admin Content</div>
        </PersonaGuard>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText('Admin Content')).toBeInTheDocument();
  });

  it('should render children when user has one of multiple allowed personas', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: { id: '1', username: 'dev', persona: 'developer' },
      })
    );

    // Act
    render(
      <MemoryRouter>
        <PersonaGuard allowedPersonas={['admin', 'developer']}>
          <div>Dev or Admin Content</div>
        </PersonaGuard>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText('Dev or Admin Content')).toBeInTheDocument();
  });

  it('should redirect to fallback path when persona not allowed', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: { id: '1', username: 'user', persona: 'user' },
      })
    );

    // Act
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <PersonaGuard allowedPersonas={['admin']} fallbackPath="/unauthorized">
                <div>Admin Content</div>
              </PersonaGuard>
            }
          />
          <Route path="/unauthorized" element={<div>Unauthorized</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Assert
    expect(screen.getByText('Unauthorized')).toBeInTheDocument();
    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
  });

  it('should redirect to persona default route when no fallback specified', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: { id: '1', username: 'user', persona: 'user' },
      })
    );

    // Act
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <PersonaGuard allowedPersonas={['admin']}>
                <div>Admin Content</div>
              </PersonaGuard>
            }
          />
          <Route path="/studio/chat" element={<div>User Chat</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Assert - user persona defaults to /studio/chat
    expect(screen.getByText('User Chat')).toBeInTheDocument();
  });

  it('should redirect developer to workflows when accessing admin', () => {
    // Arrange
    mockUseAuthStore.mockImplementation((selector) =>
      selector({
        user: { id: '1', username: 'dev', persona: 'developer' },
      })
    );

    // Act
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <PersonaGuard allowedPersonas={['admin']}>
                <div>Admin Content</div>
              </PersonaGuard>
            }
          />
          <Route path="/studio/workflows" element={<div>Developer Workflows</div>} />
        </Routes>
      </MemoryRouter>
    );

    // Assert - developer persona defaults to /studio/workflows
    expect(screen.getByText('Developer Workflows')).toBeInTheDocument();
  });
});
