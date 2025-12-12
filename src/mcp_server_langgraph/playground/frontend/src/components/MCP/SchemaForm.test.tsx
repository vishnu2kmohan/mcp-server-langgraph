/**
 * SchemaForm Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SchemaForm } from './SchemaForm';
import type { JSONSchema } from '../../api/mcp-types';

describe('SchemaForm', () => {
  it('should_render_text_input_for_string_type', () => {
    const schema: JSONSchema = {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Your name' },
      },
    };
    render(<SchemaForm schema={schema} onSubmit={() => {}} />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
  });

  it('should_render_number_input_for_number_type', () => {
    const schema: JSONSchema = {
      type: 'object',
      properties: {
        age: { type: 'number', description: 'Your age' },
      },
    };
    render(<SchemaForm schema={schema} onSubmit={() => {}} />);
    const input = screen.getByLabelText(/age/i);
    expect(input).toHaveAttribute('type', 'number');
  });

  it('should_render_checkbox_for_boolean_type', () => {
    const schema: JSONSchema = {
      type: 'object',
      properties: {
        approved: { type: 'boolean', description: 'Approve this?' },
      },
    };
    render(<SchemaForm schema={schema} onSubmit={() => {}} />);
    const input = screen.getByLabelText(/approve/i);
    expect(input).toHaveAttribute('type', 'checkbox');
  });

  it('should_render_select_for_enum_type', () => {
    const schema: JSONSchema = {
      type: 'object',
      properties: {
        color: { type: 'string', enum: ['red', 'green', 'blue'] },
      },
    };
    render(<SchemaForm schema={schema} onSubmit={() => {}} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByText('red')).toBeInTheDocument();
  });

  it('should_call_onSubmit_with_form_data', () => {
    const onSubmit = vi.fn();
    const schema: JSONSchema = {
      type: 'object',
      properties: {
        message: { type: 'string' },
      },
    };
    render(<SchemaForm schema={schema} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: 'Hello' },
    });
    fireEvent.submit(screen.getByRole('form'));
    expect(onSubmit).toHaveBeenCalledWith({ message: 'Hello' });
  });

  it('should_show_required_indicator_for_required_fields', () => {
    const schema: JSONSchema = {
      type: 'object',
      properties: {
        email: { type: 'string' },
      },
      required: ['email'],
    };
    render(<SchemaForm schema={schema} onSubmit={() => {}} />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('should_render_description_as_help_text', () => {
    const schema: JSONSchema = {
      type: 'object',
      properties: {
        username: { type: 'string', description: 'Enter your username' },
      },
    };
    render(<SchemaForm schema={schema} onSubmit={() => {}} />);
    expect(screen.getByText('Enter your username')).toBeInTheDocument();
  });
});
