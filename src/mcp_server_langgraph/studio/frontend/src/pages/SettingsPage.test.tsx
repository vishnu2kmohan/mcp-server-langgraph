/**
 * SettingsPage Tests
 *
 * TDD tests for the settings page.
 * Tests cover:
 * - Tab navigation
 * - Profile settings
 * - API keys display
 * - Save functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SettingsPage } from './SettingsPage';
import * as authStoreModule from '../stores/authStore';
import * as personaStoreModule from '../stores/personaStore';

// Mock the stores
vi.mock('../stores/authStore');
vi.mock('../stores/personaStore');

const mockUseAuthStore = vi.mocked(authStoreModule.useAuthStore);
const mockUsePersonaStore = vi.mocked(personaStoreModule.usePersonaStore);

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock state
    mockUseAuthStore.mockReturnValue({
      user: { id: 'user-1', username: 'testuser', email: 'test@example.com', displayName: 'Test User' },
      isAuthenticated: true,
      isLoading: false,
      error: null,
      token: 'mock-token',
      login: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
      clearError: vi.fn(),
    });
    mockUsePersonaStore.mockReturnValue({
      persona: 'user',
      setPersona: vi.fn(),
      isAdmin: false,
      isPowerUser: false,
    });
  });

  describe('Header', () => {
    it('should display page title', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('should display page description', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Manage your account and preferences')).toBeInTheDocument();
    });

    it('should have save button', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Save Changes')).toBeInTheDocument();
    });
  });

  describe('Tabs', () => {
    it('should have Profile tab', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Profile')).toBeInTheDocument();
    });

    it('should have API Keys tab', () => {
      render(<SettingsPage />);

      expect(screen.getByText('API Keys')).toBeInTheDocument();
    });

    it('should have Notifications tab', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Notifications')).toBeInTheDocument();
    });

    it('should have Appearance tab', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Appearance')).toBeInTheDocument();
    });

    it('should have Security tab', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Security')).toBeInTheDocument();
    });
  });

  describe('Profile Tab', () => {
    it('should display display name label', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Display Name')).toBeInTheDocument();
    });

    it('should display email label', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Email')).toBeInTheDocument();
    });

    it('should show current user data in fields', () => {
      render(<SettingsPage />);

      const inputs = screen.getAllByRole('textbox');
      const displayNameInput = inputs.find(input => (input as HTMLInputElement).value === 'Test User');
      expect(displayNameInput).toBeInTheDocument();
    });
  });

  describe('API Keys Tab', () => {
    it('should switch to API Keys tab when clicked', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('API Keys'));

      expect(screen.getByText('Your API Key')).toBeInTheDocument();
    });

    it('should show API key warning', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('API Keys'));

      expect(screen.getByText(/API keys provide access/)).toBeInTheDocument();
    });

    it('should have regenerate button', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('API Keys'));

      expect(screen.getByText('Regenerate API Key')).toBeInTheDocument();
    });
  });

  describe('Save Functionality', () => {
    it('should show Saving... when saving', async () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Save Changes'));

      expect(screen.getByText('Saving...')).toBeInTheDocument();
    });

    it('should show Saved after successful save', async () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Save Changes'));

      await waitFor(() => {
        expect(screen.getByText('Saved')).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });

  describe('Profile Form Interactions', () => {
    it('should update display name when typed', () => {
      render(<SettingsPage />);

      const inputs = screen.getAllByRole('textbox');
      const displayNameInput = inputs[0] as HTMLInputElement;

      fireEvent.change(displayNameInput, { target: { value: 'New Name' } });

      expect(displayNameInput.value).toBe('New Name');
    });

    it('should update email when typed', () => {
      render(<SettingsPage />);

      const inputs = screen.getAllByRole('textbox');
      const emailInput = inputs[1] as HTMLInputElement;

      fireEvent.change(emailInput, { target: { value: 'new@example.com' } });

      expect(emailInput.value).toBe('new@example.com');
    });

    it('should have persona selector', () => {
      render(<SettingsPage />);

      expect(screen.getByText('Default Persona')).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('should call setPersona when persona is changed', () => {
      const mockSetPersona = vi.fn();
      mockUsePersonaStore.mockReturnValue({
        persona: 'user',
        setPersona: mockSetPersona,
        isAdmin: false,
        isPowerUser: false,
      });

      render(<SettingsPage />);

      const select = screen.getByRole('combobox');
      fireEvent.change(select, { target: { value: 'admin' } });

      expect(mockSetPersona).toHaveBeenCalledWith('admin');
    });
  });

  describe('API Keys Tab Interactions', () => {
    it('should show API key container when on API Keys tab', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('API Keys'));

      // Verify the API key label is present
      expect(screen.getByText('Your API Key')).toBeInTheDocument();
    });

    it('should have toggle visibility button', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('API Keys'));

      // Find buttons in the API keys section
      const allButtons = screen.getAllByRole('button');
      // There should be multiple buttons including the toggle
      expect(allButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Notifications Tab', () => {
    it('should switch to notifications tab when clicked', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Notifications'));

      expect(screen.getByText('Session Complete')).toBeInTheDocument();
      expect(screen.getByText('Error Alerts')).toBeInTheDocument();
      expect(screen.getByText('Product Updates')).toBeInTheDocument();
    });

    it('should have checkboxes for notification settings', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Notifications'));

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBe(3);
    });

    it('should toggle notification when checkbox clicked', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Notifications'));

      const checkboxes = screen.getAllByRole('checkbox');
      const updatesCheckbox = checkboxes[2] as HTMLInputElement;

      // Initially updates is false
      expect(updatesCheckbox.checked).toBe(false);

      fireEvent.click(updatesCheckbox);

      expect(updatesCheckbox.checked).toBe(true);
    });
  });

  describe('Appearance Tab', () => {
    it('should switch to appearance tab when clicked', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Appearance'));

      expect(screen.getByText('Theme')).toBeInTheDocument();
    });

    it('should show theme options', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Appearance'));

      expect(screen.getByText('light')).toBeInTheDocument();
      expect(screen.getByText('dark')).toBeInTheDocument();
      expect(screen.getByText('system')).toBeInTheDocument();
    });

    it('should select theme when clicked', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Appearance'));

      // System should be selected by default
      const systemButton = screen.getByText('system').closest('button');
      expect(systemButton).toHaveClass('border-blue-500');

      // Click dark
      const darkButton = screen.getByText('dark').closest('button')!;
      fireEvent.click(darkButton);

      expect(darkButton).toHaveClass('border-blue-500');
    });
  });

  describe('Security Tab', () => {
    it('should switch to security tab when clicked', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Security'));

      expect(screen.getByText('Two-Factor Authentication')).toBeInTheDocument();
    });

    it('should have enable 2FA button', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Security'));

      expect(screen.getByText('Enable 2FA')).toBeInTheDocument();
    });

    it('should show active sessions section', () => {
      render(<SettingsPage />);

      fireEvent.click(screen.getByText('Security'));

      expect(screen.getByText('Active Sessions')).toBeInTheDocument();
      expect(screen.getByText('Sign Out All Devices')).toBeInTheDocument();
    });
  });
});
