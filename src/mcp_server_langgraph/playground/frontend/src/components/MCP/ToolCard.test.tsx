/**
 * ToolCard Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCard } from './ToolCard';
import type { MCPTool } from '../../api/mcp-types';

const mockTool: MCPTool = {
  name: 'test_tool',
  description: 'A test tool for unit testing',
  inputSchema: {
    type: 'object',
    properties: {
      message: { type: 'string', description: 'The message' },
      count: { type: 'number' },
    },
    required: ['message'],
  },
};

describe('ToolCard', () => {
  it('should_render_tool_name', () => {
    render(<ToolCard tool={mockTool} />);
    expect(screen.getByText('test_tool')).toBeInTheDocument();
  });

  it('should_render_tool_description', () => {
    render(<ToolCard tool={mockTool} />);
    expect(screen.getByText('A test tool for unit testing')).toBeInTheDocument();
  });

  it('should_show_parameter_count', () => {
    render(<ToolCard tool={mockTool} />);
    expect(screen.getByText(/2 params/)).toBeInTheDocument();
  });

  it('should_show_required_count', () => {
    render(<ToolCard tool={mockTool} />);
    expect(screen.getByText(/1 required/)).toBeInTheDocument();
  });

  it('should_call_onClick_when_clicked', () => {
    const onClick = vi.fn();
    render(<ToolCard tool={mockTool} onClick={onClick} />);

    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });

  it('should_apply_selected_styling_when_selected', () => {
    render(<ToolCard tool={mockTool} isSelected />);

    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-primary-50');
  });

  it('should_apply_default_styling_when_not_selected', () => {
    render(<ToolCard tool={mockTool} isSelected={false} />);

    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-white');
  });

  it('should_handle_tool_with_no_parameters', () => {
    const simpleTool: MCPTool = {
      name: 'simple_tool',
      description: 'No parameters',
      inputSchema: { type: 'object' },
    };

    render(<ToolCard tool={simpleTool} />);
    expect(screen.getByText('simple_tool')).toBeInTheDocument();
    expect(screen.queryByText(/params/)).not.toBeInTheDocument();
  });
});
