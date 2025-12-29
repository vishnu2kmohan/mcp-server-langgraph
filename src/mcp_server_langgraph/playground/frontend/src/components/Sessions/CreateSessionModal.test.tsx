/**
 * CreateSessionModal Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateSessionModal } from './CreateSessionModal';

describe('CreateSessionModal', () => {
  it('should_not_render_when_not_open', () => {
    render(<CreateSessionModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should_render_when_open', () => {
    render(<CreateSessionModal isOpen={true} onClose={() => {}} onCreate={() => {}} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should_have_name_input', () => {
    render(<CreateSessionModal isOpen={true} onClose={() => {}} onCreate={() => {}} />);
    expect(screen.getByLabelText(/session name/i)).toBeInTheDocument();
  });

  it('should_call_onCreate_with_name_when_submitted', async () => {
    const onCreate = vi.fn();
    const user = userEvent.setup();

    render(<CreateSessionModal isOpen={true} onClose={() => {}} onCreate={onCreate} />);

    const input = screen.getByLabelText(/session name/i);
    await user.type(input, 'My New Session');

    const submitButton = screen.getByRole('button', { name: /create/i });
    await user.click(submitButton);

    expect(onCreate).toHaveBeenCalledWith('My New Session', undefined);
  });

  it('should_call_onClose_when_cancel_clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<CreateSessionModal isOpen={true} onClose={onClose} onCreate={() => {}} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('should_disable_create_button_when_name_empty', () => {
    render(<CreateSessionModal isOpen={true} onClose={() => {}} onCreate={() => {}} />);
    const submitButton = screen.getByRole('button', { name: /create/i });
    expect(submitButton).toBeDisabled();
  });

  it('should_clear_form_when_closed_and_reopened', async () => {
    const { rerender } = render(
      <CreateSessionModal isOpen={true} onClose={() => {}} onCreate={() => {}} />
    );

    const input = screen.getByLabelText(/session name/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Test' } });
    expect(input.value).toBe('Test');

    rerender(<CreateSessionModal isOpen={false} onClose={() => {}} onCreate={() => {}} />);
    rerender(<CreateSessionModal isOpen={true} onClose={() => {}} onCreate={() => {}} />);

    const newInput = screen.getByLabelText(/session name/i) as HTMLInputElement;
    expect(newInput.value).toBe('');
  });

  it('should_be_accessible_with_dialog_role', () => {
    render(<CreateSessionModal isOpen={true} onClose={() => {}} onCreate={() => {}} />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });
});
