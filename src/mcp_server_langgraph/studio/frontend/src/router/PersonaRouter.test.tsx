/**
 * PersonaRouter Tests
 *
 * Tests for persona-based routing that directs users to appropriate sections.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PersonaRouter } from './PersonaRouter';
import { usePersonaStore } from '../stores/personaStore';
import { useAuthStore } from '../stores/authStore';

// Mock the stores
vi.mock('../stores/personaStore', () => ({
  usePersonaStore: vi.fn(),
}));

vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(),
}));

const mockPersonaStore = usePersonaStore as ReturnType<typeof vi.fn>;
const mockAuthStore = useAuthStore as ReturnType<typeof vi.fn>;

describe('PersonaRouter', () => {
  const AdminDashboard = () => <div>Admin Dashboard</div>;
  const StudioWorkflows = () => <div>Studio Workflows</div>;
  const StudioChat = () => <div>Studio Chat</div>;
  const NotAuthorized = () => <div>Not Authorized</div>;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock authStore with selector support
    const authState = {
      user: { id: 'user-1', roles: ['user'] },
    };
    mockAuthStore.mockImplementation((selector?: (state: typeof authState) => unknown) => {
      if (selector) {
        return selector(authState);
      }
      return authState;
    });

    mockPersonaStore.mockReturnValue({
      persona: 'user',
      getDefaultRoute: () => '/studio/chat',
      canAccessRoute: (route: string) => route.startsWith('/studio/chat'),
    });
  });

  const renderWithRouter = (initialPath: string) => {
    return render(
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/*" element={<PersonaRouter />}>
            <Route path="admin/*">
              <Route path="dashboard" element={<AdminDashboard />} />
            </Route>
            <Route path="studio/*">
              <Route path="workflows" element={<StudioWorkflows />} />
              <Route path="chat" element={<StudioChat />} />
            </Route>
            <Route path="not-authorized" element={<NotAuthorized />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
  };

  describe('Default Routing', () => {
    it('should redirect admin to admin dashboard on root path', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'admin',
        getDefaultRoute: () => '/admin/dashboard',
        canAccessRoute: () => true,
      });

      renderWithRouter('/');

      await waitFor(() => {
        expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
      });
    });

    it('should redirect developer to studio workflows on root path', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'developer',
        getDefaultRoute: () => '/studio/workflows',
        canAccessRoute: (route: string) =>
          route.startsWith('/studio/'),
      });

      renderWithRouter('/');

      await waitFor(() => {
        expect(screen.getByText('Studio Workflows')).toBeInTheDocument();
      });
    });

    it('should redirect user to studio chat on root path', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'user',
        getDefaultRoute: () => '/studio/chat',
        canAccessRoute: (route: string) =>
          route === '/studio/chat' || route === '/studio/sessions',
      });

      renderWithRouter('/');

      await waitFor(() => {
        expect(screen.getByText('Studio Chat')).toBeInTheDocument();
      });
    });
  });

  describe('Access Control', () => {
    it('should allow admin to access admin routes', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'admin',
        getDefaultRoute: () => '/admin/dashboard',
        canAccessRoute: () => true,
      });

      renderWithRouter('/admin/dashboard');

      await waitFor(() => {
        expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
      });
    });

    it('should redirect developer away from admin routes', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'developer',
        getDefaultRoute: () => '/studio/workflows',
        canAccessRoute: (route: string) =>
          route.startsWith('/studio/'),
      });

      renderWithRouter('/admin/dashboard');

      await waitFor(() => {
        expect(screen.getByText('Not Authorized')).toBeInTheDocument();
      });
    });

    it('should redirect user away from developer routes', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'user',
        getDefaultRoute: () => '/studio/chat',
        canAccessRoute: (route: string) =>
          route === '/studio/chat' || route === '/studio/sessions',
      });

      renderWithRouter('/studio/workflows');

      await waitFor(() => {
        expect(screen.getByText('Not Authorized')).toBeInTheDocument();
      });
    });

    it('should allow user to access chat', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'user',
        getDefaultRoute: () => '/studio/chat',
        canAccessRoute: (route: string) =>
          route === '/studio/chat' || route === '/studio/sessions',
      });

      renderWithRouter('/studio/chat');

      await waitFor(() => {
        expect(screen.getByText('Studio Chat')).toBeInTheDocument();
      });
    });
  });

  describe('Authentication Check', () => {
    it('should redirect to login when not authenticated', async () => {
      const authState = { user: null };
      mockAuthStore.mockImplementation((selector?: (state: typeof authState) => unknown) => {
        if (selector) {
          return selector(authState);
        }
        return authState;
      });

      renderWithRouter('/studio/workflows');

      await waitFor(() => {
        // PersonaRouter should trigger auth redirect
        expect(screen.queryByText('Studio Workflows')).not.toBeInTheDocument();
      });
    });
  });

  describe('Route Persistence', () => {
    it('should allow navigation within allowed routes', async () => {
      mockPersonaStore.mockReturnValue({
        persona: 'developer',
        getDefaultRoute: () => '/studio/workflows',
        canAccessRoute: (route: string) =>
          route.startsWith('/studio/'),
      });

      renderWithRouter('/studio/workflows');

      await waitFor(() => {
        expect(screen.getByText('Studio Workflows')).toBeInTheDocument();
      });
    });
  });
});
