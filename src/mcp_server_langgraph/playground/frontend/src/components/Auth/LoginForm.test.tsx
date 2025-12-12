/**
 * LoginForm Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LoginForm } from './LoginForm';

describe('LoginForm', () => {
  const mockOnClose = vi.fn();
  const mockOnLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_not_render_when_closed', () => {
    render(
      <LoginForm
        isOpen={false}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should_render_when_open', () => {
    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('should_have_username_and_password_inputs', () => {
    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
      />
    );

    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('should_disable_submit_when_fields_are_empty', () => {
    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
      />
    );

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    expect(submitButton).toBeDisabled();
  });

  it('should_enable_submit_when_fields_are_filled', () => {
    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
      />
    );

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });

    const submitButton = screen.getByRole('button', { name: /sign in/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('should_call_onLogin_when_submitted', async () => {
    mockOnLogin.mockResolvedValueOnce(undefined);

    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
      />
    );

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'testuser' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockOnLogin).toHaveBeenCalledWith('testuser', 'password');
    });
  });

  it('should_call_onClose_when_cancel_clicked', () => {
    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should_display_error_when_provided', () => {
    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
        error="Invalid credentials"
      />
    );

    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
  });

  it('should_show_loading_state', () => {
    render(
      <LoginForm
        isOpen={true}
        onClose={mockOnClose}
        onLogin={mockOnLogin}
        isLoading={true}
      />
    );

    expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeDisabled();
    expect(screen.getByLabelText(/password/i)).toBeDisabled();
  });
});
