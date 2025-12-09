/**
 * ObservabilityTabs Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ObservabilityTabs } from './ObservabilityTabs';

// Mock child components
vi.mock('./TracePanel', () => ({
  TracePanel: () => <div data-testid="trace-panel">Traces</div>,
}));
vi.mock('./LogPanel', () => ({
  LogPanel: () => <div data-testid="log-panel">Logs</div>,
}));
vi.mock('./MetricsPanel', () => ({
  MetricsPanel: () => <div data-testid="metrics-panel">Metrics</div>,
}));
vi.mock('./AlertPanel', () => ({
  AlertPanel: () => <div data-testid="alert-panel">Alerts</div>,
}));

describe('ObservabilityTabs', () => {
  it('should_render_tab_buttons', () => {
    render(<ObservabilityTabs />);
    expect(screen.getByRole('tab', { name: /traces/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /logs/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /metrics/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /alerts/i })).toBeInTheDocument();
  });

  it('should_show_traces_by_default', () => {
    render(<ObservabilityTabs />);
    expect(screen.getByTestId('trace-panel')).toBeInTheDocument();
  });

  it('should_switch_to_logs_tab', () => {
    render(<ObservabilityTabs />);
    fireEvent.click(screen.getByRole('tab', { name: /logs/i }));
    expect(screen.getByTestId('log-panel')).toBeInTheDocument();
  });

  it('should_switch_to_metrics_tab', () => {
    render(<ObservabilityTabs />);
    fireEvent.click(screen.getByRole('tab', { name: /metrics/i }));
    expect(screen.getByTestId('metrics-panel')).toBeInTheDocument();
  });

  it('should_switch_to_alerts_tab', () => {
    render(<ObservabilityTabs />);
    fireEvent.click(screen.getByRole('tab', { name: /alerts/i }));
    expect(screen.getByTestId('alert-panel')).toBeInTheDocument();
  });

  it('should_show_alert_count_badge', () => {
    render(<ObservabilityTabs alertCount={3} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('should_have_tablist_role', () => {
    render(<ObservabilityTabs />);
    expect(screen.getByRole('tablist')).toBeInTheDocument();
  });
});
