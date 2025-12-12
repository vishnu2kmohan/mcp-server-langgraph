/**
 * AgentInfoBadge Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentInfoBadge } from './AgentInfoBadge';
import type { AgentMetadata } from '../../api/types';

describe('AgentInfoBadge', () => {
  const basicMetadata: AgentMetadata = {
    confidence: 0.85,
    responseFormat: 'detailed',
  };

  const fullMetadata: AgentMetadata = {
    confidence: 0.85,
    responseFormat: 'detailed',
    reasoning: 'This appears to be a technical question about React hooks.',
    verificationScore: 0.92,
    refinementAttempts: 1,
    contextTokensBefore: 5000,
    contextTokensAfter: 2500,
  };

  it('should_render_confidence_percentage', () => {
    render(<AgentInfoBadge metadata={basicMetadata} />);
    expect(screen.getByText(/85%/)).toBeInTheDocument();
  });

  it('should_show_high_confidence_label', () => {
    render(<AgentInfoBadge metadata={{ confidence: 0.9 }} />);
    expect(screen.getByText(/High/)).toBeInTheDocument();
  });

  it('should_show_medium_confidence_label', () => {
    render(<AgentInfoBadge metadata={{ confidence: 0.6 }} />);
    expect(screen.getByText(/Medium/)).toBeInTheDocument();
  });

  it('should_show_low_confidence_label', () => {
    render(<AgentInfoBadge metadata={{ confidence: 0.3 }} />);
    expect(screen.getByText(/Low/)).toBeInTheDocument();
  });

  it('should_render_response_format', () => {
    render(<AgentInfoBadge metadata={basicMetadata} />);
    expect(screen.getByText(/detailed/)).toBeInTheDocument();
  });

  it('should_expand_details_when_clicked', () => {
    render(<AgentInfoBadge metadata={fullMetadata} />);

    // Initially reasoning is not visible
    expect(screen.queryByText(/Agent Reasoning/)).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByLabelText('Toggle agent details'));

    // Now reasoning should be visible
    expect(screen.getByText('Agent Reasoning')).toBeInTheDocument();
    expect(screen.getByText(/This appears to be a technical question/)).toBeInTheDocument();
  });

  it('should_show_verification_score', () => {
    render(<AgentInfoBadge metadata={fullMetadata} />);
    fireEvent.click(screen.getByLabelText('Toggle agent details'));

    expect(screen.getByText('Verification')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
  });

  it('should_show_refinement_attempts', () => {
    render(<AgentInfoBadge metadata={fullMetadata} />);
    fireEvent.click(screen.getByLabelText('Toggle agent details'));

    expect(screen.getByText('Refinements')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('should_show_context_compaction', () => {
    render(<AgentInfoBadge metadata={fullMetadata} />);
    fireEvent.click(screen.getByLabelText('Toggle agent details'));

    expect(screen.getByText('Context Compaction')).toBeInTheDocument();
    expect(screen.getByText(/5,000 → 2,500 tokens/)).toBeInTheDocument();
    expect(screen.getByText(/-50%/)).toBeInTheDocument();
  });

  it('should_collapse_details_when_clicked_again', () => {
    render(<AgentInfoBadge metadata={fullMetadata} />);

    // Expand
    fireEvent.click(screen.getByLabelText('Toggle agent details'));
    expect(screen.getByText('Agent Reasoning')).toBeInTheDocument();

    // Collapse
    fireEvent.click(screen.getByLabelText('Toggle agent details'));
    expect(screen.queryByText('Agent Reasoning')).not.toBeInTheDocument();
  });

  it('should_not_show_expand_indicator_without_details', () => {
    render(<AgentInfoBadge metadata={{ confidence: 0.9 }} />);

    // Should not have expand/collapse behavior without details
    const button = screen.getByLabelText('Toggle agent details');
    expect(button.querySelector('svg')).toBeNull(); // No chevron icon
  });
});
