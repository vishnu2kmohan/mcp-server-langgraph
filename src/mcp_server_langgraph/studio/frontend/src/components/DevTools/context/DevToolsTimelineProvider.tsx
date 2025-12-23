/**
 * DevToolsTimelineProvider
 *
 * React context provider for unified timeline state across all DevTools tabs.
 * Provides shared time-travel debugging, event registration, and filtering.
 */
import React, { createContext, useContext, useMemo } from "react";

import {
  useDevToolsTimeline,
  type UseDevToolsTimelineReturn,
  type UseDevToolsTimelineOptions,
  type TimelineEvent,
} from "../hooks/useDevToolsTimeline";

// =============================================================================
// Types
// =============================================================================

export type TimelineContextValue = UseDevToolsTimelineReturn;

export interface DevToolsTimelineProviderProps extends UseDevToolsTimelineOptions {
  /** Child components */
  children: React.ReactNode;
}

// =============================================================================
// Context
// =============================================================================

const TimelineContext = createContext<TimelineContextValue | null>(null);

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to access the shared timeline context.
 * Must be used within a DevToolsTimelineProvider.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useTimelineContext(): TimelineContextValue {
  const context = useContext(TimelineContext);

  if (!context) {
    throw new Error(
      "useTimelineContext must be used within a DevToolsTimelineProvider",
    );
  }

  return context;
}

// =============================================================================
// Provider Component
// =============================================================================

/**
 * Provider component that shares timeline state across all DevTools tabs.
 */
export function DevToolsTimelineProvider({
  children,
  sessionStartTime,
  initialEvents,
  maxEvents,
  playbackInterval,
  playbackSpeed,
  onTimeChange,
  onEventRegistered,
}: DevToolsTimelineProviderProps): React.ReactElement {
  const timeline = useDevToolsTimeline({
    sessionStartTime,
    initialEvents,
    maxEvents,
    playbackInterval,
    playbackSpeed,
    onTimeChange,
    onEventRegistered,
  });

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo<TimelineContextValue>(
    () => timeline,
    [timeline],
  );

  return (
    <TimelineContext.Provider value={contextValue}>
      {children}
    </TimelineContext.Provider>
  );
}

// Re-export types for convenience
export type { TimelineEvent };

export default DevToolsTimelineProvider;
