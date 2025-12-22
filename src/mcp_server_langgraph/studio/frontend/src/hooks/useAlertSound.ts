/**
 * useAlertSound Hook
 *
 * Custom hook for playing sound notifications for critical alerts.
 *
 * Features:
 * - Play sound for critical alerts
 * - Respect user sound preference
 * - Debounce rapid alerts
 * - Use Web Audio API
 * - Configurable volume
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useCallback, useRef, useState, useEffect } from "react";

// =============================================================================
// Types
// =============================================================================

/**
 * Alert severity for sound triggering
 */
export type SoundAlertSeverity = "critical" | "warning" | "info";

/**
 * Available sound presets
 */
export type AlertSoundPreset =
  | "default"
  | "urgent"
  | "subtle"
  | "classic"
  | "chime"
  | "custom";

/**
 * Sound preset configuration
 */
export interface SoundPresetConfig {
  /** Display name for the preset */
  name: string;
  /** Description of the sound */
  description: string;
  /** URL to the sound file */
  url: string;
  /** Default volume for this preset (0-1) */
  defaultVolume: number;
}

/**
 * Available sound presets catalog
 */
export const ALERT_SOUND_PRESETS: Record<
  Exclude<AlertSoundPreset, "custom">,
  SoundPresetConfig
> = {
  default: {
    name: "Default",
    description: "Standard alert beep",
    url: "/sounds/critical-alert.wav",
    defaultVolume: 0.5,
  },
  urgent: {
    name: "Urgent",
    description: "Attention-grabbing alarm",
    url: "/sounds/urgent-alert.wav",
    defaultVolume: 0.7,
  },
  subtle: {
    name: "Subtle",
    description: "Soft notification chime",
    url: "/sounds/subtle-alert.wav",
    defaultVolume: 0.4,
  },
  classic: {
    name: "Classic",
    description: "Traditional system beep",
    url: "/sounds/classic-alert.wav",
    defaultVolume: 0.5,
  },
  chime: {
    name: "Chime",
    description: "Pleasant bell tone",
    url: "/sounds/chime-alert.wav",
    defaultVolume: 0.5,
  },
};

/**
 * Options for useAlertSound hook
 */
export interface UseAlertSoundOptions {
  /** Whether sound is enabled (default: true) */
  enabled?: boolean;
  /** Play sound for warning alerts too (default: false) */
  warningSound?: boolean;
  /** Debounce time in ms to avoid rapid sounds (default: 3000) */
  debounceMs?: number;
  /** Volume level 0-1 (default: 0.5) */
  volume?: number;
  /** Custom sound URL (default: built-in alert sound) */
  soundUrl?: string;
  /** Sound preset to use (default: "default") */
  preset?: AlertSoundPreset;
}

/**
 * Return type for useAlertSound hook
 */
export interface UseAlertSoundReturn {
  /** Play alert sound for given severity */
  playAlertSound: (severity: SoundAlertSeverity) => void;
  /** Stop currently playing sound */
  stopSound: () => void;
  /** Whether sound is currently playing */
  isPlaying: boolean;
}

/**
 * Options for sound player factory
 */
export interface AlertSoundPlayerOptions {
  /** Custom sound URL */
  soundUrl?: string;
  /** Volume 0-1 */
  volume?: number;
}

/**
 * Sound player interface
 */
export interface AlertSoundPlayer {
  play: () => Promise<void>;
  stop: () => void;
  setVolume: (volume: number) => void;
}

// =============================================================================
// Default Sound URL
// =============================================================================

// Default alert sound - path to audio file
// Falls back to Web Audio API beep if file not available
const DEFAULT_SOUND_URL = "/sounds/critical-alert.wav";

// =============================================================================
// Web Audio API Fallback
// =============================================================================

/**
 * Create a simple beep sound using Web Audio API
 * Used as fallback when audio file is not available
 */
function playBeepFallback(volume: number): void {
  try {
    const audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    // Alert tone: 800Hz for urgency
    oscillator.frequency.value = 800;
    oscillator.type = "sine";

    // Volume control
    gainNode.gain.value = volume;

    // Quick beep pattern: beep-beep
    oscillator.start();

    // Fade out after 200ms
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
    oscillator.stop(audioContext.currentTime + 0.25);

    // Second beep after short pause
    setTimeout(() => {
      try {
        const osc2 = audioContext.createOscillator();
        const gain2 = audioContext.createGain();
        osc2.connect(gain2);
        gain2.connect(audioContext.destination);
        osc2.frequency.value = 1000; // Slightly higher for second beep
        osc2.type = "sine";
        gain2.gain.value = volume;
        osc2.start();
        gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        osc2.stop(audioContext.currentTime + 0.25);
      } catch {
        // Ignore errors in second beep
      }
    }, 300);
  } catch {
    // Web Audio API not available
  }
}

