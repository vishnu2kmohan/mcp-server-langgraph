/**
 * ResponseFormatSelector Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { renderHook, act } from '@testing-library/react';
import { ResponseFormatSelector, useResponseFormat } from './ResponseFormatSelector';

describe('ResponseFormatSelector', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should_render_both_format_options', () => {
    render(<ResponseFormatSelector />);
    expect(screen.getByText('Concise')).toBeInTheDocument();
    expect(screen.getByText('Detailed')).toBeInTheDocument();
  });

  it('should_default_to_detailed_format', () => {
    render(<ResponseFormatSelector />);
    const detailedButton = screen.getByText('Detailed');
    expect(detailedButton).toHaveAttribute('aria-pressed', 'true');
  });

  it('should_switch_to_concise_when_clicked', () => {
    const onChange = vi.fn();
    render(<ResponseFormatSelector onChange={onChange} />);

    fireEvent.click(screen.getByText('Concise'));

    expect(onChange).toHaveBeenCalledWith('concise');
    expect(screen.getByText('Concise')).toHaveAttribute('aria-pressed', 'true');
  });

  it('should_switch_to_detailed_when_clicked', () => {
    const onChange = vi.fn();
    render(<ResponseFormatSelector value="concise" onChange={onChange} />);

    fireEvent.click(screen.getByText('Detailed'));

    expect(onChange).toHaveBeenCalledWith('detailed');
  });

  it('should_persist_to_localStorage', () => {
    render(<ResponseFormatSelector />);

    fireEvent.click(screen.getByText('Concise'));

    // Verify the value was saved by reading it back
    expect(localStorage.getItem('playground_response_format')).toBe('concise');
  });

  it('should_load_from_localStorage_on_mount', () => {
    localStorage.setItem('playground_response_format', 'concise');

    render(<ResponseFormatSelector />);

    expect(screen.getByText('Concise')).toHaveAttribute('aria-pressed', 'true');
  });

  it('should_use_controlled_value', () => {
    render(<ResponseFormatSelector value="concise" />);

    expect(screen.getByText('Concise')).toHaveAttribute('aria-pressed', 'true');
  });

  it('should_show_response_label', () => {
    render(<ResponseFormatSelector />);
    expect(screen.getByText('Response:')).toBeInTheDocument();
  });
});

describe('useResponseFormat', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should_default_to_detailed', () => {
    const { result } = renderHook(() => useResponseFormat());
    expect(result.current.format).toBe('detailed');
  });

  it('should_load_from_localStorage', () => {
    localStorage.setItem('playground_response_format', 'concise');

    const { result } = renderHook(() => useResponseFormat());
    expect(result.current.format).toBe('concise');
  });

  it('should_update_format', () => {
    const { result } = renderHook(() => useResponseFormat());

    act(() => {
      result.current.setFormat('concise');
    });

    expect(result.current.format).toBe('concise');
    expect(localStorage.getItem('playground_response_format')).toBe('concise');
  });
});
