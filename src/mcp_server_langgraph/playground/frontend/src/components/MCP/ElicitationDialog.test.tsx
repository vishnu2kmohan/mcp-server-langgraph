/**
 * ElicitationDialog Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ElicitationDialog } from './ElicitationDialog';
import type { Elicitation } from '../../api/mcp-types';

describe('ElicitationDialog', () => {
  const mockElicitation: Elicitation = {
    id: 'elicit-1',
    serverId: 'server-1',
    message: 'Please confirm this action',
    requestedSchema: {
      type: 'object',
      properties: {
        approved: { type: 'boolean', description: 'Approve?' },
        reason: { type: 'string', description: 'Reason' },
      },
      required: ['approved'],
    },
  };

  it('should_render_dialog_when_elicitation_provided', () => {
    render(
      <ElicitationDialog
        elicitation={mockElicitation}
        onAccept={() => {}}
        onDecline={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Please confirm this action')).toBeInTheDocument();
  });

  it('should_not_render_when_no_elicitation', () => {
    render(
      <ElicitationDialog
        elicitation={null}
        onAccept={() => {}}
        onDecline={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should_render_schema_form_fields', () => {
    render(
      <ElicitationDialog
        elicitation={mockElicitation}
        onAccept={() => {}}
        onDecline={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByLabelText(/approved/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/reason/i)).toBeInTheDocument();
  });

  it('should_call_onAccept_with_form_data', () => {
    const onAccept = vi.fn();
    render(
      <ElicitationDialog
        elicitation={mockElicitation}
        onAccept={onAccept}
        onDecline={() => {}}
        onCancel={() => {}}
      />
    );
    fireEvent.change(screen.getByLabelText(/reason/i), {
      target: { value: 'Looks good' },
    });
    fireEvent.click(screen.getByRole('button', { name: /accept/i }));
    expect(onAccept).toHaveBeenCalledWith({ approved: false, reason: 'Looks good' });
  });

  it('should_call_onDecline_when_declined', () => {
    const onDecline = vi.fn();
    render(
      <ElicitationDialog
        elicitation={mockElicitation}
        onAccept={() => {}}
        onDecline={onDecline}
        onCancel={() => {}}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /decline/i }));
    expect(onDecline).toHaveBeenCalled();
  });

  it('should_call_onCancel_when_cancelled', () => {
    const onCancel = vi.fn();
    render(
      <ElicitationDialog
        elicitation={mockElicitation}
        onAccept={() => {}}
        onDecline={() => {}}
        onCancel={onCancel}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('should_show_server_id', () => {
    render(
      <ElicitationDialog
        elicitation={mockElicitation}
        onAccept={() => {}}
        onDecline={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByText(/server-1/)).toBeInTheDocument();
  });

  it('should_have_accessible_dialog', () => {
    render(
      <ElicitationDialog
        elicitation={mockElicitation}
        onAccept={() => {}}
        onDecline={() => {}}
        onCancel={() => {}}
      />
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby');
  });
});
