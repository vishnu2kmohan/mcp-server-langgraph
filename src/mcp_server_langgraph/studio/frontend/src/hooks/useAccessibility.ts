/**
 * useAccessibility Hook
 *
 * Hook to manage accessibility preferences.
 * Features:
 * - Screen reader mode toggle
 * - Reduced motion preference (respects system setting)
 * - High contrast mode
 * - Font size adjustment
 * - Enhanced focus indicators
 * - Persist settings to localStorage
 * - Announce function for screen readers
 *
 * Based on GEMINI.md, AGENTS.md, CLAUDE.md patterns.
 * Implements WCAG 2.1 AA accessibility requirements.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { storage, STORAGE_KEYS } from "../utils/storage";

// ==============================================================================
// Types
// ==============================================================================

export type FontSize = "small" | "medium" | "large";

export interface AccessibilitySettings {
  screenReaderMode: boolean;
  reducedMotion: boolean;
  highContrast: boolean;
  fontSize: FontSize;
  enhancedFocus: boolean;
}

export interface AccessibilityState extends AccessibilitySettings {
  setScreenReaderMode: (enabled: boolean) => void;
  setReducedMotion: (enabled: boolean) => void;
  setHighContrast: (enabled: boolean) => void;
  setFontSize: (size: FontSize) => void;
  setEnhancedFocus: (enabled: boolean) => void;
  resetToDefaults: () => void;
  announce: (message: string, priority?: "polite" | "assertive") => void;
}

// ==============================================================================
// Constants
// ==============================================================================

const STORAGE_KEY = STORAGE_KEYS.ACCESSIBILITY;

const DEFAULT_SETTINGS: AccessibilitySettings = {
  screenReaderMode: false,
  reducedMotion: false,
  highContrast: false,
  fontSize: "medium",
  enhancedFocus: false,
};

const FONT_SIZE_MAP: Record<FontSize, string> = {
  small: "14px",
  medium: "16px",
  large: "18px",
};

// ==============================================================================
// Helper Functions
// ==============================================================================

function loadSettings(): AccessibilitySettings {
  const stored = storage.get<AccessibilitySettings>(STORAGE_KEY, {
    expectObject: true,
  });
  if (stored) {
    return { ...DEFAULT_SETTINGS, ...stored };
  }
  return DEFAULT_SETTINGS;
}

function saveSettings(settings: AccessibilitySettings): void {
  storage.set(STORAGE_KEY, settings);
}

function getSystemReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// ==============================================================================
// Hook
// ==============================================================================

export function useAccessibility(): AccessibilityState {
  // Load initial settings
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    const loaded = loadSettings();
    // Override reducedMotion with system preference if not explicitly set
    const systemReducedMotion = getSystemReducedMotion();
    return {
      ...loaded,
      reducedMotion: loaded.reducedMotion || systemReducedMotion,
    };
  });

  // Apply settings to document
  useEffect(() => {
    const { highContrast, enhancedFocus, fontSize } = settings;

    // High contrast class
    if (highContrast) {
      document.documentElement.classList.add("high-contrast");
    } else {
      document.documentElement.classList.remove("high-contrast");
    }

    // Enhanced focus class
    if (enhancedFocus) {
      document.documentElement.classList.add("enhanced-focus");
    } else {
      document.documentElement.classList.remove("enhanced-focus");
    }

    // Font size CSS variable
    document.documentElement.style.setProperty(
      "--font-size-base",
      FONT_SIZE_MAP[fontSize],
    );
  }, [settings]);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  // Individual setters
  const setScreenReaderMode = useCallback((enabled: boolean) => {
    setSettings((prev) => ({ ...prev, screenReaderMode: enabled }));
  }, []);

  const setReducedMotion = useCallback((enabled: boolean) => {
    setSettings((prev) => ({ ...prev, reducedMotion: enabled }));
  }, []);

  const setHighContrast = useCallback((enabled: boolean) => {
    setSettings((prev) => ({ ...prev, highContrast: enabled }));
  }, []);

  const setFontSize = useCallback((size: FontSize) => {
    setSettings((prev) => ({ ...prev, fontSize: size }));
  }, []);

  const setEnhancedFocus = useCallback((enabled: boolean) => {
    setSettings((prev) => ({ ...prev, enhancedFocus: enabled }));
  }, []);

  const resetToDefaults = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
  }, []);

  // Announce function for screen readers using aria-live regions
  const announce = useCallback(
    (message: string, priority: "polite" | "assertive" = "polite") => {
      // Find or create the live region
      let liveRegion = document.getElementById("accessibility-announcer");
      if (!liveRegion) {
        liveRegion = document.createElement("div");
        liveRegion.id = "accessibility-announcer";
        liveRegion.setAttribute("aria-live", priority);
        liveRegion.setAttribute("aria-atomic", "true");
        liveRegion.className = "sr-only";
        liveRegion.style.cssText =
          "position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;";
        document.body.appendChild(liveRegion);
      }

      // Update the priority if needed
      liveRegion.setAttribute("aria-live", priority);

      // Clear and set message (this triggers the announcement)
      liveRegion.textContent = "";
      // Use requestAnimationFrame to ensure the DOM updates
      requestAnimationFrame(() => {
        if (liveRegion) {
          liveRegion.textContent = message;
        }
      });
    },
    [],
  );

  return useMemo(
    () => ({
      ...settings,
      setScreenReaderMode,
      setReducedMotion,
      setHighContrast,
      setFontSize,
      setEnhancedFocus,
      resetToDefaults,
      announce,
    }),
    [
      settings,
      setScreenReaderMode,
      setReducedMotion,
      setHighContrast,
      setFontSize,
      setEnhancedFocus,
      resetToDefaults,
      announce,
    ],
  );
}

export default useAccessibility;
