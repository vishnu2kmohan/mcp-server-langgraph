/**
 * TraceWaterfall Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TraceWaterfall } from './TraceWaterfall';
import type { SpanInfo } from '../../api/types';

describe('TraceWaterfall', () => {
  const mockSpans: SpanInfo[] = [
    { spanId: 'span-1', operationName: 'agent_chat', serviceName: 'playground', startTime: '2025-01-01T10:00:00.000Z', endTime: '2025-01-01T10:00:01.500Z', durationMs: 1500, status: 'OK' },
    { spanId: 'span-2', parentSpanId: 'span-1', operationName: 'llm_call', serviceName: 'llm', startTime: '2025-01-01T10:00:00.100Z', endTime: '2025-01-01T10:00:01.000Z', durationMs: 900, status: 'OK' },
  ];

  it('should_render_all_spans', () => {
    render(<TraceWaterfall spans={mockSpans} totalDuration={1500} />);
    expect(screen.getByText('agent_chat')).toBeInTheDocument();
    expect(screen.getByText('llm_call')).toBeInTheDocument();
  });

  it('should_show_span_duration', () => {
    render(<TraceWaterfall spans={mockSpans} totalDuration={1500} />);
    expect(screen.getByText(/1500ms/)).toBeInTheDocument();
  });

  it('should_show_empty_state_when_no_spans', () => {
    render(<TraceWaterfall spans={[]} totalDuration={0} />);
    expect(screen.getByText(/no spans/i)).toBeInTheDocument();
  });

  it('should_render_waterfall_bars', () => {
    render(<TraceWaterfall spans={mockSpans} totalDuration={1500} />);
    const bars = screen.getAllByTestId('span-bar');
    expect(bars).toHaveLength(2);
  });
});
