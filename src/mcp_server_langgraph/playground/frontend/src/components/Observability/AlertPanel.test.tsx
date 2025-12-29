/**
 * AlertPanel Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AlertPanel } from './AlertPanel';
import type { Alert } from '../../api/types';

describe('AlertPanel', () => {
  const mockAlerts: Alert[] = [
    { id: 'alert-1', severity: 'critical', title: 'Critical Alert', description: 'Critical issue', source: 'system', timestamp: '2025-01-01T10:00:00Z', acknowledged: false },
    { id: 'alert-2', severity: 'high', title: 'High Alert', description: 'High priority', source: 'system', timestamp: '2025-01-01T10:01:00Z', acknowledged: false },
    { id: 'alert-3', severity: 'medium', title: 'Medium Alert', description: 'Medium priority', source: 'system', timestamp: '2025-01-01T10:02:00Z', acknowledged: true },
  ];

  it('should_render_all_alerts', () => {
    render(<AlertPanel alerts={mockAlerts} />);
    expect(screen.getByText('Critical Alert')).toBeInTheDocument();
    expect(screen.getByText('High Alert')).toBeInTheDocument();
    expect(screen.getByText('Medium Alert')).toBeInTheDocument();
  });

  it('should_show_empty_state_when_no_alerts', () => {
    render(<AlertPanel alerts={[]} />);
    expect(screen.getByText(/no alerts/i)).toBeInTheDocument();
  });

  it('should_apply_severity_styling', () => {
    render(<AlertPanel alerts={mockAlerts} />);
    // Find the alert container (grandparent of the title)
    const titleElement = screen.getByText('Critical Alert');
    const alertCard = titleElement.closest('.p-3.rounded-lg');
    expect(alertCard).toHaveClass('alert-critical');
  });

  it('should_call_onAcknowledge_when_clicked', () => {
    const onAcknowledge = vi.fn();
    render(<AlertPanel alerts={mockAlerts} onAcknowledge={onAcknowledge} />);
    const ackButtons = screen.getAllByRole('button', { name: /acknowledge/i });
    fireEvent.click(ackButtons[0]);
    expect(onAcknowledge).toHaveBeenCalledWith('alert-1');
  });

  it('should_show_acknowledged_state', () => {
    render(<AlertPanel alerts={mockAlerts} />);
    expect(screen.getByText(/acknowledged/i)).toBeInTheDocument();
  });

  it('should_have_assertive_aria_live', () => {
    render(<AlertPanel alerts={mockAlerts} />);
    const region = screen.getByRole('region');
    expect(region).toHaveAttribute('aria-live', 'assertive');
  });
});