// =============================================================================
// Sound Player Factory
// =============================================================================

/**
 * Create an alert sound player using the Audio API with Web Audio fallback
 */
export function createAlertSoundPlayer(
  options: AlertSoundPlayerOptions = {}
): AlertSoundPlayer {
  const { soundUrl = DEFAULT_SOUND_URL, volume = 0.5 } = options;

  const audio = new Audio();
  audio.src = soundUrl;
  audio.volume = volume;

  // Track if audio file loaded successfully
  let audioFileAvailable = false;

  audio.addEventListener("canplaythrough", () => {
    audioFileAvailable = true;
  });

  audio.addEventListener("error", () => {
    audioFileAvailable = false;
  });

  // Try to load the audio file
  audio.load();

  return {
    play: async () => {
      if (audioFileAvailable) {
        audio.currentTime = 0;
        await audio.play();
      } else {
        // Use Web Audio API fallback
        playBeepFallback(volume);
      }
    },
    stop: () => {
      audio.pause();
      audio.currentTime = 0;
    },
    setVolume: (newVolume: number) => {
      audio.volume = Math.max(0, Math.min(1, newVolume));
    },
  };
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Get sound URL based on preset or custom URL
 */
function getSoundUrl(preset: AlertSoundPreset, customUrl?: string): string {
  if (preset === "custom" && customUrl) {
    return customUrl;
  }
  return ALERT_SOUND_PRESETS[preset === "custom" ? "default" : preset].url;
}

/**
 * Hook for playing alert sound notifications
 *
 * @example
 * ```tsx
 * function AlertsPanel() {
 *   const { playAlertSound } = useAlertSound({
 *     enabled: true,
 *     preset: "urgent",
 *     volume: 0.7,
 *   });
 *
 *   useEffect(() => {
 *     if (newCriticalAlert) {
 *       playAlertSound("critical");
 *     }
 *   }, [newCriticalAlert, playAlertSound]);
 *
 *   return <div>...</div>;
 * }
 * ```
 */
export function useAlertSound(
  options: UseAlertSoundOptions = {}
): UseAlertSoundReturn {
  const {
    enabled = true,
    warningSound = false,
    debounceMs = 3000,
    volume = 0.5,
    soundUrl,
    preset = "default",
  } = options;

  // Get effective sound URL based on preset
  const effectiveSoundUrl = getSoundUrl(preset, soundUrl);

  const [isPlaying, setIsPlaying] = useState(false);
  const lastPlayTimeRef = useRef<number>(0);
  const playerRef = useRef<AlertSoundPlayer | null>(null);

  // Initialize audio player
  useEffect(() => {
    playerRef.current = createAlertSoundPlayer({
      soundUrl: effectiveSoundUrl,
      volume,
    });

    return () => {
      playerRef.current?.stop();
    };
  }, [effectiveSoundUrl, volume]);

  // Update volume when it changes
  useEffect(() => {
    playerRef.current?.setVolume(volume);
  }, [volume]);

  /**
   * Play alert sound for given severity
   */
  const playAlertSound = useCallback(
    (severity: SoundAlertSeverity) => {
      // Check if enabled
      if (!enabled) {
        return;
      }

      // Check if severity should trigger sound
      if (severity === "critical") {
        // Always play for critical
      } else if (severity === "warning" && warningSound) {
        // Play for warning only if warningSound is enabled
      } else {
        // Don't play for info or warning (when warningSound is disabled)
        return;
      }

      // Check debounce
      const now = Date.now();
      if (now - lastPlayTimeRef.current < debounceMs) {
        return;
      }

      // Play sound
      lastPlayTimeRef.current = now;
      setIsPlaying(true);

      playerRef.current
        ?.play()
        .then(() => {
          setIsPlaying(false);
        })
        .catch(() => {
          setIsPlaying(false);
        });
    },
    [enabled, warningSound, debounceMs]
  );

  /**
   * Stop currently playing sound
   */
  const stopSound = useCallback(() => {
    playerRef.current?.stop();
    setIsPlaying(false);
  }, []);

  return {
    playAlertSound,
    stopSound,
    isPlaying,
  };
}
