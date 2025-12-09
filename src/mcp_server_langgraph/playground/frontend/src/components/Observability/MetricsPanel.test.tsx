/**
 * MetricsPanel Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricsPanel } from './MetricsPanel';
import type { MetricsSummary } from '../../api/types';

describe('MetricsPanel', () => {
  const mockMetrics: MetricsSummary = {
    llm: {
      totalCalls: 10,
      totalTokens: 5000,
      promptTokens: 3000,
      completionTokens: 2000,
      averageLatencyMs: 1500,
      p50LatencyMs: 1200,
      p99LatencyMs: 3000,
      errorRate: 0.05,
    },
    tools: {
      totalCalls: 5,
      successRate: 0.9,
      averageLatencyMs: 500,
      errorCount: 1,
      byTool: {},
    },
    sessionDurationMs: 60000,
    messageCount: 20,
  };

  it('should_render_llm_metrics', () => {
    render(<MetricsPanel metrics={mockMetrics} />);
    expect(screen.getByText('10')).toBeInTheDocument(); // totalCalls
    expect(screen.getByText('5,000')).toBeInTheDocument(); // totalTokens
  });

  it('should_render_tool_metrics', () => {
    render(<MetricsPanel metrics={mockMetrics} />);
    expect(screen.getByText('5')).toBeInTheDocument(); // tool calls
    expect(screen.getByText('90%')).toBeInTheDocument(); // success rate
  });

  it('should_show_loading_state', () => {
    render(<MetricsPanel metrics={null} isLoading />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('should_show_empty_state_when_no_metrics', () => {
    render(<MetricsPanel metrics={null} />);
    expect(screen.getByText(/no metrics/i)).toBeInTheDocument();
  });
});
