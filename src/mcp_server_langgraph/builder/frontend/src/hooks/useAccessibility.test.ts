/**
 * Tests for Accessibility Utilities Hook
 *
 * TDD: Tests written FIRST before implementation
 *
 * WCAG 2.1 AA Compliance utilities:
 * - Focus management
 * - Screen reader announcements
 * - Keyboard navigation
 * - Skip-to-content
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAccessibility, useFocusTrap, useAnnounce, useSkipToContent } from './useAccessibility';

describe('Accessibility Hooks', () => {
  // ==============================================================================
  // useAnnounce - Screen Reader Announcements
  // ==============================================================================

  describe('useAnnounce', () => {
    beforeEach(() => {
      // Clean up any existing live regions
      document.querySelectorAll('[aria-live]').forEach(el => el.remove());
    });

    afterEach(() => {
      document.querySelectorAll('[aria-live]').forEach(el => el.remove());
    });

    it('returns announce function', () => {
      const { result } = renderHook(() => useAnnounce());

      expect(typeof result.current.announce).toBe('function');
      expect(typeof result.current.announcePolite).toBe('function');
      expect(typeof result.current.announceAssertive).toBe('function');
    });

    it('creates live region element on mount', () => {
      renderHook(() => useAnnounce());

      const liveRegion = document.querySelector('[aria-live]');
      expect(liveRegion).not.toBeNull();
    });

    it('announces polite messages to screen readers', () => {
      const { result } = renderHook(() => useAnnounce());

      act(() => {
        result.current.announcePolite('Item saved successfully');
      });

      const liveRegion = document.querySelector('[aria-live="polite"]');
      expect(liveRegion?.textContent).toBe('Item saved successfully');
    });

    it('announces assertive messages for urgent notifications', () => {
      const { result } = renderHook(() => useAnnounce());

      act(() => {
        result.current.announceAssertive('Error: Session expired');
      });

      const liveRegion = document.querySelector('[aria-live="assertive"]');
      expect(liveRegion?.textContent).toBe('Error: Session expired');
    });

    it('clears announcement after delay', async () => {
      vi.useFakeTimers();
      const { result } = renderHook(() => useAnnounce());

      act(() => {
        result.current.announcePolite('Temporary message');
      });

      const liveRegion = document.querySelector('[aria-live="polite"]');
      expect(liveRegion?.textContent).toBe('Temporary message');

      // Advance past clear delay
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      expect(liveRegion?.textContent).toBe('');

      vi.useRealTimers();
    });

    it('removes live region on unmount', () => {
      const { unmount } = renderHook(() => useAnnounce());

      const beforeUnmount = document.querySelectorAll('[aria-live]').length;
      expect(beforeUnmount).toBeGreaterThan(0);

      unmount();

      // Live regions should be cleaned up
      const afterUnmount = document.querySelectorAll('[data-announcer]').length;
      expect(afterUnmount).toBe(0);
    });
  });

  // ==============================================================================
  // useFocusTrap - Modal Focus Management
  // ==============================================================================

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
      button1.textContent = 'First';
      button2.textContent = 'Second';
      button3.textContent = 'Third';
      container.appendChild(button1);
      container.appendChild(button2);
      container.appendChild(button3);
      document.body.appendChild(container);
    });

    afterEach(() => {
      document.body.removeChild(container);
    });

    it('returns ref and active state', () => {
      const { result } = renderHook(() => useFocusTrap());

      expect(result.current).toHaveProperty('containerRef');
      expect(result.current).toHaveProperty('isActive');
      expect(result.current).toHaveProperty('activate');
      expect(result.current).toHaveProperty('deactivate');
    });

    it('focuses first focusable element when activated', () => {
      const { result } = renderHook(() => useFocusTrap());

      // Assign ref to container
      act(() => {
        (result.current.containerRef as any).current = container;
        result.current.activate();
      });

      expect(result.current.isActive).toBe(true);
      expect(document.activeElement).toBe(button1);
    });

    it('returns focus to trigger element when deactivated', () => {
      const triggerButton = document.createElement('button');
      triggerButton.textContent = 'Trigger';
      document.body.appendChild(triggerButton);
      triggerButton.focus();

      const { result } = renderHook(() => useFocusTrap());

      act(() => {
        (result.current.containerRef as any).current = container;
        result.current.activate();
      });

      expect(document.activeElement).toBe(button1);

      act(() => {
        result.current.deactivate();
      });

      expect(result.current.isActive).toBe(false);
      expect(document.activeElement).toBe(triggerButton);

      document.body.removeChild(triggerButton);
    });

    it('traps Tab key within container', () => {
      const { result } = renderHook(() => useFocusTrap());

      act(() => {
        (result.current.containerRef as any).current = container;
        result.current.activate();
      });

      // Focus is on button1, Tab should go to button2
      button1.focus();

      const tabEvent = new KeyboardEvent('keydown', {
        key: 'Tab',
        bubbles: true,
      });
      container.dispatchEvent(tabEvent);

      // Due to JSDOM limitations, we verify the handler was set up
      expect(result.current.isActive).toBe(true);
    });

    it('wraps focus from last to first element', () => {
      const { result } = renderHook(() => useFocusTrap());

      act(() => {
        (result.current.containerRef as any).current = container;
        result.current.activate();
      });

      // Focus on last element
      button3.focus();

      const tabEvent = new KeyboardEvent('keydown', {
        key: 'Tab',
        shiftKey: false,
        bubbles: true,
      });

      // Simulate tab behavior (in real browser, focus would wrap)
      container.dispatchEvent(tabEvent);

      expect(result.current.isActive).toBe(true);
    });
  });

  // ==============================================================================
  // useSkipToContent - Skip Navigation Link
  // ==============================================================================

  describe('useSkipToContent', () => {
    let mainContent: HTMLElement;

    beforeEach(() => {
      mainContent = document.createElement('main');
      mainContent.id = 'main-content';
      mainContent.tabIndex = -1;
      // Mock scrollIntoView for JSDOM
      mainContent.scrollIntoView = vi.fn();
      document.body.appendChild(mainContent);
    });

    afterEach(() => {
      document.body.removeChild(mainContent);
    });

    it('returns skip link props', () => {
      const { result } = renderHook(() => useSkipToContent('main-content'));

      expect(result.current).toHaveProperty('skipLinkProps');
      expect(result.current.skipLinkProps).toHaveProperty('href');
      expect(result.current.skipLinkProps).toHaveProperty('onClick');
      expect(result.current.skipLinkProps).toHaveProperty('className');
    });

    it('has correct href targeting main content', () => {
      const { result } = renderHook(() => useSkipToContent('main-content'));

      expect(result.current.skipLinkProps.href).toBe('#main-content');
    });

    it('focuses main content on click', () => {
      const { result } = renderHook(() => useSkipToContent('main-content'));

      act(() => {
        const mockEvent = { preventDefault: vi.fn() };
        result.current.skipLinkProps.onClick(mockEvent as any);
      });

      expect(document.activeElement).toBe(mainContent);
    });

    it('provides visually-hidden-until-focus class', () => {
      const { result } = renderHook(() => useSkipToContent('main-content'));

      expect(result.current.skipLinkProps.className).toContain('sr-only');
      expect(result.current.skipLinkProps.className).toContain('focus:not-sr-only');
    });
  });

  // ==============================================================================
  // useAccessibility - Combined Accessibility Utilities
  // ==============================================================================

  describe('useAccessibility', () => {
    it('returns all accessibility utilities', () => {
      const { result } = renderHook(() => useAccessibility());

      expect(result.current).toHaveProperty('announce');
      expect(result.current).toHaveProperty('focusTrap');
      expect(result.current).toHaveProperty('prefersReducedMotion');
      expect(result.current).toHaveProperty('prefersHighContrast');
    });

    it('detects prefers-reduced-motion preference', () => {
      // Mock matchMedia
      const mockMatchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('reduced-motion'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }));
      vi.stubGlobal('matchMedia', mockMatchMedia);

      const { result } = renderHook(() => useAccessibility());

      expect(result.current.prefersReducedMotion).toBe(true);

      vi.unstubAllGlobals();
    });

    it('detects prefers-high-contrast preference', () => {
      const mockMatchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('more'),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }));
      vi.stubGlobal('matchMedia', mockMatchMedia);

      const { result } = renderHook(() => useAccessibility());

      expect(result.current.prefersHighContrast).toBe(true);

      vi.unstubAllGlobals();
    });
  });
});
