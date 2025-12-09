/**
 * TracePanel Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TracePanel } from './TracePanel';
import type { TraceInfo } from '../../api/types';

describe('TracePanel', () => {
  const mockTraces: TraceInfo[] = [
    {
      traceId: 'trace-1',
      spans: [
        { spanId: 'span-1', operationName: 'agent_chat', serviceName: 'playground', startTime: '2025-01-01T10:00:00Z', durationMs: 1500, status: 'OK' },
      ],
      startTime: '2025-01-01T10:00:00Z',
      totalDurationMs: 1500,
    },
  ];

  it('should_render_trace_list', () => {
    render(<TracePanel traces={mockTraces} />);
    expect(screen.getByText(/trace-1/i)).toBeInTheDocument();
  });

  it('should_show_empty_state_when_no_traces', () => {
    render(<TracePanel traces={[]} />);
    expect(screen.getByText(/no traces/i)).toBeInTheDocument();
  });

  it('should_show_loading_state', () => {
    render(<TracePanel traces={[]} isLoading />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('should_display_trace_duration', () => {
    render(<TracePanel traces={mockTraces} />);
    // 1500ms >= 1000ms is formatted as seconds: "1.50s"
    expect(screen.getByText(/1\.50s/i)).toBeInTheDocument();
  });
});
