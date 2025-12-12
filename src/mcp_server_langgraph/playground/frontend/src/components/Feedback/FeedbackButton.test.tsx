/**
 * FeedbackButton Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FeedbackButton } from './FeedbackButton';

describe('FeedbackButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_render_feedback_button', () => {
    render(<FeedbackButton />);
    expect(screen.getByLabelText('Give feedback')).toBeInTheDocument();
  });

  it('should_open_feedback_panel_when_clicked', () => {
    render(<FeedbackButton />);

    fireEvent.click(screen.getByLabelText('Give feedback'));

    expect(screen.getByText("How's your experience?")).toBeInTheDocument();
  });

  it('should_close_feedback_panel_when_clicked_again', () => {
    render(<FeedbackButton />);

    // Open
    fireEvent.click(screen.getByLabelText('Give feedback'));
    expect(screen.getByText("How's your experience?")).toBeInTheDocument();

    // Close
    fireEvent.click(screen.getByLabelText('Close feedback'));
    expect(screen.queryByText("How's your experience?")).not.toBeInTheDocument();
  });

  it('should_render_all_rating_emojis', () => {
    render(<FeedbackButton />);
    fireEvent.click(screen.getByLabelText('Give feedback'));

    expect(screen.getByLabelText('Very Unhappy')).toBeInTheDocument();
    expect(screen.getByLabelText('Unhappy')).toBeInTheDocument();
    expect(screen.getByLabelText('Neutral')).toBeInTheDocument();
    expect(screen.getByLabelText('Happy')).toBeInTheDocument();
    expect(screen.getByLabelText('Very Happy')).toBeInTheDocument();
  });

  it('should_show_comment_input_after_rating_selected', () => {
    render(<FeedbackButton />);
    fireEvent.click(screen.getByLabelText('Give feedback'));

    // Initially no textarea
    expect(screen.queryByPlaceholderText(/additional feedback/i)).not.toBeInTheDocument();

    // Select a rating
    fireEvent.click(screen.getByLabelText('Happy'));

    // Now textarea should appear
    expect(screen.getByPlaceholderText(/additional feedback/i)).toBeInTheDocument();
  });

  it('should_show_submit_button_after_rating_selected', () => {
    render(<FeedbackButton />);
    fireEvent.click(screen.getByLabelText('Give feedback'));

    fireEvent.click(screen.getByLabelText('Happy'));

    expect(screen.getByRole('button', { name: 'Submit Feedback' })).toBeInTheDocument();
  });

  it('should_call_onSubmit_with_feedback_data', () => {
    const onSubmit = vi.fn();
    render(<FeedbackButton onSubmit={onSubmit} />);

    fireEvent.click(screen.getByLabelText('Give feedback'));
    fireEvent.click(screen.getByLabelText('Very Happy'));
    fireEvent.change(screen.getByPlaceholderText(/additional feedback/i), {
      target: { value: 'Great app!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Submit Feedback' }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        rating: 5,
        comment: 'Great app!',
        page: '/',
      })
    );
  });

  it('should_show_thank_you_after_submission', async () => {
    render(<FeedbackButton />);

    fireEvent.click(screen.getByLabelText('Give feedback'));
    fireEvent.click(screen.getByLabelText('Happy'));
    fireEvent.click(screen.getByRole('button', { name: 'Submit Feedback' }));

    expect(screen.getByText('Thanks for your feedback!')).toBeInTheDocument();
  });

  it('should_apply_position_class', () => {
    const { rerender } = render(<FeedbackButton position="bottom-left" />);

    // The container should have left-4 class
    const container = screen.getByLabelText('Give feedback').parentElement;
    expect(container).toHaveClass('left-4');

    rerender(<FeedbackButton position="bottom-right" />);
    expect(container).toHaveClass('right-4');
  });
});
