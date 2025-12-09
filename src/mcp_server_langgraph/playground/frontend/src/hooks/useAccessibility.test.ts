/**
 * useAccessibility Hook Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAccessibility, useFocusTrap, useAnnounce } from './useAccessibility';

describe('useAccessibility', () => {
  describe('useFocusTrap', () => {
    let container: HTMLDivElement;
    let button1: HTMLButtonElement;
    let button2: HTMLButtonElement;
    let button3: HTMLButtonElement;

    beforeEach(() => {
      container = document.createElement('div');
      button1 = document.createElement('button');
      button2 = document.createElement('button');
      button3 = document.createElement('button');
      button1.textContent = 'Button 1';
      button2.textContent = 'Button 2';
      button3.textContent = 'Button 3';
      container.appendChild(button1);
      container.appendChild(button2);
      container.appendChild(button3);
      document.body.appendChild(container);
    });

    afterEach(() => {
      document.body.removeChild(container);
    });

    it('should_trap_focus_within_container', () => {
      const ref = { current: container };
      renderHook(() => useFocusTrap(ref, true));

      // Focus first element
      button1.focus();
      expect(document.activeElement).toBe(button1);
    });

    it('should_not_trap_focus_when_disabled', () => {
      const ref = { current: container };
      renderHook(() => useFocusTrap(ref, false));

      // Focus should not be managed
      button1.focus();
      expect(document.activeElement).toBe(button1);
    });

    it('should_handle_null_ref', () => {
      const ref = { current: null };
      // Should not throw
      expect(() => renderHook(() => useFocusTrap(ref, true))).not.toThrow();
    });
  });

  describe('useAnnounce', () => {
    beforeEach(() => {
      // Clean up any existing live regions
      document.querySelectorAll('[aria-live]').forEach((el) => el.remove());
    });

    it('should_create_live_region', () => {
      renderHook(() => useAnnounce());
      const liveRegion = document.querySelector('[aria-live="polite"]');
      expect(liveRegion).toBeTruthy();
    });

    it('should_announce_message', async () => {
      const { result } = renderHook(() => useAnnounce());

      act(() => {
        result.current.announce('Test message');
      });

      const liveRegion = document.querySelector('[aria-live="polite"]');
      expect(liveRegion?.textContent).toBe('Test message');
    });

    it('should_support_assertive_mode', async () => {
      const { result } = renderHook(() => useAnnounce('assertive'));

      const liveRegion = document.querySelector('[aria-live="assertive"]');
      expect(liveRegion).toBeTruthy();
    });

    it('should_clear_announcement_after_delay', async () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useAnnounce());

      act(() => {
        result.current.announce('Test message');
      });

      act(() => {
        vi.advanceTimersByTime(1000);
      });

      const liveRegion = document.querySelector('[aria-live="polite"]');
      expect(liveRegion?.textContent).toBe('');

      vi.useRealTimers();
    });
  });

  describe('useAccessibility', () => {
    it('should_return_accessibility_utilities', () => {
      const { result } = renderHook(() => useAccessibility());

      expect(result.current.announce).toBeDefined();
      expect(result.current.focusTrapRef).toBeDefined();
      expect(result.current.enableFocusTrap).toBeDefined();
      expect(result.current.disableFocusTrap).toBeDefined();
    });

    it('should_toggle_focus_trap', () => {
      const { result } = renderHook(() => useAccessibility());

      expect(result.current.isFocusTrapEnabled).toBe(false);

      act(() => {
        result.current.enableFocusTrap();
      });
      expect(result.current.isFocusTrapEnabled).toBe(true);

      act(() => {
        result.current.disableFocusTrap();
      });
      expect(result.current.isFocusTrapEnabled).toBe(false);
    });
  });
});
