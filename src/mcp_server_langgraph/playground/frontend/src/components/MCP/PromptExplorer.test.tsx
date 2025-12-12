/**
 * PromptExplorer Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PromptExplorer } from './PromptExplorer';

// Mock useMCPPrompts hook
vi.mock('../../hooks/useMCPPrompts', () => ({
  useMCPPrompts: () => ({
    prompts: [
      {
        name: 'greeting',
        description: 'Generate a greeting message',
        arguments: [
          { name: 'name', description: 'Name to greet', required: true },
        ],
      },
      {
        name: 'summarize',
        description: 'Summarize text content',
        arguments: [
          { name: 'text', description: 'Text to summarize', required: true },
          { name: 'length', description: 'Summary length', required: false },
        ],
      },
    ],
    getPrompt: vi.fn().mockResolvedValue({
      messages: [
        { role: 'user', content: { type: 'text', text: 'Hello!' } },
        { role: 'assistant', content: { type: 'text', text: 'Hi there!' } },
      ],
    }),
    isLoading: false,
  }),
}));

describe('PromptExplorer', () => {
  it('should_render_prompt_count', () => {
    render(<PromptExplorer />);
    expect(screen.getByText(/Prompts \(2\)/)).toBeInTheDocument();
  });

  it('should_render_all_prompts', () => {
    render(<PromptExplorer />);
    expect(screen.getByText('greeting')).toBeInTheDocument();
    expect(screen.getByText('summarize')).toBeInTheDocument();
  });

  it('should_render_search_input', () => {
    render(<PromptExplorer />);
    expect(screen.getByPlaceholderText('Search prompts...')).toBeInTheDocument();
  });

  it('should_filter_prompts_by_search_query', () => {
    render(<PromptExplorer />);

    const searchInput = screen.getByPlaceholderText('Search prompts...');
    fireEvent.change(searchInput, { target: { value: 'greet' } });

    expect(screen.getByText('greeting')).toBeInTheDocument();
    expect(screen.queryByText('summarize')).not.toBeInTheDocument();
  });

  it('should_show_no_match_message_when_search_has_no_results', () => {
    render(<PromptExplorer />);

    const searchInput = screen.getByPlaceholderText('Search prompts...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    expect(screen.getByText('No prompts match your search.')).toBeInTheDocument();
  });

  it('should_call_onPromptSelect_when_prompt_clicked', () => {
    const onPromptSelect = vi.fn();
    render(<PromptExplorer onPromptSelect={onPromptSelect} />);

    fireEvent.click(screen.getByText('greeting'));
    expect(onPromptSelect).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'greeting' })
    );
  });

  it('should_show_argument_count', () => {
    render(<PromptExplorer />);
    expect(screen.getByText('1 argument')).toBeInTheDocument();
    expect(screen.getByText('2 arguments')).toBeInTheDocument();
  });

  it('should_show_argument_form_when_prompt_selected', () => {
    render(<PromptExplorer />);

    fireEvent.click(screen.getByText('greeting'));

    // Check for the argument input by its placeholder
    expect(screen.getByPlaceholderText('Name to greet')).toBeInTheDocument();
  });

  it('should_show_required_indicator_for_required_arguments', () => {
    render(<PromptExplorer />);

    fireEvent.click(screen.getByText('greeting'));

    // Required arguments have an asterisk
    const requiredIndicator = screen.getByText('*');
    expect(requiredIndicator).toBeInTheDocument();
  });

  it('should_execute_prompt_and_show_result', async () => {
    render(<PromptExplorer />);

    // Click prompt to select it
    fireEvent.click(screen.getByText('greeting'));

    // Fill in argument
    const nameInput = screen.getByPlaceholderText('Name to greet');
    fireEvent.change(nameInput, { target: { value: 'World' } });

    // Submit form
    const submitButton = screen.getByRole('button', { name: /Get Prompt/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/User: Hello!/)).toBeInTheDocument();
      expect(screen.getByText(/Assistant: Hi there!/)).toBeInTheDocument();
    });
  });

  it('should_show_close_button_when_prompt_selected', () => {
    render(<PromptExplorer />);

    fireEvent.click(screen.getByText('greeting'));

    expect(screen.getByLabelText('Close prompt details')).toBeInTheDocument();
  });

  it('should_close_prompt_details_when_close_clicked', () => {
    render(<PromptExplorer />);

    // Select prompt
    fireEvent.click(screen.getByText('greeting'));
    expect(screen.getByLabelText('Close prompt details')).toBeInTheDocument();

    // Close it
    fireEvent.click(screen.getByLabelText('Close prompt details'));

    // Form should be gone
    expect(screen.queryByPlaceholderText('Name to greet')).not.toBeInTheDocument();
  });
});
