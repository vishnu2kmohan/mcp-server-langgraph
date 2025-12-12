/**
 * App Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from './App';

// Mock all child components
vi.mock('./contexts/MCPHostContext', () => ({
  MCPHostProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useMCPHost: () => ({
    servers: new Map(),
    pendingElicitations: [],
    pendingSamplingRequests: [],
    addServer: vi.fn(),
    removeServer: vi.fn(),
    allTools: [],
    allResources: [],
    allPrompts: [],
  }),
}));

vi.mock('./components/Layout', () => ({
  Header: () => <header data-testid="header">Header</header>,
  Sidebar: ({ children }: { children: React.ReactNode }) => (
    <aside data-testid="sidebar">{children}</aside>
  ),
}));

vi.mock('./components/Sessions', () => ({
  SessionList: () => <div data-testid="session-list">Sessions</div>,
  CreateSessionModal: () => null,
}));

vi.mock('./hooks/useSession', () => ({
  useSession: () => ({
    sessions: [],
    activeSession: null,
    isLoading: false,
    error: null,
    loadSessions: vi.fn(),
    createSession: vi.fn(),
    selectSession: vi.fn(),
    deleteSession: vi.fn(),
    clearActiveSession: vi.fn(),
  }),
}));

vi.mock('./components/Chat', () => ({
  ChatInterface: () => <div data-testid="chat-interface">Chat</div>,
}));

vi.mock('./components/Observability', () => ({
  ObservabilityTabs: () => <div data-testid="observability-tabs">Observability</div>,
}));

vi.mock('./components/MCP', () => ({
  ElicitationDialog: () => null,
  SamplingDialog: () => null,
}));

vi.mock('./hooks/useMCPElicitation', () => ({
  useMCPElicitation: () => ({
    pendingElicitation: null,
    accept: vi.fn(),
    decline: vi.fn(),
    cancel: vi.fn(),
  }),
}));

vi.mock('./hooks/useMCPSampling', () => ({
  useMCPSampling: () => ({
    pendingSamplingRequest: null,
    approveSampling: vi.fn(),
    rejectSampling: vi.fn(),
  }),
}));

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_render_header', () => {
    render(<App />);
    expect(screen.getByTestId('header')).toBeInTheDocument();
  });

  it('should_render_sidebar', () => {
    render(<App />);
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('should_render_session_list', () => {
    render(<App />);
    expect(screen.getByTestId('session-list')).toBeInTheDocument();
  });

  it('should_render_chat_interface', () => {
    render(<App />);
    expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
  });

  it('should_render_observability_tabs', () => {
    render(<App />);
    expect(screen.getByTestId('observability-tabs')).toBeInTheDocument();
  });

  it('should_have_main_layout_structure', () => {
    render(<App />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('should_apply_full_height_layout', () => {
    const { container } = render(<App />);
    const appRoot = container.firstChild;
    expect(appRoot).toHaveClass('h-screen');
  });
});
