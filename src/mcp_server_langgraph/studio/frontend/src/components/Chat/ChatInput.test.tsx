/**
 * ChatInput Tests
 *
 * Tests for chat input component with message submission.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  const defaultProps = {
    onSend: vi.fn(),
    isDisabled: false,
    placeholder: 'Type a message...',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render input field', () => {
      render(<ChatInput {...defaultProps} />);

      expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
    });

    it('should render send button', () => {
      render(<ChatInput {...defaultProps} />);

      expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
    });
  });

  describe('Message Input', () => {
    it('should update input value when typing', () => {
      render(<ChatInput {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type a message...');
      fireEvent.change(input, { target: { value: 'Hello world' } });

      expect(input).toHaveValue('Hello world');
    });

    it('should call onSend with message when send button is clicked', () => {
      render(<ChatInput {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type a message...');
      fireEvent.change(input, { target: { value: 'Hello world' } });
      fireEvent.click(screen.getByRole('button', { name: /send/i }));

      expect(defaultProps.onSend).toHaveBeenCalledWith('Hello world');
    });

    it('should call onSend when Enter is pressed', () => {
      render(<ChatInput {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type a message...');
      fireEvent.change(input, { target: { value: 'Hello world' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(defaultProps.onSend).toHaveBeenCalledWith('Hello world');
    });

    it('should not call onSend when Shift+Enter is pressed', () => {
      render(<ChatInput {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type a message...');
      fireEvent.change(input, { target: { value: 'Hello world' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

      expect(defaultProps.onSend).not.toHaveBeenCalled();
    });

    it('should clear input after sending', () => {
      render(<ChatInput {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type a message...');
      fireEvent.change(input, { target: { value: 'Hello world' } });
      fireEvent.click(screen.getByRole('button', { name: /send/i }));

      expect(input).toHaveValue('');
    });

    it('should not send empty message', () => {
      render(<ChatInput {...defaultProps} />);

      fireEvent.click(screen.getByRole('button', { name: /send/i }));

      expect(defaultProps.onSend).not.toHaveBeenCalled();
    });

    it('should not send whitespace-only message', () => {
      render(<ChatInput {...defaultProps} />);

      const input = screen.getByPlaceholderText('Type a message...');
      fireEvent.change(input, { target: { value: '   ' } });
      fireEvent.click(screen.getByRole('button', { name: /send/i }));

      expect(defaultProps.onSend).not.toHaveBeenCalled();
    });
  });

  describe('Disabled State', () => {
    it('should disable input when isDisabled is true', () => {
      render(<ChatInput {...defaultProps} isDisabled={true} />);

      const input = screen.getByPlaceholderText('Type a message...');
      expect(input).toBeDisabled();
    });

    it('should disable button when isDisabled is true', () => {
      render(<ChatInput {...defaultProps} isDisabled={true} />);

      const button = screen.getByRole('button', { name: /send/i });
      expect(button).toBeDisabled();
    });
  });

  describe('Custom Placeholder', () => {
    it('should use custom placeholder', () => {
      render(<ChatInput {...defaultProps} placeholder="Ask me anything..." />);

      expect(screen.getByPlaceholderText('Ask me anything...')).toBeInTheDocument();
    });
  });
});
