/**
 * TraceCanvas Component Tests
 *
 * TDD tests for the trace visualization canvas component.
 * Tests cover:
 * - Connection status display
 * - Control panel functionality
 * - Empty state
 * - Span count display
 * - Connect/Disconnect buttons
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TraceCanvas } from './TraceCanvas';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { ReactFlowProvider } from 'reactflow';

// Mock the hooks
vi.mock('../../hooks/useTraceWebSocket', () => ({
  useTraceWebSocket: vi.fn(() => ({
    spans: [],
    events: [],
    isConnected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    clearTraces: vi.fn(),
  })),
}));

vi.mock('../../hooks/useTraceToReactFlow', () => ({
  useTraceToReactFlow: vi.fn(() => ({
    nodes: [],
    edges: [],
  })),
}));

// Mock ResizeObserver
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverMock;

// Mock store for testing
const createMockStore = () => {
  return configureStore({
    reducer: {
      ui: (state = { sidebarOpen: true }) => state,
    },
  });
};

const renderWithProviders = (component: React.ReactNode) => {
  const store = createMockStore();
  return render(
    <Provider store={store}>
      <ReactFlowProvider>{component}</ReactFlowProvider>
    </Provider>
  );
};

describe('TraceCanvas', () => {
  let mockUseTraceWebSocket: ReturnType<typeof vi.fn>;
  let mockUseTraceToReactFlow: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    const webSocketModule = await import('../../hooks/useTraceWebSocket');
    const reactFlowModule = await import('../../hooks/useTraceToReactFlow');
    mockUseTraceWebSocket = webSocketModule.useTraceWebSocket as ReturnType<typeof vi.fn>;
    mockUseTraceToReactFlow = reactFlowModule.useTraceToReactFlow as ReturnType<typeof vi.fn>;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Empty State', () => {
    it('should show empty state message when disconnected with no spans', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('Not connected')).toBeInTheDocument();
    });

    it('should show waiting message when connected with no spans', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('Waiting for traces...')).toBeInTheDocument();
    });
  });

  describe('Connection Status', () => {
    it('should show disconnected indicator when not connected', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('should show connected indicator when connected', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('should have green status dot when connected', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      const { container } = renderWithProviders(<TraceCanvas />);

      const greenDot = container.querySelector('.bg-green-500');
      expect(greenDot).toBeInTheDocument();
    });

    it('should have gray status dot when disconnected', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      const { container } = renderWithProviders(<TraceCanvas />);

      const grayDot = container.querySelector('.bg-gray-400');
      expect(grayDot).toBeInTheDocument();
    });
  });

  describe('Connect Button', () => {
    it('should show Connect button when disconnected', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('Connect')).toBeInTheDocument();
    });

    it('should call connect when Connect button is clicked', () => {
      const mockConnect = vi.fn();
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: mockConnect,
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      fireEvent.click(screen.getByText('Connect'));
      expect(mockConnect).toHaveBeenCalled();
    });

    it('should show Disconnect button when connected', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('Disconnect')).toBeInTheDocument();
    });

    it('should call disconnect when Disconnect button is clicked', () => {
      const mockDisconnect = vi.fn();
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: mockDisconnect,
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      fireEvent.click(screen.getByText('Disconnect'));
      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe('Clear Button', () => {
    it('should always show Clear button', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('Clear')).toBeInTheDocument();
    });

    it('should call clearTraces when Clear button is clicked', () => {
      const mockClearTraces = vi.fn();
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: mockClearTraces,
      });

      renderWithProviders(<TraceCanvas />);

      fireEvent.click(screen.getByText('Clear'));
      expect(mockClearTraces).toHaveBeenCalled();
    });
  });

  describe('Span and Event Count', () => {
    it('should display span count', () => {
      const mockSpans = [
        { spanId: '1', traceId: 't1', name: 'Span 1', startTime: '', status: 'OK' as const, attributes: {} },
        { spanId: '2', traceId: 't1', name: 'Span 2', startTime: '', status: 'OK' as const, attributes: {} },
      ];
      mockUseTraceWebSocket.mockReturnValue({
        spans: mockSpans,
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('2 spans | 0 events')).toBeInTheDocument();
    });

    it('should display event count', () => {
      const mockEvents = [
        { spanId: '1', name: 'Event 1', timestamp: '', attributes: {} },
        { spanId: '1', name: 'Event 2', timestamp: '', attributes: {} },
        { spanId: '1', name: 'Event 3', timestamp: '', attributes: {} },
      ];
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: mockEvents,
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas />);

      expect(screen.getByText('0 spans | 3 events')).toBeInTheDocument();
    });
  });

  describe('Props', () => {
    it('should pass sessionId to useTraceWebSocket', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas sessionId="test-session-123" />);

      expect(mockUseTraceWebSocket).toHaveBeenCalledWith(
        expect.objectContaining({ sessionId: 'test-session-123' })
      );
    });

    it('should pass autoConnect to useTraceWebSocket', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      renderWithProviders(<TraceCanvas autoConnect={true} />);

      expect(mockUseTraceWebSocket).toHaveBeenCalledWith(
        expect.objectContaining({ autoConnect: true })
      );
    });

    it('should apply custom className', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });

      const { container } = renderWithProviders(
        <TraceCanvas className="custom-class" />
      );

      const canvasDiv = container.querySelector('.custom-class');
      expect(canvasDiv).toBeInTheDocument();
    });
  });

  describe('React Flow Integration', () => {
    it('should pass nodes to useTraceToReactFlow', () => {
      const mockSpans = [
        { spanId: '1', traceId: 't1', name: 'Span 1', startTime: '', status: 'OK' as const, attributes: {} },
      ];
      mockUseTraceWebSocket.mockReturnValue({
        spans: mockSpans,
        events: [],
        isConnected: true,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });
      mockUseTraceToReactFlow.mockReturnValue({
        nodes: [],
        edges: [],
      });

      renderWithProviders(<TraceCanvas />);

      expect(mockUseTraceToReactFlow).toHaveBeenCalledWith(
        expect.objectContaining({ spans: mockSpans })
      );
    });

    it('should use horizontal layout by default', () => {
      mockUseTraceWebSocket.mockReturnValue({
        spans: [],
        events: [],
        isConnected: false,
        connect: vi.fn(),
        disconnect: vi.fn(),
        clearTraces: vi.fn(),
      });
      mockUseTraceToReactFlow.mockReturnValue({
        nodes: [],
        edges: [],
      });

      renderWithProviders(<TraceCanvas />);

      expect(mockUseTraceToReactFlow).toHaveBeenCalledWith(
        expect.objectContaining({ layout: 'horizontal' })
      );
    });
  });
});
