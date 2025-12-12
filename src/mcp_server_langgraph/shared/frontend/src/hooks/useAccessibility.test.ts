/**
 * useAccessibility Hook Tests
 *
 * TDD: RED phase - Write tests first
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  useAccessibility,
  useFocusTrap,
  useAnnounce,
  useSkipLink,
} from './useAccessibility';
import { useRef } from 'react';

describe('useFocusTrap', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    container.innerHTML = `
      <button id="first">First</button>
      <button id="second">Second</button>
      <button id="third">Third</button>
    `;
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it('returns focusTrapRef and control functions', () => {
    const { result } = renderHook(() => useFocusTrap());

    expect(result.current.focusTrapRef).toBeDefined();
    expect(typeof result.current.activate).toBe('function');
    expect(typeof result.current.deactivate).toBe('function');
  });

  it('traps focus within container when activated', () => {
    const { result } = renderHook(() => useFocusTrap());

    // Attach ref to container
    Object.defineProperty(result.current.focusTrapRef, 'current', {
      value: container,
      writable: true,
    });

    act(() => {
      result.current.activate();
    });

    expect(result.current.isActive).toBe(true);
  });

  it('deactivates focus trap', () => {
    const { result } = renderHook(() => useFocusTrap());

    Object.defineProperty(result.current.focusTrapRef, 'current', {
      value: container,
      writable: true,
    });

    act(() => {
      result.current.activate();
    });

    act(() => {
      result.current.deactivate();
    });

    expect(result.current.isActive).toBe(false);
  });
});

describe('useAnnounce', () => {
  beforeEach(() => {
    // Clear any existing live regions
    document.querySelectorAll('[aria-live]').forEach((el) => el.remove());
  });

  it('returns announce functions', () => {
    const { result } = renderHook(() => useAnnounce());

    expect(typeof result.current.announce).toBe('function');
    expect(typeof result.current.announcePolite).toBe('function');
    expect(typeof result.current.announceAssertive).toBe('function');
  });

  it('announce creates aria-live region with message', () => {
    const { result } = renderHook(() => useAnnounce());

    act(() => {
      result.current.announce('Test message');
    });

    const liveRegion = document.querySelector('[aria-live]');
    expect(liveRegion).toBeTruthy();
    expect(liveRegion?.textContent).toBe('Test message');
  });

  it('announcePolite uses polite politeness', () => {
    const { result } = renderHook(() => useAnnounce());

    act(() => {
      result.current.announcePolite('Polite message');
    });

    const liveRegion = document.querySelector('[aria-live="polite"]');
    expect(liveRegion).toBeTruthy();
    expect(liveRegion?.textContent).toBe('Polite message');
  });

  it('announceAssertive uses assertive politeness', () => {
    const { result } = renderHook(() => useAnnounce());

    act(() => {
      result.current.announceAssertive('Urgent message');
    });

    const liveRegion = document.querySelector('[aria-live="assertive"]');
    expect(liveRegion).toBeTruthy();
    expect(liveRegion?.textContent).toBe('Urgent message');
  });

  it('clears announcement after timeout', async () => {
    vi.useFakeTimers();

    const { result } = renderHook(() => useAnnounce());

    act(() => {
      result.current.announce('Temporary message');
    });

    let liveRegion = document.querySelector('[aria-live]');
    expect(liveRegion?.textContent).toBe('Temporary message');

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    liveRegion = document.querySelector('[aria-live]');
    expect(liveRegion?.textContent).toBe('');

    vi.useRealTimers();
  });
});

describe('useSkipLink', () => {
  it('returns skipLinkProps and targetProps', () => {
    const { result } = renderHook(() => useSkipLink('main-content'));

    expect(result.current.skipLinkProps).toBeDefined();
    expect(result.current.skipLinkProps.href).toBe('#main-content');
    expect(typeof result.current.skipLinkProps.onClick).toBe('function');

    expect(result.current.targetProps).toBeDefined();
    expect(result.current.targetProps.id).toBe('main-content');
    expect(result.current.targetProps.tabIndex).toBe(-1);
  });

  it('onClick focuses the target element', () => {
    const { result } = renderHook(() => useSkipLink('test-target'));

    const target = document.createElement('main');
    target.id = 'test-target';
    target.tabIndex = -1;
    // Mock scrollIntoView since jsdom doesn't implement it
    target.scrollIntoView = vi.fn();
    document.body.appendChild(target);

    const mockEvent = {
      preventDefault: vi.fn(),
    } as unknown as React.MouseEvent;

    act(() => {
      result.current.skipLinkProps.onClick(mockEvent);
    });

    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(document.activeElement).toBe(target);
    expect(target.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth' });

    document.body.removeChild(target);
  });
});

describe('useAccessibility', () => {
  it('combines all accessibility hooks', () => {
    const { result } = renderHook(() => useAccessibility());

    // Focus trap
    expect(result.current.focusTrapRef).toBeDefined();
    expect(typeof result.current.activateFocusTrap).toBe('function');
    expect(typeof result.current.deactivateFocusTrap).toBe('function');

    // Announce
    expect(typeof result.current.announce).toBe('function');
    expect(typeof result.current.announcePolite).toBe('function');
    expect(typeof result.current.announceAssertive).toBe('function');

    // Preferences
    expect(typeof result.current.prefersReducedMotion).toBe('boolean');
    expect(typeof result.current.prefersHighContrast).toBe('boolean');
  });

  it('detects reduced motion preference', () => {
    global.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));

    const { result } = renderHook(() => useAccessibility());
    expect(result.current.prefersReducedMotion).toBe(true);
  });

  it('detects high contrast preference', () => {
    global.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-contrast: more)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));

    const { result } = renderHook(() => useAccessibility());
    expect(result.current.prefersHighContrast).toBe(true);
  });
});
