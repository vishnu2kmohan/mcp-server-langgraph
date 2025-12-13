/**
 * Sidebar Tests
 *
 * Tests for sidebar navigation component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from './Sidebar';

// Mock useLocation
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useLocation: vi.fn(() => ({ pathname: '/studio/chat' })),
  };
});

describe('Sidebar', () => {
  describe('Navigation Links', () => {
    it('should render Chat navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /chat/i })).toBeInTheDocument();
    });

    it('should render Sessions navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /sessions/i })).toBeInTheDocument();
    });

    it('should render Workflows navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /workflows/i })).toBeInTheDocument();
    });

    it('should render MCP navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /mcp/i })).toBeInTheDocument();
    });

    it('should render Observability navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /observability/i })).toBeInTheDocument();
    });

    it('should render Cost navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /cost/i })).toBeInTheDocument();
    });

    it('should render Settings navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /settings/i })).toBeInTheDocument();
    });

    it('should render Admin Dashboard navigation link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /admin/i })).toBeInTheDocument();
    });
  });

  describe('Active Link Highlighting', () => {
    it('should highlight Chat link when on chat page', () => {
      render(
        <MemoryRouter initialEntries={['/studio/chat']}>
          <Sidebar />
        </MemoryRouter>
      );

      const chatLink = screen.getByRole('link', { name: /chat/i });
      expect(chatLink.className).toMatch(/bg-blue/);
    });

    it('should highlight Workflows link when on workflows page', () => {
      render(
        <MemoryRouter initialEntries={['/studio/workflows']}>
          <Sidebar />
        </MemoryRouter>
      );

      const workflowsLink = screen.getByRole('link', { name: /workflows/i });
      expect(workflowsLink.className).toMatch(/bg-blue/);
    });
  });

  describe('Link Navigation', () => {
    it('should have correct href for Chat link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const chatLink = screen.getByRole('link', { name: /chat/i });
      expect(chatLink).toHaveAttribute('href', '/studio/chat');
    });

    it('should have correct href for Sessions link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const sessionsLink = screen.getByRole('link', { name: /sessions/i });
      expect(sessionsLink).toHaveAttribute('href', '/studio/sessions');
    });

    it('should have correct href for Workflows link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const workflowsLink = screen.getByRole('link', { name: /workflows/i });
      expect(workflowsLink).toHaveAttribute('href', '/studio/workflows');
    });

    it('should have correct href for MCP link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const mcpLink = screen.getByRole('link', { name: /mcp/i });
      expect(mcpLink).toHaveAttribute('href', '/studio/mcp');
    });

    it('should have correct href for Observability link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const observabilityLink = screen.getByRole('link', { name: /observability/i });
      expect(observabilityLink).toHaveAttribute('href', '/studio/observability');
    });

    it('should have correct href for Cost link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const costLink = screen.getByRole('link', { name: /cost/i });
      expect(costLink).toHaveAttribute('href', '/studio/cost');
    });

    it('should have correct href for Settings link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const settingsLink = screen.getByRole('link', { name: /settings/i });
      expect(settingsLink).toHaveAttribute('href', '/studio/settings');
    });

    it('should have correct href for Admin Dashboard link', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      const adminLink = screen.getByRole('link', { name: /admin/i });
      expect(adminLink).toHaveAttribute('href', '/admin/dashboard');
    });
  });

  describe('Sidebar Layout', () => {
    it('should render as navigation element', () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });
});
