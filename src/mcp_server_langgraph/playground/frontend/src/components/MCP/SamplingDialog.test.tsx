/**
 * SamplingDialog Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SamplingDialog } from './SamplingDialog';
import type { SamplingRequest } from '../../api/mcp-types';

describe('SamplingDialog', () => {
  const mockSamplingRequest: SamplingRequest = {
    id: 'sample-1',
    serverId: 'server-1',
    messages: [
      { role: 'user', content: { type: 'text', text: 'Summarize this code' } },
    ],
    modelPreferences: {
      hints: [{ name: 'claude-3-sonnet' }],
      intelligencePriority: 0.8,
    },
    systemPrompt: 'You are a code analyst.',
    maxTokens: 500,
  };

  it('should_render_dialog_when_request_provided', () => {
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={() => {}}
        onReject={() => {}}
      />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/sampling request/i)).toBeInTheDocument();
  });

  it('should_not_render_when_no_request', () => {
    render(
      <SamplingDialog
        request={null}
        onApprove={() => {}}
        onReject={() => {}}
      />
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should_display_system_prompt', () => {
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={() => {}}
        onReject={() => {}}
      />
    );
    expect(screen.getByText(/you are a code analyst/i)).toBeInTheDocument();
  });

  it('should_display_messages', () => {
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={() => {}}
        onReject={() => {}}
      />
    );
    expect(screen.getByText(/summarize this code/i)).toBeInTheDocument();
  });

  it('should_display_model_preferences', () => {
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={() => {}}
        onReject={() => {}}
      />
    );
    expect(screen.getByText(/claude-3-sonnet/i)).toBeInTheDocument();
  });

  it('should_display_max_tokens', () => {
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={() => {}}
        onReject={() => {}}
      />
    );
    expect(screen.getByText(/500/)).toBeInTheDocument();
  });

  it('should_call_onApprove_when_approved', () => {
    const onApprove = vi.fn();
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={onApprove}
        onReject={() => {}}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /approve/i }));
    expect(onApprove).toHaveBeenCalled();
  });

  it('should_call_onReject_when_rejected', () => {
    const onReject = vi.fn();
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={() => {}}
        onReject={onReject}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /reject/i }));
    expect(onReject).toHaveBeenCalled();
  });

  it('should_show_server_id', () => {
    render(
      <SamplingDialog
        request={mockSamplingRequest}
        onApprove={() => {}}
        onReject={() => {}}
      />
    );
    expect(screen.getByText(/server-1/)).toBeInTheDocument();
  });
});
