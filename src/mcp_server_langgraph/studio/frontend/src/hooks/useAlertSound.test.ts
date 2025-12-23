/**
 * useAlertSound Hook Tests
 *
 * TDD tests for the alert sound notification hook.
 * Features:
 * - Play sound for critical alerts
 * - Respect user sound preference
 * - Debounce rapid alerts
 * - Use Web Audio API
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  beforeAll,
  afterAll,
} from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useAlertSound, createAlertSoundPlayer } from "./useAlertSound";

// =============================================================================
// Mocks
// =============================================================================

// Mock Audio API
const mockPlay = vi.fn();
const mockPause = vi.fn();
const mockLoad = vi.fn();

// Shared mock audio instance for tests that check properties
let mockAudioInstance: MockAudio;

// Create a mock Audio class that simulates event callbacks
class MockAudio {
  src = "";
  volume = 0.5;
  currentTime = 0;
  private eventListeners: Map<string, Array<() => void>> = new Map();

  constructor() {
    // Store reference to this instance for test assertions
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    mockAudioInstance = this;
  }

  play = mockPlay;
  pause = mockPause;

  // Simulate successful audio load by triggering canplaythrough
  load = () => {
    mockLoad();
    // Simulate async event triggering
    setTimeout(() => {
      this.triggerEvent("canplaythrough");
    }, 0);
  };

  addEventListener = vi.fn((event: string, callback: () => void) => {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(callback);
  });

  removeEventListener = vi.fn((event: string, callback: () => void) => {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  });

  // Helper to trigger events for testing
  triggerEvent(event: string) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach((cb) => cb());
    }
  }
}

// Store original Audio constructor
const OriginalAudio = globalThis.Audio;

beforeAll(() => {
  // Replace global Audio with mock
  globalThis.Audio = MockAudio as unknown as typeof Audio;
});

afterAll(() => {
  // Restore original Audio
  globalThis.Audio = OriginalAudio;
});

// =============================================================================
// Tests
// =============================================================================

describe("useAlertSound", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockPlay.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("playAlertSound", () => {
    it("should return playAlertSound function", () => {
      const { result } = renderHook(() => useAlertSound());

      expect(typeof result.current.playAlertSound).toBe("function");
    });

    it("should play sound when called with critical severity", async () => {
      const { result } = renderHook(() => useAlertSound({ enabled: true }));

      // Advance timers to trigger canplaythrough event
      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      await act(async () => {
        result.current.playAlertSound("critical");
      });

      expect(mockPlay).toHaveBeenCalled();
    });

    it("should not play sound when disabled", async () => {
      const { result } = renderHook(() => useAlertSound({ enabled: false }));

      await act(async () => {
        result.current.playAlertSound("critical");
      });

      expect(mockPlay).not.toHaveBeenCalled();
    });

    it("should not play sound for warning severity by default", async () => {
      const { result } = renderHook(() => useAlertSound({ enabled: true }));

      await act(async () => {
        result.current.playAlertSound("warning");
      });

      expect(mockPlay).not.toHaveBeenCalled();
    });

    it("should play sound for warning when warningSound is enabled", async () => {
      const { result } = renderHook(() =>
        useAlertSound({ enabled: true, warningSound: true }),
      );

      // Advance timers to trigger canplaythrough event
      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      await act(async () => {
        result.current.playAlertSound("warning");
      });

      expect(mockPlay).toHaveBeenCalled();
    });
  });

  describe("Debouncing", () => {
    it("should debounce rapid sound plays", async () => {
      const { result } = renderHook(() =>
        useAlertSound({ enabled: true, debounceMs: 1000 }),
      );

      // Advance timers to trigger canplaythrough event
      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      // Play first time
      await act(async () => {
        result.current.playAlertSound("critical");
      });

      // Try to play again immediately
      await act(async () => {
        result.current.playAlertSound("critical");
      });

      // Should only have played once
      expect(mockPlay).toHaveBeenCalledTimes(1);
    });

    it("should allow playing after debounce period", async () => {
      const { result } = renderHook(() =>
        useAlertSound({ enabled: true, debounceMs: 1000 }),
      );

      // Advance timers to trigger canplaythrough event
      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      // Play first time
      await act(async () => {
        result.current.playAlertSound("critical");
      });

      // Advance time past debounce
      await act(async () => {
        vi.advanceTimersByTime(1100);
      });

      // Play again
      await act(async () => {
        result.current.playAlertSound("critical");
      });

      // Should have played twice
      expect(mockPlay).toHaveBeenCalledTimes(2);
    });
  });

  describe("Volume", () => {
    it("should set volume on audio element", () => {
      renderHook(() => useAlertSound({ enabled: true, volume: 0.8 }));

      expect(mockAudioInstance.volume).toBe(0.8);
    });

    it("should default to 0.5 volume", () => {
      renderHook(() => useAlertSound({ enabled: true }));

      expect(mockAudioInstance.volume).toBe(0.5);
    });
  });

  describe("isPlaying state", () => {
    it("should return isPlaying state", () => {
      const { result } = renderHook(() => useAlertSound());

      expect(typeof result.current.isPlaying).toBe("boolean");
    });

    it("should initially be false", () => {
      const { result } = renderHook(() => useAlertSound());

      expect(result.current.isPlaying).toBe(false);
    });
  });

  describe("stopSound", () => {
    it("should return stopSound function", () => {
      const { result } = renderHook(() => useAlertSound());

      expect(typeof result.current.stopSound).toBe("function");
    });

    it("should pause audio when called", async () => {
      const { result } = renderHook(() => useAlertSound({ enabled: true }));

      // Advance timers to trigger canplaythrough event
      await act(async () => {
        vi.advanceTimersByTime(10);
      });

      await act(async () => {
        result.current.playAlertSound("critical");
      });

      act(() => {
        result.current.stopSound();
      });

      expect(mockPause).toHaveBeenCalled();
    });
  });
});

describe("createAlertSoundPlayer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockPlay.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should create a sound player", () => {
    const player = createAlertSoundPlayer();

    expect(player).toBeDefined();
    expect(typeof player.play).toBe("function");
    expect(typeof player.stop).toBe("function");
  });

  it("should play sound when play is called", async () => {
    const player = createAlertSoundPlayer();

    // Advance timers to trigger canplaythrough event
    vi.advanceTimersByTime(10);

    await player.play();

    expect(mockPlay).toHaveBeenCalled();
  });

  it("should stop sound when stop is called", async () => {
    const player = createAlertSoundPlayer();

    // Advance timers to trigger canplaythrough event
    vi.advanceTimersByTime(10);

    await player.play();
    player.stop();

    expect(mockPause).toHaveBeenCalled();
  });

  it("should allow custom sound URL", () => {
    const customUrl = "/sounds/custom-alert.mp3";
    createAlertSoundPlayer({ soundUrl: customUrl });

    expect(mockAudioInstance.src).toBe(customUrl);
  });

  it("should allow custom volume", () => {
    createAlertSoundPlayer({ volume: 0.3 });

    expect(mockAudioInstance.volume).toBe(0.3);
  });

  describe("Web Audio API Fallback", () => {
    it("should not call HTML Audio play when audio file not available", async () => {
      const player = createAlertSoundPlayer();

      // DON'T advance timers - this means canplaythrough never fires
      // and audioFileAvailable stays false, so it uses fallback path
      // (Web Audio API or silent fallback)

      await player.play();

      // Should NOT have called the HTML Audio play since file isn't available
      expect(mockPlay).not.toHaveBeenCalled();
    });

    it("should load the audio file on creation", () => {
      createAlertSoundPlayer();

      // Should call load() to try to load the audio file
      expect(mockLoad).toHaveBeenCalled();
    });
  });
});
