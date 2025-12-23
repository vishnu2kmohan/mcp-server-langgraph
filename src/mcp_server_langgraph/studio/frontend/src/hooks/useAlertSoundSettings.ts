/**
 * useAlertSoundSettings Hook
 *
 * Hook for managing alert sound customization settings with persistence.
 *
 * Features:
 * - Sound preset selection
 * - Volume control
 * - Sound enable/disable toggle
 * - Warning sound toggle
 * - Custom sound URL support
 * - LocalStorage persistence
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useCallback, useState, useEffect, useMemo } from "react";
import type { AlertSoundPreset } from "./useAlertSound";
import { ALERT_SOUND_PRESETS, useAlertSound } from "./useAlertSound";
import { storage } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

/**
 * Alert sound settings
 */
export interface AlertSoundSettings {
  /** Whether sound notifications are enabled */
  enabled: boolean;
  /** Selected sound preset */
  preset: AlertSoundPreset;
  /** Volume level (0-1) */
  volume: number;
  /** Whether to play sound for warning alerts */
  warningSound: boolean;
  /** Custom sound URL (when preset is "custom") */
  customSoundUrl?: string;
  /** Debounce time in ms */
  debounceMs: number;
}

/**
 * Default settings
 */
export const DEFAULT_ALERT_SOUND_SETTINGS: AlertSoundSettings = {
  enabled: true,
  preset: "default",
  volume: 0.5,
  warningSound: false,
  customSoundUrl: undefined,
  debounceMs: 3000,
};

/**
 * Storage key for persisting settings
 */
const STORAGE_KEY = "mcp:alert-sound-settings";

/**
 * Return type for useAlertSoundSettings hook
 */
export interface UseAlertSoundSettingsReturn {
  /** Current settings */
  settings: AlertSoundSettings;
  /** Update a specific setting */
  updateSetting: <K extends keyof AlertSoundSettings>(
    key: K,
    value: AlertSoundSettings[K],
  ) => void;
  /** Update multiple settings at once */
  updateSettings: (updates: Partial<AlertSoundSettings>) => void;
  /** Reset all settings to defaults */
  resetSettings: () => void;
  /** Test the current sound */
  testSound: () => void;
  /** Available presets for UI display */
  availablePresets: Array<{
    id: Exclude<AlertSoundPreset, "custom">;
    name: string;
    description: string;
  }>;
}

// =============================================================================
// Storage helpers
// =============================================================================

function loadSettings(): AlertSoundSettings {
  const stored = storage.get<Partial<AlertSoundSettings>>(STORAGE_KEY, {
    expectObject: true,
  });
  if (stored) {
    return { ...DEFAULT_ALERT_SOUND_SETTINGS, ...stored };
  }
  return DEFAULT_ALERT_SOUND_SETTINGS;
}

function saveSettings(settings: AlertSoundSettings): void {
  storage.set(STORAGE_KEY, settings);
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for managing alert sound settings
 *
 * @example
 * ```tsx
 * function SoundSettings() {
 *   const { settings, updateSetting, testSound, availablePresets } =
 *     useAlertSoundSettings();
 *
 *   return (
 *     <div>
 *       <select
 *         value={settings.preset}
 *         onChange={(e) => updateSetting("preset", e.target.value)}
 *       >
 *         {availablePresets.map((p) => (
 *           <option key={p.id} value={p.id}>{p.name}</option>
 *         ))}
 *       </select>
 *       <button onClick={testSound}>Test Sound</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useAlertSoundSettings(): UseAlertSoundSettingsReturn {
  const [settings, setSettings] = useState<AlertSoundSettings>(loadSettings);

  // Initialize sound player for testing
  const { playAlertSound } = useAlertSound({
    enabled: true, // Always enabled for testing
    preset: settings.preset,
    volume: settings.volume,
    soundUrl: settings.customSoundUrl,
    warningSound: settings.warningSound,
    debounceMs: 500, // Short debounce for testing
  });

  // Persist settings when they change
  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  /**
   * Update a single setting
   */
  const updateSetting = useCallback(
    <K extends keyof AlertSoundSettings>(
      key: K,
      value: AlertSoundSettings[K],
    ) => {
      setSettings((prev) => ({
        ...prev,
        [key]: value,
      }));
    },
    [],
  );

  /**
   * Update multiple settings
   */
  const updateSettings = useCallback((updates: Partial<AlertSoundSettings>) => {
    setSettings((prev) => ({
      ...prev,
      ...updates,
    }));
  }, []);

  /**
   * Reset to defaults
   */
  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_ALERT_SOUND_SETTINGS);
  }, []);

  /**
   * Test current sound
   */
  const testSound = useCallback(() => {
    playAlertSound("critical");
  }, [playAlertSound]);

  /**
   * Available presets for UI
   */
  const availablePresets = useMemo(
    () =>
      (
        Object.entries(ALERT_SOUND_PRESETS) as Array<
          [
            Exclude<AlertSoundPreset, "custom">,
            (typeof ALERT_SOUND_PRESETS)[keyof typeof ALERT_SOUND_PRESETS],
          ]
        >
      ).map(([id, config]) => ({
        id,
        name: config.name,
        description: config.description,
      })),
    [],
  );

  return {
    settings,
    updateSetting,
    updateSettings,
    resetSettings,
    testSound,
    availablePresets,
  };
}

/**
 * Hook to get alert sound options from settings
 * Use this to connect settings to the useAlertSound hook
 */
export function useAlertSoundOptionsFromSettings(): ReturnType<
  typeof useAlertSound
> & {
  settings: AlertSoundSettings;
} {
  const settings = useMemo(loadSettings, []);

  const alertSound = useAlertSound({
    enabled: settings.enabled,
    preset: settings.preset,
    volume: settings.volume,
    soundUrl: settings.customSoundUrl,
    warningSound: settings.warningSound,
    debounceMs: settings.debounceMs,
  });

  return {
    ...alertSound,
    settings,
  };
}
