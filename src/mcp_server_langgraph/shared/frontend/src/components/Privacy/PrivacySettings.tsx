/**
 * PrivacySettings Component
 *
 * Privacy controls for analytics and usage data collection.
 * Respects Do Not Track browser setting.
 */

import React, { useState, useEffect } from 'react';

// ==============================================================================
// Types
// ==============================================================================

export interface PrivacySettingsProps {
  onSettingsChange?: (settings: PrivacyState) => void;
}

export interface PrivacyState {
  analyticsEnabled: boolean;
  usageDataEnabled: boolean;
}

// ==============================================================================
// Helpers
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

function isDoNotTrackEnabled(): boolean {
  if (typeof navigator === 'undefined') return false;
  return navigator.doNotTrack === '1';
}

const STORAGE_KEYS = {
  analytics: 'privacy_analytics_optout',
  usage: 'privacy_usage_optout',
} as const;

// ==============================================================================
// Toggle Component
// ==============================================================================

interface ToggleProps {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description: string;
  disabled?: boolean;
}

function Toggle({ id, checked, onChange, label, description, disabled }: ToggleProps) {
  return (
    <div className="flex items-start gap-4 py-4">
      <div className="flex-1">
        <label htmlFor={id} className="text-sm font-medium text-gray-900 dark:text-white">
          {label}
        </label>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{description}</p>
      </div>
      <button
        id={id}
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={clsx(
          'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent',
          'transition-colors duration-200 ease-in-out',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
          checked ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <span
          className={clsx(
            'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0',
            'transition duration-200 ease-in-out',
            checked ? 'translate-x-5' : 'translate-x-0'
          )}
        />
      </button>
    </div>
  );
}

// ==============================================================================
// PrivacySettings Component
// ==============================================================================

export function PrivacySettings({ onSettingsChange }: PrivacySettingsProps) {
  const [analyticsEnabled, setAnalyticsEnabled] = useState(true);
  const [usageDataEnabled, setUsageDataEnabled] = useState(true);
  const dntEnabled = isDoNotTrackEnabled();

  // Load saved preferences
  useEffect(() => {
    try {
      const analyticsOptout = localStorage.getItem(STORAGE_KEYS.analytics);
      const usageOptout = localStorage.getItem(STORAGE_KEYS.usage);

      if (analyticsOptout === 'true') setAnalyticsEnabled(false);
      if (usageOptout === 'true') setUsageDataEnabled(false);
    } catch {
      // localStorage not available
    }
  }, []);

  const handleAnalyticsChange = (enabled: boolean) => {
    setAnalyticsEnabled(enabled);
    try {
      if (enabled) {
        localStorage.removeItem(STORAGE_KEYS.analytics);
      } else {
        localStorage.setItem(STORAGE_KEYS.analytics, 'true');
      }
    } catch {
      // localStorage not available
    }
    onSettingsChange?.({
      analyticsEnabled: enabled,
      usageDataEnabled,
    });
  };

  const handleUsageChange = (enabled: boolean) => {
    setUsageDataEnabled(enabled);
    try {
      if (enabled) {
        localStorage.removeItem(STORAGE_KEYS.usage);
      } else {
        localStorage.setItem(STORAGE_KEYS.usage, 'true');
      }
    } catch {
      // localStorage not available
    }
    onSettingsChange?.({
      analyticsEnabled,
      usageDataEnabled: enabled,
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
      <h2
        role="heading"
        className="text-lg font-semibold text-gray-900 dark:text-white mb-4"
      >
        Privacy Settings
      </h2>

      {dntEnabled && (
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Do Not Track is enabled in your browser. We respect this setting and
            disable all analytics and tracking automatically.
          </p>
        </div>
      )}

      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        <Toggle
          id="analytics-toggle"
          checked={analyticsEnabled && !dntEnabled}
          onChange={handleAnalyticsChange}
          label="Analytics"
          description="Collect anonymous analytics to help improve the application"
          disabled={dntEnabled}
        />

        <Toggle
          id="usage-toggle"
          checked={usageDataEnabled && !dntEnabled}
          onChange={handleUsageChange}
          label="Usage Data"
          description="Collect feature usage data to understand how features are used"
          disabled={dntEnabled}
        />
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          What we collect
        </h3>
        <ul className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
          <li>• Anonymous session identifiers (no personal information)</li>
          <li>• Feature usage patterns</li>
          <li>• Performance metrics</li>
          <li>• Error reports (without personal data)</li>
        </ul>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-3">
          We never collect or store personal information, browsing history, or
          any data that could identify you.
        </p>
      </div>
    </div>
  );
}

export default PrivacySettings;
