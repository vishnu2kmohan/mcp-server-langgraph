/**
 * useKeyboardNavigation Hook
 *
 * Provides keyboard navigation support for lists and menus.
 * Part of P3.5 UX Excellence - Keyboard Navigation.
 */

import { useState, useCallback, useEffect } from 'react';

export interface UseKeyboardNavigationOptions<T> {
  initialIndex?: number;
  wrap?: boolean;
  onSelect?: (item: T, index: number) => void;
}

export interface UseKeyboardNavigationResult<T> {
  focusedIndex: number;
  focusedItem: T | undefined;
  setFocusedIndex: (index: number) => void;
  handleKeyDown: (event: React.KeyboardEvent) => void;
}

export function useKeyboardNavigation<T>(
  items: T[],
  options: UseKeyboardNavigationOptions<T> = {}
): UseKeyboardNavigationResult<T> {
  const { initialIndex = 0, wrap = false, onSelect } = options;
  const [focusedIndex, setFocusedIndex] = useState(initialIndex);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (items.length === 0) return;

      switch (event.key) {
        case 'ArrowDown':
        case 'j': // Vim-style navigation
          event.preventDefault();
          setFocusedIndex((current) => {
            if (current >= items.length - 1) {
              return wrap ? 0 : current;
            }
            return current + 1;
          });
          break;

        case 'ArrowUp':
        case 'k': // Vim-style navigation
          event.preventDefault();
          setFocusedIndex((current) => {
            if (current <= 0) {
              return wrap ? items.length - 1 : current;
            }
            return current - 1;
          });
          break;

        case 'Home':
          event.preventDefault();
          setFocusedIndex(0);
          break;

        case 'End':
          event.preventDefault();
          setFocusedIndex(items.length - 1);
          break;

        case 'Enter':
        case ' ': // Space
          event.preventDefault();
          if (onSelect && items[focusedIndex]) {
            onSelect(items[focusedIndex], focusedIndex);
          }
          break;

        default:
          break;
      }
    },
    [items, wrap, focusedIndex, onSelect]
  );

  // Reset focus when items change
  useEffect(() => {
    if (focusedIndex >= items.length && items.length > 0) {
      setFocusedIndex(items.length - 1);
    }
  }, [items.length, focusedIndex]);

  return {
    focusedIndex,
    focusedItem: items[focusedIndex],
    setFocusedIndex,
    handleKeyDown,
  };
}

export interface KeyboardShortcutModifiers {
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
}

export function useKeyboardShortcut(
  key: string,
  callback: (event: KeyboardEvent) => void,
  modifiers: KeyboardShortcutModifiers = {}
): void {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const matchesModifiers =
        (!modifiers.ctrlKey || event.ctrlKey) &&
        (!modifiers.metaKey || event.metaKey) &&
        (!modifiers.shiftKey || event.shiftKey) &&
        (!modifiers.altKey || event.altKey);

      // Check if we need at least one modifier
      const hasRequiredModifier =
        modifiers.ctrlKey || modifiers.metaKey || modifiers.shiftKey || modifiers.altKey;

      // If modifiers are required, check that they match
      const modifiersMatch = hasRequiredModifier
        ? matchesModifiers &&
          (modifiers.ctrlKey === event.ctrlKey || !modifiers.ctrlKey) &&
          (modifiers.metaKey === event.metaKey || !modifiers.metaKey) &&
          (modifiers.shiftKey === event.shiftKey || !modifiers.shiftKey) &&
          (modifiers.altKey === event.altKey || !modifiers.altKey)
        : true;

      if (event.key.toLowerCase() === key.toLowerCase() && modifiersMatch) {
        // Don't trigger shortcuts when typing in inputs
        const target = event.target as HTMLElement;
        const isInput =
          target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable;

        if (!isInput) {
          event.preventDefault();
          callback(event);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [key, callback, modifiers]);
}

/**
 * Common keyboard shortcuts used throughout the app
 */
export const KeyboardShortcuts = {
  NEW_SESSION: { key: 'n', modifiers: { ctrlKey: true } },
  TOGGLE_SIDEBAR: { key: 'b', modifiers: { ctrlKey: true } },
  FOCUS_INPUT: { key: '/', modifiers: {} },
  TOGGLE_THEME: { key: 't', modifiers: { ctrlKey: true, shiftKey: true } },
  CLOSE_MODAL: { key: 'Escape', modifiers: {} },
  SUBMIT: { key: 'Enter', modifiers: { ctrlKey: true } },
  SEARCH: { key: 'k', modifiers: { ctrlKey: true } },
};

/**
 * Hook to display available keyboard shortcuts
 */
export function useKeyboardShortcutsHelp(): { shortcuts: Array<{ key: string; description: string; display: string }> } {
  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const modKey = isMac ? '⌘' : 'Ctrl';

  return {
    shortcuts: [
      { key: 'NEW_SESSION', description: 'New Session', display: `${modKey}+N` },
      { key: 'TOGGLE_SIDEBAR', description: 'Toggle Sidebar', display: `${modKey}+B` },
      { key: 'FOCUS_INPUT', description: 'Focus Input', display: '/' },
      { key: 'TOGGLE_THEME', description: 'Toggle Theme', display: `${modKey}+Shift+T` },
      { key: 'CLOSE_MODAL', description: 'Close Modal', display: 'Esc' },
      { key: 'SUBMIT', description: 'Submit Message', display: `${modKey}+Enter` },
      { key: 'SEARCH', description: 'Search', display: `${modKey}+K` },
    ],
  };
}
