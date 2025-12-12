/**
 * Tests for PrivacySettings Component
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PrivacySettings } from './PrivacySettings';

describe('PrivacySettings Component', () => {
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  };

  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders privacy settings heading', () => {
      render(<PrivacySettings />);
      expect(screen.getByRole('heading', { name: /privacy settings/i })).toBeInTheDocument();
    });

    it('renders analytics toggle', () => {
      render(<PrivacySettings />);
      expect(screen.getByRole('switch', { name: /analytics/i })).toBeInTheDocument();
    });

    it('renders usage data toggle', () => {
      render(<PrivacySettings />);
      expect(screen.getByRole('switch', { name: /usage data/i })).toBeInTheDocument();
    });

    it('displays Do Not Track status when enabled', () => {
      Object.defineProperty(navigator, 'doNotTrack', {
        value: '1',
        configurable: true,
      });

      render(<PrivacySettings />);
      expect(screen.getByText(/do not track is enabled/i)).toBeInTheDocument();

      Object.defineProperty(navigator, 'doNotTrack', {
        value: null,
        configurable: true,
      });
    });
  });

  // ==============================================================================
  // Toggle Tests
  // ==============================================================================

  describe('Toggle Functionality', () => {
    it('toggles analytics opt-out', () => {
      localStorageMock.getItem.mockReturnValue(null);
      render(<PrivacySettings />);

      const toggle = screen.getByRole('switch', { name: /analytics/i });
      expect(toggle).toBeChecked(); // Default on

      fireEvent.click(toggle);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'privacy_analytics_optout',
        'true'
      );
    });

    it('toggles usage data collection', () => {
      localStorageMock.getItem.mockReturnValue(null);
      render(<PrivacySettings />);

      const toggle = screen.getByRole('switch', { name: /usage data/i });
      expect(toggle).toBeChecked(); // Default on

      fireEvent.click(toggle);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'privacy_usage_optout',
        'true'
      );
    });

    it('loads saved preferences from localStorage', () => {
      localStorageMock.getItem.mockImplementation((key: string) => {
        if (key === 'privacy_analytics_optout') return 'true';
        if (key === 'privacy_usage_optout') return 'true';
        return null;
      });

      render(<PrivacySettings />);

      const analyticsToggle = screen.getByRole('switch', { name: /analytics/i });
      const usageToggle = screen.getByRole('switch', { name: /usage data/i });

      expect(analyticsToggle).not.toBeChecked();
      expect(usageToggle).not.toBeChecked();
    });
  });

  // ==============================================================================
  // Callback Tests
  // ==============================================================================

  describe('Callbacks', () => {
    it('calls onSettingsChange when toggled', () => {
      const onSettingsChange = vi.fn();
      localStorageMock.getItem.mockReturnValue(null);

      render(<PrivacySettings onSettingsChange={onSettingsChange} />);

      const toggle = screen.getByRole('switch', { name: /analytics/i });
      fireEvent.click(toggle);

      expect(onSettingsChange).toHaveBeenCalledWith({
        analyticsEnabled: false,
        usageDataEnabled: true,
      });
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has proper ARIA labels for toggles', () => {
      render(<PrivacySettings />);

      expect(screen.getByRole('switch', { name: /analytics/i })).toBeInTheDocument();
      expect(screen.getByRole('switch', { name: /usage data/i })).toBeInTheDocument();
    });

    it('has descriptive text for each setting', () => {
      render(<PrivacySettings />);

      expect(screen.getByText(/collect anonymous analytics/i)).toBeInTheDocument();
      expect(screen.getByText(/collect feature usage/i)).toBeInTheDocument();
    });
  });
});
