/**
 * useAnimationPerformance Hook
 *
 * Monitors animation performance using the Long Animation Frames API.
 * Detects jank (frame drops) and provides metrics for debugging.
 *
 * @see https://developer.chrome.com/docs/web-platform/long-animation-frames
 */
import { useState, useCallback, useEffect, useRef } from "react";

/**
 * Animation performance metrics.
 */
export interface AnimationMetrics {
  /** Number of frames that exceeded the jank threshold */
  droppedFrames: number;
  /** Total frames observed */
  totalFrames: number;
  /** Count of jank events detected */
  jankCount: number;
  /** Average frame time in milliseconds */
  averageFrameTime: number;
  /** Maximum frame time observed */
  maxFrameTime: number;
}

/**
 * Options for the useAnimationPerformance hook.
 */
export interface UseAnimationPerformanceOptions {
  /** Whether to start monitoring immediately */
  enabled?: boolean;
  /** Frame time threshold for jank detection (default: 16.67ms for 60fps) */
  jankThresholdMs?: number;
  /** Callback when jank is detected */
  onJank?: (entry: PerformanceEntry) => void;
  /** Only enable in development mode */
  devOnly?: boolean;
}

/**
 * Return type for the useAnimationPerformance hook.
 */
export interface UseAnimationPerformanceReturn {
  /** Current performance metrics */
  metrics: AnimationMetrics;
  /** Whether monitoring is active */
  isMonitoring: boolean;
  /** Start performance monitoring */
  startMonitoring: () => void;
  /** Stop performance monitoring */
  stopMonitoring: () => void;
  /** Reset metrics to initial values */
  reset: () => void;
}

const INITIAL_METRICS: AnimationMetrics = {
  droppedFrames: 0,
  totalFrames: 0,
  jankCount: 0,
  averageFrameTime: 0,
  maxFrameTime: 0,
};

/**
 * Hook for monitoring animation performance and detecting jank.
 *
 * Uses the Long Animation Frames API (when available) to track frame timing
 * and detect performance issues during animations.
 *
 * @example
 * ```tsx
 * function AnimatedComponent() {
 *   const { metrics, isMonitoring, startMonitoring } = useAnimationPerformance({
 *     enabled: import.meta.env.DEV,
 *     jankThresholdMs: 16.67,
 *     onJank: (entry) => console.warn('Animation jank:', entry),
 *   });
 *
 *   return (
 *     <div>
 *       {isMonitoring && (
 *         <div>Jank count: {metrics.jankCount}</div>
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useAnimationPerformance(
  options: UseAnimationPerformanceOptions = {}
): UseAnimationPerformanceReturn {
  const {
    enabled = false,
    jankThresholdMs = 16.67, // 60fps threshold
    onJank,
    devOnly = true,
  } = options;

  const [metrics, setMetrics] = useState<AnimationMetrics>(INITIAL_METRICS);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const observerRef = useRef<PerformanceObserver | null>(null);
  const frameTimesRef = useRef<number[]>([]);
  const onJankRef = useRef(onJank);

  // Keep callback ref updated
  useEffect(() => {
    onJankRef.current = onJank;
  }, [onJank]);

  /**
   * Process a long animation frame entry.
   */
  const processEntry = useCallback(
    (entry: PerformanceEntry) => {
      const duration = entry.duration;
      frameTimesRef.current.push(duration);

      const isJank = duration > jankThresholdMs;

      setMetrics((prev) => {
        const newTotalFrames = prev.totalFrames + 1;
        const newDroppedFrames = isJank
          ? prev.droppedFrames + 1
          : prev.droppedFrames;
        const newJankCount = isJank ? prev.jankCount + 1 : prev.jankCount;
        const newMaxFrameTime = Math.max(prev.maxFrameTime, duration);

        // Calculate running average
        const totalTime = frameTimesRef.current.reduce((a, b) => a + b, 0);
        const newAverageFrameTime = totalTime / frameTimesRef.current.length;

        return {
          droppedFrames: newDroppedFrames,
          totalFrames: newTotalFrames,
          jankCount: newJankCount,
          averageFrameTime: newAverageFrameTime,
          maxFrameTime: newMaxFrameTime,
        };
      });

      if (isJank && onJankRef.current) {
        onJankRef.current(entry);
      }
    },
    [jankThresholdMs]
  );

  /**
   * Start monitoring animation performance.
   */
  const startMonitoring = useCallback(() => {
    // Check if we should only run in dev mode
    if (devOnly && !import.meta.env.DEV) {
      return;
    }

    // Check if PerformanceObserver and long-animation-frame are supported
    if (typeof PerformanceObserver === "undefined") {
      console.warn(
        "useAnimationPerformance: PerformanceObserver not supported"
      );
      return;
    }

    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          processEntry(entry);
        }
      });

      // Try to observe long-animation-frame (Chrome 123+)
      // Fall back to longtask if not available
      try {
        observer.observe({ type: "long-animation-frame", buffered: true });
      } catch {
        // Fallback to longtask for broader browser support
        observer.observe({ type: "longtask", buffered: true });
      }

      observerRef.current = observer;
      setIsMonitoring(true);
    } catch (error) {
      console.warn("useAnimationPerformance: Failed to start monitoring", error);
    }
  }, [devOnly, processEntry]);

  /**
   * Stop monitoring animation performance.
   */
  const stopMonitoring = useCallback(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
    setIsMonitoring(false);
  }, []);

  /**
   * Reset metrics to initial values.
   */
  const reset = useCallback(() => {
    frameTimesRef.current = [];
    setMetrics(INITIAL_METRICS);
  }, []);

  // Auto-start if enabled
  useEffect(() => {
    if (enabled) {
      startMonitoring();
    }

    return () => {
      stopMonitoring();
    };
  }, [enabled, startMonitoring, stopMonitoring]);

  return {
    metrics,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    reset,
  };
}

export default useAnimationPerformance;
