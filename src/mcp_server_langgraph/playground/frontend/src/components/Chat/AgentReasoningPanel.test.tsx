/**
 * AgentReasoningPanel Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentReasoningPanel } from './AgentReasoningPanel';
import type { AgentReasoningData } from './AgentReasoningPanel';

describe('AgentReasoningPanel', () => {
  const basicData: AgentReasoningData = {
    reasoning: 'The user is asking about React hooks. I should provide a detailed explanation.',
    toolCalls: [
      { name: 'search', arguments: { query: 'React hooks' }, result: 'Found 5 results' },
    ],
  };

  const fullData: AgentReasoningData = {
    reasoning: 'This is a complex technical question.',
    routingDecision: 'technical_agent',
    confidence: 0.92,
    toolCalls: [
      { name: 'search', arguments: { query: 'hooks' }, result: 'Results found' },
      { name: 'analyze', arguments: { code: 'sample' }, result: 'Analysis complete' },
    ],
    contextCompaction: {
      before: 8000,
      after: 4000,
      method: 'summarization',
    },
    refinementHistory: [
      { iteration: 1, change: 'Added more detail', score: 0.85 },
      { iteration: 2, change: 'Improved clarity', score: 0.92 },
    ],
  };

  it('should_render_collapsed_by_default', () => {
    render(<AgentReasoningPanel data={basicData} />);
    expect(screen.getByText('Agent Reasoning')).toBeInTheDocument();
    expect(screen.queryByText(basicData.reasoning)).not.toBeInTheDocument();
  });

  it('should_expand_when_header_clicked', () => {
    render(<AgentReasoningPanel data={basicData} />);

    fireEvent.click(screen.getByText('Agent Reasoning'));

    expect(screen.getByText(basicData.reasoning)).toBeInTheDocument();
  });

  it('should_start_expanded_when_defaultExpanded', () => {
    render(<AgentReasoningPanel data={basicData} defaultExpanded />);
    expect(screen.getByText(basicData.reasoning)).toBeInTheDocument();
  });

  it('should_show_tool_calls', () => {
    render(<AgentReasoningPanel data={basicData} defaultExpanded />);

    expect(screen.getByText('Tool Calls')).toBeInTheDocument();
    expect(screen.getByText('search')).toBeInTheDocument();
  });

  it('should_show_routing_decision', () => {
    render(<AgentReasoningPanel data={fullData} defaultExpanded />);

    expect(screen.getByText('Routing')).toBeInTheDocument();
    expect(screen.getByText('technical_agent')).toBeInTheDocument();
  });

  it('should_show_confidence', () => {
    render(<AgentReasoningPanel data={fullData} defaultExpanded />);

    expect(screen.getByText('Confidence')).toBeInTheDocument();
    // The 92% is part of refinement history with same score, use regex
    expect(screen.getAllByText(/92%/).length).toBeGreaterThan(0);
  });

  it('should_show_context_compaction', () => {
    render(<AgentReasoningPanel data={fullData} defaultExpanded />);

    expect(screen.getByText('Context Compaction')).toBeInTheDocument();
    expect(screen.getByText(/8,000 → 4,000/)).toBeInTheDocument();
  });

  it('should_show_refinement_history', () => {
    render(<AgentReasoningPanel data={fullData} defaultExpanded />);

    expect(screen.getByText('Refinement History')).toBeInTheDocument();
    expect(screen.getByText(/Iteration 1/)).toBeInTheDocument();
    expect(screen.getByText(/Iteration 2/)).toBeInTheDocument();
  });

  it('should_collapse_when_clicked_again', () => {
    render(<AgentReasoningPanel data={basicData} defaultExpanded />);

    expect(screen.getByText(basicData.reasoning)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Agent Reasoning'));

    expect(screen.queryByText(basicData.reasoning)).not.toBeInTheDocument();
  });

  it('should_show_tool_call_count_badge', () => {
    render(<AgentReasoningPanel data={fullData} />);
    expect(screen.getByText('2 tools')).toBeInTheDocument();
  });

  it('should_be_accessible', () => {
    render(<AgentReasoningPanel data={basicData} />);

    const button = screen.getByRole('button', { name: /Agent Reasoning/ });
    expect(button).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
  });
});
