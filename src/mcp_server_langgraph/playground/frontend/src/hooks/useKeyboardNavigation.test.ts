/**
 * useKeyboardNavigation Hook Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useKeyboardNavigation, useKeyboardShortcut, KeyboardShortcuts } from './useKeyboardNavigation';

describe('useKeyboardNavigation', () => {
  const items = ['item1', 'item2', 'item3', 'item4'];

  it('should_initialize_with_first_item_focused', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items));
    expect(result.current.focusedIndex).toBe(0);
    expect(result.current.focusedItem).toBe('item1');
  });

  it('should_move_focus_down_with_arrow_down', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items));

    act(() => {
      result.current.handleKeyDown({ key: 'ArrowDown', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(result.current.focusedIndex).toBe(1);
    expect(result.current.focusedItem).toBe('item2');
  });

  it('should_move_focus_up_with_arrow_up', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items, { initialIndex: 2 }));

    act(() => {
      result.current.handleKeyDown({ key: 'ArrowUp', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(result.current.focusedIndex).toBe(1);
    expect(result.current.focusedItem).toBe('item2');
  });

  it('should_wrap_around_at_end', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items, { wrap: true, initialIndex: 3 }));

    act(() => {
      result.current.handleKeyDown({ key: 'ArrowDown', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(result.current.focusedIndex).toBe(0);
    expect(result.current.focusedItem).toBe('item1');
  });

  it('should_wrap_around_at_start', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items, { wrap: true, initialIndex: 0 }));

    act(() => {
      result.current.handleKeyDown({ key: 'ArrowUp', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(result.current.focusedIndex).toBe(3);
    expect(result.current.focusedItem).toBe('item4');
  });

  it('should_not_wrap_when_disabled', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items, { wrap: false, initialIndex: 3 }));

    act(() => {
      result.current.handleKeyDown({ key: 'ArrowDown', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(result.current.focusedIndex).toBe(3);
  });

  it('should_call_onSelect_when_enter_pressed', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useKeyboardNavigation(items, { onSelect }));

    act(() => {
      result.current.handleKeyDown({ key: 'Enter', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(onSelect).toHaveBeenCalledWith('item1', 0);
  });

  it('should_move_to_first_with_home', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items, { initialIndex: 2 }));

    act(() => {
      result.current.handleKeyDown({ key: 'Home', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(result.current.focusedIndex).toBe(0);
  });

  it('should_move_to_last_with_end', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items, { initialIndex: 0 }));

    act(() => {
      result.current.handleKeyDown({ key: 'End', preventDefault: vi.fn() } as unknown as React.KeyboardEvent);
    });

    expect(result.current.focusedIndex).toBe(3);
  });

  it('should_set_focus_index_directly', () => {
    const { result } = renderHook(() => useKeyboardNavigation(items));

    act(() => {
      result.current.setFocusedIndex(2);
    });

    expect(result.current.focusedIndex).toBe(2);
    expect(result.current.focusedItem).toBe('item3');
  });
});

describe('useKeyboardShortcut', () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>;
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    addEventListenerSpy = vi.spyOn(document, 'addEventListener');
    removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
  });

  afterEach(() => {
    addEventListenerSpy.mockRestore();
    removeEventListenerSpy.mockRestore();
  });

  it('should_register_keyboard_listener', () => {
    const callback = vi.fn();
    renderHook(() => useKeyboardShortcut('k', callback, { ctrlKey: true }));

    expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
  });

  it('should_cleanup_on_unmount', () => {
    const callback = vi.fn();
    const { unmount } = renderHook(() => useKeyboardShortcut('k', callback, { ctrlKey: true }));

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
  });

  it('should_call_callback_when_shortcut_pressed', () => {
    const callback = vi.fn();
    renderHook(() => useKeyboardShortcut('k', callback, { ctrlKey: true }));

    // Simulate the keydown event
    const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
    document.dispatchEvent(event);

    expect(callback).toHaveBeenCalled();
  });

  it('should_not_call_callback_without_modifier', () => {
    const callback = vi.fn();
    renderHook(() => useKeyboardShortcut('k', callback, { ctrlKey: true }));

    const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: false });
    document.dispatchEvent(event);

    expect(callback).not.toHaveBeenCalled();
  });
});

describe('KeyboardShortcuts', () => {
  it('should_return_common_shortcuts', () => {
    expect(KeyboardShortcuts.NEW_SESSION).toBeDefined();
    expect(KeyboardShortcuts.TOGGLE_SIDEBAR).toBeDefined();
    expect(KeyboardShortcuts.FOCUS_INPUT).toBeDefined();
    expect(KeyboardShortcuts.TOGGLE_THEME).toBeDefined();
  });
});
