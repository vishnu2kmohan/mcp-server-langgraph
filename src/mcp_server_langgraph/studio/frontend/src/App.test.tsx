/**
 * App Component Tests
 *
 * TDD tests for the root application component.
 * Tests cover:
 * - Rendering
 * - Outlet integration
 * - Toaster configuration
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { App } from './App';

// Mock sonner Toaster
vi.mock('sonner', () => ({
  Toaster: ({ position }: { position: string }) => (
    <div data-testid="toaster" data-position={position}>Toast Notifications</div>
  ),
}));

describe('App', () => {
  describe('Rendering', () => {
    it('should render without crashing', () => {
      render(
        <MemoryRouter>
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Home Content')).toBeInTheDocument();
    });

    it('should render with correct root class', () => {
      const { container } = render(
        <MemoryRouter>
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const rootDiv = container.querySelector('.min-h-screen');
      expect(rootDiv).toBeInTheDocument();
    });

    it('should have dark mode classes', () => {
      const { container } = render(
        <MemoryRouter>
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const rootDiv = container.querySelector('.bg-white');
      expect(rootDiv).toBeInTheDocument();
      expect(rootDiv).toHaveClass('dark:bg-gray-900');
    });
  });

  describe('Outlet', () => {
    it('should render child routes via Outlet', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<App />}>
              <Route index element={<div data-testid="child">Child Component</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('child')).toBeInTheDocument();
    });

    it('should render different routes', () => {
      render(
        <MemoryRouter initialEntries={['/test']}>
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home</div>} />
              <Route path="test" element={<div data-testid="test-route">Test Route</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('test-route')).toBeInTheDocument();
    });
  });

  describe('Toaster', () => {
    it('should render Toaster component', () => {
      render(
        <MemoryRouter>
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByTestId('toaster')).toBeInTheDocument();
    });

    it('should have correct position', () => {
      render(
        <MemoryRouter>
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      );

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-position', 'bottom-right');
    });
  });
});
