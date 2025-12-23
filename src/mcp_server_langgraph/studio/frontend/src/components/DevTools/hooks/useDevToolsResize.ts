/**
 * useDevToolsResize Hook
 *
 * Manages DevTools panel resize functionality:
 * - Height state management
 * - Min/max constraints
 * - Persistence to localStorage
 * - Resize state tracking
 */
import { useState, useCallback, useEffect, useMemo } from "react";

import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import { storage } from "../../../utils/storage";
import { setHeight, selectHeight } from "../../../store/slices/devToolsSlice";

// =============================================================================
// Types
// =============================================================================

export interface UseDevToolsResizeOptions {
  /** Minimum panel height in pixels */
  minHeight?: number;
  /** Maximum panel height in pixels */
  maxHeight?: number;
  /** Default panel height in pixels */
  defaultHeight?: number;
  /** localStorage key for persisting height */
  storageKey?: string;
}

export interface UseDevToolsResizeReturn {
  /** Current height in pixels */
  height: number;
  /** Current height as percentage of window height */
  heightPercent: number;
  /** Set panel height (clamped to constraints) */
  setHeight: (height: number) => void;
  /** Reset to default height */
  resetHeight: () => void;
  /** Whether currently resizing */
  isResizing: boolean;
  /** Start resize operation */
  startResize: () => void;
  /** End resize operation */
  endResize: () => void;
  /** Minimum height constraint */
  minHeight: number;
  /** Maximum height constraint */
  maxHeight: number;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY = "devtools-height";
const DEFAULT_MIN_HEIGHT = 100;
const DEFAULT_MAX_HEIGHT = 600;
const DEFAULT_HEIGHT = 200;

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDevToolsResize(
  options: UseDevToolsResizeOptions = {}
): UseDevToolsResizeReturn {
  const {
    minHeight = DEFAULT_MIN_HEIGHT,
    maxHeight = DEFAULT_MAX_HEIGHT,
    defaultHeight = DEFAULT_HEIGHT,
    storageKey = STORAGE_KEY,
  } = options;

  const dispatch = useAppDispatch();
  const height = useAppSelector(selectHeight);

  const [isResizing, setIsResizing] = useState(false);

  /**
   * Clamp value between min and max
   */
  const clamp = useCallback(
    (value: number): number => {
      return Math.min(Math.max(value, minHeight), maxHeight);
    },
    [minHeight, maxHeight]
  );

  /**
   * Load persisted height on mount
   */
  useEffect(() => {
    const persisted = storage.get<number>(storageKey);
    if (persisted !== undefined && !isNaN(persisted)) {
      dispatch(setHeight(clamp(persisted)));
    }
  }, [storageKey, clamp, dispatch]);

  /**
   * Set panel height with clamping and persistence
   */
  const handleSetHeight = useCallback(
    (newHeight: number) => {
      const clampedHeight = clamp(newHeight);
      dispatch(setHeight(clampedHeight));
      storage.set(storageKey, clampedHeight);
    },
    [clamp, dispatch, storageKey]
  );

  /**
   * Reset to default height
   */
  const resetHeight = useCallback(() => {
    dispatch(setHeight(defaultHeight));
    storage.remove(storageKey);
  }, [defaultHeight, dispatch, storageKey]);

  /**
   * Start resize operation
   */
  const startResize = useCallback(() => {
    setIsResizing(true);
  }, []);

  /**
   * End resize operation
   */
  const endResize = useCallback(() => {
    setIsResizing(false);
  }, []);

  /**
   * Calculate height as percentage of window
   */
  const heightPercent = useMemo(() => {
    const windowHeight = typeof window !== "undefined" ? window.innerHeight : 800;
    return Math.round((height / windowHeight) * 100);
  }, [height]);

  return {
    height,
    heightPercent,
    setHeight: handleSetHeight,
    resetHeight,
    isResizing,
    startResize,
    endResize,
    minHeight,
    maxHeight,
  };
}

export default useDevToolsResize;
