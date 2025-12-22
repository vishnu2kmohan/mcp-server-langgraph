/**
 * useAlertSoundSettings Hook Tests
 *
 * TDD tests for alert sound settings management.
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import {
  useAlertSoundSettings,
  DEFAULT_ALERT_SOUND_SETTINGS,
} from "./useAlertSoundSettings";

// =============================================================================
// Mocks
// =============================================================================

// Mock useAlertSound
vi.mock("./useAlertSound", async () => {
  const actual = await vi.importActual("./useAlertSound");
  return {
    ...actual,
    useAlertSound: vi.fn(() => ({
      playAlertSound: vi.fn(),
      stopSound: vi.fn(),
      isPlaying: false,
    })),
  };
});

// Local storage mock state
let mockStorage: Record<string, string> = {};

// Create a properly typed localStorage mock
const createLocalStorageMock = () => ({
  getItem: vi.fn((key: string): string | null => mockStorage[key] ?? null),
  setItem: vi.fn((key: string, value: string): void => {
    mockStorage[key] = value;
  }),
  removeItem: vi.fn((key: string): void => {
    delete mockStorage[key];
  }),
  clear: vi.fn((): void => {
    mockStorage = {};
  }),
  length: 0,
  key: vi.fn((): string | null => null),
});

let localStorageMock = createLocalStorageMock();

// =============================================================================
// Tests
// =============================================================================

describe("useAlertSoundSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the storage
    mockStorage = {};
    // Recreate the mock with fresh spies
    localStorageMock = createLocalStorageMock();
    // Stub localStorage globally
    vi.stubGlobal("localStorage", localStorageMock);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    mockStorage = {};
  });

  describe("Initial state", () => {
    it("should return default settings when no stored settings", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      expect(result.current.settings).toEqual(DEFAULT_ALERT_SOUND_SETTINGS);
    });

    it("should load stored settings from localStorage", () => {
      const storedSettings = {
        enabled: false,
        preset: "urgent",
        volume: 0.8,
      };
      // Pre-populate the store before rendering
      mockStorage["mcp:alert-sound-settings"] = JSON.stringify(storedSettings);

      const { result } = renderHook(() => useAlertSoundSettings());

      expect(result.current.settings.enabled).toBe(false);
      expect(result.current.settings.preset).toBe("urgent");
      expect(result.current.settings.volume).toBe(0.8);
    });

    it("should use defaults for missing stored properties", () => {
      const partialSettings = { volume: 0.9 };
      // Pre-populate the store before rendering
      mockStorage["mcp:alert-sound-settings"] = JSON.stringify(partialSettings);

      const { result } = renderHook(() => useAlertSoundSettings());

      expect(result.current.settings.volume).toBe(0.9);
      expect(result.current.settings.enabled).toBe(true); // Default
      expect(result.current.settings.preset).toBe("default"); // Default
    });
  });

  describe("updateSetting", () => {
    it("should update a single setting", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      act(() => {
        result.current.updateSetting("volume", 0.7);
      });

      expect(result.current.settings.volume).toBe(0.7);
    });

    it("should update enabled setting", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      act(() => {
        result.current.updateSetting("enabled", false);
      });

      expect(result.current.settings.enabled).toBe(false);
    });

    it("should update preset setting", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      act(() => {
        result.current.updateSetting("preset", "subtle");
      });

      expect(result.current.settings.preset).toBe("subtle");
    });

    it("should persist updated settings to localStorage", async () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      act(() => {
        result.current.updateSetting("volume", 0.6);
      });

      // Wait for the useEffect to run and persist
      // The storage utility prefixes keys with "studio-"
      await waitFor(() => {
        expect(
          mockStorage["studio-mcp:alert-sound-settings"],
        ).toBeDefined();
      });

      const savedValue = JSON.parse(
        mockStorage["studio-mcp:alert-sound-settings"],
      );
      expect(savedValue.volume).toBe(0.6);
    });
  });

  describe("updateSettings", () => {
    it("should update multiple settings at once", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      act(() => {
        result.current.updateSettings({
          volume: 0.3,
          preset: "chime",
          enabled: false,
        });
      });

      expect(result.current.settings.volume).toBe(0.3);
      expect(result.current.settings.preset).toBe("chime");
      expect(result.current.settings.enabled).toBe(false);
    });

    it("should only update specified settings", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      act(() => {
        result.current.updateSettings({ volume: 0.2 });
      });

      expect(result.current.settings.volume).toBe(0.2);
      expect(result.current.settings.enabled).toBe(true); // Unchanged
      expect(result.current.settings.preset).toBe("default"); // Unchanged
    });
  });

  describe("resetSettings", () => {
    it("should reset all settings to defaults", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      // Change some settings
      act(() => {
        result.current.updateSettings({
          volume: 0.1,
          preset: "urgent",
          enabled: false,
        });
      });

      // Reset
      act(() => {
        result.current.resetSettings();
      });

      expect(result.current.settings).toEqual(DEFAULT_ALERT_SOUND_SETTINGS);
    });
  });

  describe("testSound", () => {
    it("should return testSound function", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      expect(typeof result.current.testSound).toBe("function");
    });

    it("should call playAlertSound when testSound is called", async () => {
      const mockPlayAlertSound = vi.fn();
      const { useAlertSound } = await import("./useAlertSound");
      (useAlertSound as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        playAlertSound: mockPlayAlertSound,
        stopSound: vi.fn(),
        isPlaying: false,
      });

      const { result } = renderHook(() => useAlertSoundSettings());

      act(() => {
        result.current.testSound();
      });

      expect(mockPlayAlertSound).toHaveBeenCalledWith("critical");
    });
  });

  describe("availablePresets", () => {
    it("should return available presets for UI", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      expect(result.current.availablePresets.length).toBeGreaterThan(0);
      expect(result.current.availablePresets[0]).toHaveProperty("id");
      expect(result.current.availablePresets[0]).toHaveProperty("name");
      expect(result.current.availablePresets[0]).toHaveProperty("description");
    });

    it("should include default preset", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      const defaultPreset = result.current.availablePresets.find(
        (p) => p.id === "default"
      );
      expect(defaultPreset).toBeDefined();
      expect(defaultPreset?.name).toBe("Default");
    });

    it("should include all standard presets", () => {
      const { result } = renderHook(() => useAlertSoundSettings());

      const presetIds = result.current.availablePresets.map((p) => p.id);
      expect(presetIds).toContain("default");
      expect(presetIds).toContain("urgent");
      expect(presetIds).toContain("subtle");
      expect(presetIds).toContain("classic");
      expect(presetIds).toContain("chime");
    });
  });

  describe("error handling", () => {
    it("should handle localStorage errors gracefully", () => {
      // Override the mock to throw an error
      const originalGetItem = localStorageMock.getItem;
      localStorageMock.getItem = vi.fn(() => {
        throw new Error("localStorage error");
      });

      // Should not throw
      const { result } = renderHook(() => useAlertSoundSettings());

      expect(result.current.settings).toEqual(DEFAULT_ALERT_SOUND_SETTINGS);

      // Restore the original mock
      localStorageMock.getItem = originalGetItem;
    });

    it("should handle invalid JSON in localStorage", () => {
      // Set invalid JSON in the store
      mockStorage["mcp:alert-sound-settings"] = "invalid json {";

      // Should not throw and return defaults
      const { result } = renderHook(() => useAlertSoundSettings());

      expect(result.current.settings).toEqual(DEFAULT_ALERT_SOUND_SETTINGS);
    });
  });
});
