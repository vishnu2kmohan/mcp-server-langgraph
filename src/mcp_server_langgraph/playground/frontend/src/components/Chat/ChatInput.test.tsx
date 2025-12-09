/**
 * ChatInput Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  it('should_render_textarea', () => {
    render(<ChatInput onSend={() => {}} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('should_call_onSend_when_enter_pressed', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();

    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByRole('textbox');

    await user.type(textarea, 'Hello');
    await user.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledWith('Hello');
  });

  it('should_not_send_when_shift_enter_pressed', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();

    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByRole('textbox');

    await user.type(textarea, 'Line 1');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    await user.type(textarea, 'Line 2');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('should_not_send_empty_message', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();

    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByRole('textbox');

    await user.click(textarea);
    await user.keyboard('{Enter}');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('should_clear_input_after_send', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();

    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;

    await user.type(textarea, 'Hello');
    await user.keyboard('{Enter}');

    expect(textarea.value).toBe('');
  });

  it('should_disable_when_disabled_prop_is_true', () => {
    render(<ChatInput onSend={() => {}} disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('should_show_send_button', () => {
    render(<ChatInput onSend={() => {}} />);
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('should_send_on_button_click', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();

    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByRole('textbox');
    const button = screen.getByRole('button', { name: /send/i });

    await user.type(textarea, 'Hello');
    await user.click(button);

    expect(onSend).toHaveBeenCalledWith('Hello');
  });

  it('should_have_placeholder_text', () => {
    render(<ChatInput onSend={() => {}} placeholder="Type a message..." />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
  });
});
