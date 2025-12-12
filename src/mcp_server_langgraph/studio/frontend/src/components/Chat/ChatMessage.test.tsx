/**
 * ChatMessage Tests
 *
 * Tests for individual chat message display component.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from './ChatMessage';

describe('ChatMessage', () => {
  describe('User Messages', () => {
    it('should render user message with correct styling', () => {
      render(
        <ChatMessage
          role="user"
          content="Hello, how are you?"
          timestamp={new Date('2024-01-15T10:30:00Z')}
        />
      );

      expect(screen.getByText('Hello, how are you?')).toBeInTheDocument();
    });

    it('should display user label', () => {
      render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
        />
      );

      expect(screen.getByText('You')).toBeInTheDocument();
    });

    it('should apply user message styling', () => {
      const { container } = render(
        <ChatMessage
          role="user"
          content="Test message"
          timestamp={new Date()}
        />
      );

      const messageDiv = container.querySelector('[data-role="user"]');
      expect(messageDiv).toHaveClass('bg-blue-100');
    });
  });

  describe('Assistant Messages', () => {
    it('should render assistant message', () => {
      render(
        <ChatMessage
          role="assistant"
          content="I am doing well, thank you!"
          timestamp={new Date()}
        />
      );

      expect(screen.getByText('I am doing well, thank you!')).toBeInTheDocument();
    });

    it('should display assistant label', () => {
      render(
        <ChatMessage
          role="assistant"
          content="Test response"
          timestamp={new Date()}
        />
      );

      expect(screen.getByText('Assistant')).toBeInTheDocument();
    });

    it('should apply assistant message styling', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content="Test message"
          timestamp={new Date()}
        />
      );

      const messageDiv = container.querySelector('[data-role="assistant"]');
      expect(messageDiv).toHaveClass('bg-gray-100');
    });
  });

  describe('Timestamp', () => {
    it('should display formatted timestamp', () => {
      render(
        <ChatMessage
          role="user"
          content="Test"
          timestamp={new Date('2024-01-15T10:30:00Z')}
          showTimestamp={true}
        />
      );

      // Should display time in some format
      expect(screen.getByText(/\d{1,2}:\d{2}/)).toBeInTheDocument();
    });

    it('should hide timestamp when showTimestamp is false', () => {
      render(
        <ChatMessage
          role="user"
          content="Test"
          timestamp={new Date('2024-01-15T10:30:00Z')}
          showTimestamp={false}
        />
      );

      // Timestamp text should not be present
      const timestampElement = screen.queryByTestId('timestamp');
      expect(timestampElement).not.toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show loading indicator when isLoading is true', () => {
      render(
        <ChatMessage
          role="assistant"
          content=""
          timestamp={new Date()}
          isLoading={true}
        />
      );

      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    });
  });

  describe('Markdown Content', () => {
    it('should render markdown content when enabled', () => {
      render(
        <ChatMessage
          role="assistant"
          content="**Bold text**"
          timestamp={new Date()}
          renderMarkdown={true}
        />
      );

      // Should render as bold (strong element)
      expect(screen.getByText('Bold text')).toBeInTheDocument();
    });
  });
});
