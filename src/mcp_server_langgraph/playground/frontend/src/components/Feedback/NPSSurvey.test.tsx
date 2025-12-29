/**
 * NPSSurvey Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NPSSurvey } from './NPSSurvey';

describe('NPSSurvey', () => {
  it('should_render_nps_question', () => {
    render(<NPSSurvey onSubmit={() => {}} />);
    expect(screen.getByText(/how likely/i)).toBeInTheDocument();
  });

  it('should_render_score_buttons_0_to_10', () => {
    render(<NPSSurvey onSubmit={() => {}} />);
    for (let i = 0; i <= 10; i++) {
      expect(screen.getByRole('button', { name: String(i) })).toBeInTheDocument();
    }
  });

  it('should_highlight_selected_score', () => {
    render(<NPSSurvey onSubmit={() => {}} />);
    // Score 9 is a promoter, should get bg-primary-600
    const button9 = screen.getByRole('button', { name: '9' });
    fireEvent.click(button9);
    expect(button9).toHaveClass('bg-primary-600');
  });

  it('should_show_labels_for_scale_ends', () => {
    render(<NPSSurvey onSubmit={() => {}} />);
    expect(screen.getByText(/not likely/i)).toBeInTheDocument();
    expect(screen.getByText(/extremely likely/i)).toBeInTheDocument();
  });

  it('should_call_onSubmit_with_score', () => {
    const onSubmit = vi.fn();
    render(<NPSSurvey onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole('button', { name: '9' }));
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    expect(onSubmit).toHaveBeenCalledWith(9);
  });

  it('should_disable_submit_without_selection', () => {
    render(<NPSSurvey onSubmit={() => {}} />);
    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  it('should_enable_submit_after_selection', () => {
    render(<NPSSurvey onSubmit={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: '7' }));
    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('should_call_onDismiss_when_dismissed', () => {
    const onDismiss = vi.fn();
    render(<NPSSurvey onSubmit={() => {}} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: /dismiss|skip|close/i }));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('should_have_accessible_fieldset', () => {
    render(<NPSSurvey onSubmit={() => {}} />);
    expect(screen.getByRole('group')).toBeInTheDocument();
  });
});
