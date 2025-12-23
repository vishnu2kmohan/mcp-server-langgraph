/**
 * useDevToolsTimeline Hook
 *
 * Unified time-travel debugging across all DevTools tabs.
 * Synchronizes logs, metrics, alerts, traces (OTEL), and LangGraph execution.
 */
import { useState, useCallback, useMemo, useRef, useEffect } from "react";

// =============================================================================
// Types
// =============================================================================

export type TimelineEventType =
  | "console"
  | "network"
  | "state"
  | "trace"
  | "alert"
  | "metric"
  | "otel_span"
  | "langgraph_node";

export interface TimelineEvent {
  /** Unique event ID */
  id: string;
  /** Event type */
  type: TimelineEventType;
  /** Absolute timestamp (ms since epoch) */
  timestamp: number;
  /** Relative time from session start (ms) */
  relativeTime: number;
  /** Source identifier */
  source: string;
  /** Event payload data */
  data: Record<string, unknown>;
}

export interface TimelineBookmark {
  /** Bookmark ID */
  id: string;
  /** Timestamp the bookmark points to */
  timestamp: number;
  /** User-provided label */
  label: string;
}

export interface SpanHierarchy {
  /** Root span of the trace */
  root: TimelineEvent | null;
  /** Direct children of the root */
  children: TimelineEvent[];
  /** Maximum depth of the hierarchy */
  depth: number;
}

export interface SpanStats {
  /** Total number of spans */
  totalSpans: number;
  /** Total duration across all spans */
  totalDuration: number;
  /** Average span duration */
  averageDuration: number;
}

export interface TimeWindow {
  /** Start of the time window */
  start: number;
  /** End of the time window */
  end: number;
}

export interface ActiveFilters {
  /** Whether a time window is active */
  hasTimeWindow: boolean;
  /** Whether a span is selected */
  hasSpanSelection: boolean;
  /** Whether a type filter is active */
  hasTypeFilter: boolean;
  /** Currently active type filter (if any) */
  typeFilter: TimelineEventType[] | null;
}

export interface UseDevToolsTimelineOptions {
  /** Session start timestamp */
  sessionStartTime?: number;
  /** Initial events to load */
  initialEvents?: TimelineEvent[];
  /** Maximum events to store */
  maxEvents?: number;
  /** Playback interval (ms) */
  playbackInterval?: number;
  /** Playback speed multiplier */
  playbackSpeed?: number;
  /** Callback when time changes */
  onTimeChange?: (time: number) => void;
  /** Callback when event is registered */
  onEventRegistered?: (event: TimelineEvent) => void;
}

export interface UseDevToolsTimelineReturn {
  // State
  events: TimelineEvent[];
  currentTime: number;
  timeRange: { start: number; end: number };
  isPlaying: boolean;
  isAtEnd: boolean;
  isLiveMode: boolean;
  playbackSpeed: number;
  bookmarks: TimelineBookmark[];
  sessionStartTime: number;
  timeWindow: TimeWindow | null;
  selectedSpanId: string | null;

  // Event registration
  registerEvent: (
    event: Omit<TimelineEvent, "id" | "relativeTime" | "source"> & {
      source?: string;
    },
  ) => void;

  // Time navigation
  setCurrentTime: (time: number) => void;
  jumpToStart: () => void;
  jumpToEnd: () => void;
  stepForward: () => void;
  stepBackward: () => void;

  // Playback
  startPlayback: () => void;
  stopPlayback: () => void;
  setPlaybackSpeed: (speed: number) => void;

  // Filtering
  getEventsAtCurrentTime: () => TimelineEvent[];
  getEventsByType: (type: TimelineEventType) => TimelineEvent[];
  getEventsInRange: (start: number, end: number) => TimelineEvent[];
  getVisibleEvents: () => TimelineEvent[];
  setTypeFilter: (types: TimelineEventType[]) => void;

  // Time window and span selection
  setTimeWindow: (start: number, end: number) => void;
  clearTimeWindow: () => void;
  getEventsInWindow: () => TimelineEvent[];
  selectSpan: (spanId: string) => void;
  clearSpanSelection: () => void;
  getEventsInSelectedSpan: () => TimelineEvent[];
  getActiveFilters: () => ActiveFilters;
  getFilteredEvents: () => TimelineEvent[];

  // Correlation
  getEventsNear: (timestamp: number, windowMs: number) => TimelineEvent[];
  getCorrelatedEvents: (correlationId: string) => TimelineEvent[];
  getPreviousEventOfType: (
    eventId: string,
    type: TimelineEventType,
  ) => TimelineEvent | null;
  getEventsByTraceId: (traceId: string) => TimelineEvent[];

  // OTEL Spans
  getSpansByTraceId: (traceId: string) => TimelineEvent[];
  getSpanHierarchy: (traceId: string) => SpanHierarchy;
  getSpanStats: (traceId: string) => SpanStats;
  getSlowSpans: (thresholdMs: number) => TimelineEvent[];
  getErrorSpans: () => TimelineEvent[];

  // LangGraph
  getLangGraphNodeEvents: (nodeId: string) => TimelineEvent[];
  getLangGraphStateAtCurrentTime: () => Record<string, string>;

  // Bookmarks
  addBookmark: (label: string) => void;
  removeBookmark: (id: string) => void;
  jumpToBookmark: (id: string) => void;

  // Clear/Reset
  clearEvents: () => void;
  clearEventsByType: (type: TimelineEventType) => void;
  reset: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_MAX_EVENTS = 5000;
const DEFAULT_PLAYBACK_INTERVAL = 100;
const DEFAULT_PLAYBACK_SPEED = 1;

// =============================================================================
// Helper Functions
// =============================================================================

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function insertSorted(
  events: TimelineEvent[],
  event: TimelineEvent,
): TimelineEvent[] {
  const result = [...events];
  const insertIndex = result.findIndex((e) => e.timestamp > event.timestamp);
  if (insertIndex === -1) {
    result.push(event);
  } else {
    result.splice(insertIndex, 0, event);
  }
  return result;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDevToolsTimeline(
  options: UseDevToolsTimelineOptions = {},
): UseDevToolsTimelineReturn {
  const {
    sessionStartTime: initialSessionStart = Date.now(),
    initialEvents = [],
    maxEvents = DEFAULT_MAX_EVENTS,
    playbackInterval = DEFAULT_PLAYBACK_INTERVAL,
    playbackSpeed: initialPlaybackSpeed = DEFAULT_PLAYBACK_SPEED,
    onTimeChange,
    onEventRegistered,
  } = options;

  const [sessionStartTime] = useState(initialSessionStart);
  const [events, setEvents] = useState<TimelineEvent[]>(initialEvents);
  const [currentTime, setCurrentTimeState] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [playbackSpeed, setPlaybackSpeedState] = useState(initialPlaybackSpeed);
  const [bookmarks, setBookmarks] = useState<TimelineBookmark[]>([]);
  const [typeFilter, setTypeFilter] = useState<TimelineEventType[] | null>(
    null,
  );
  const [timeWindow, setTimeWindowState] = useState<TimeWindow | null>(null);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);

  // Refs for callbacks
  const onTimeChangeRef = useRef(onTimeChange);
  onTimeChangeRef.current = onTimeChange;
  const onEventRegisteredRef = useRef(onEventRegistered);
  onEventRegisteredRef.current = onEventRegistered;
  const playbackIntervalRef = useRef(playbackInterval);
  playbackIntervalRef.current = playbackInterval;
  const playbackSpeedRef = useRef(playbackSpeed);
  playbackSpeedRef.current = playbackSpeed;

  // Keep currentTime ref in sync for callbacks
  const currentTimeRef = useRef(currentTime);
  currentTimeRef.current = currentTime;

  // Computed values
  const timeRange = useMemo(() => {
    if (events.length === 0) return { start: 0, end: 0 };
    return {
      start: events[0].timestamp,
      end: events[events.length - 1].timestamp,
    };
  }, [events]);

  const isAtEnd = useMemo(() => {
    if (events.length === 0) return true;
    return currentTime >= timeRange.end;
  }, [currentTime, timeRange, events.length]);

  // ==========================================================================
  // Event Registration
  // ==========================================================================

  const registerEvent = useCallback(
    (
      eventInput: Omit<TimelineEvent, "id" | "relativeTime" | "source"> & {
        source?: string;
      },
    ) => {
      const event: TimelineEvent = {
        id: generateId(),
        type: eventInput.type,
        timestamp: eventInput.timestamp,
        relativeTime: eventInput.timestamp - sessionStartTime,
        source: eventInput.source ?? eventInput.type,
        data: eventInput.data,
      };

      setEvents((prev) => {
        let updated = insertSorted(prev, event);
        if (updated.length > maxEvents) {
          updated = updated.slice(-maxEvents);
        }
        return updated;
      });

      // Auto-advance in live mode
      if (isLiveMode) {
        setCurrentTimeState(event.timestamp);
      }

      onEventRegisteredRef.current?.(event);
    },
    [sessionStartTime, maxEvents, isLiveMode],
  );

  // ==========================================================================
  // Time Navigation
  // ==========================================================================

  const setCurrentTime = useCallback(
    (time: number) => {
      const clampedTime = Math.max(
        timeRange.start || 0,
        Math.min(time, timeRange.end || time),
      );
      setCurrentTimeState(clampedTime);
      setIsLiveMode(false);
      onTimeChangeRef.current?.(clampedTime);
    },
    [timeRange],
  );

  const jumpToStart = useCallback(() => {
    if (events.length > 0) {
      setCurrentTimeState(events[0].timestamp);
      setIsLiveMode(false);
    }
  }, [events]);

  const jumpToEnd = useCallback(() => {
    if (events.length > 0) {
      setCurrentTimeState(events[events.length - 1].timestamp);
      setIsLiveMode(true);
    }
  }, [events]);

  const stepForward = useCallback(() => {
    const nextEvent = events.find((e) => e.timestamp > currentTime);
    if (nextEvent) {
      setCurrentTimeState(nextEvent.timestamp);
      setIsLiveMode(false);
    }
  }, [events, currentTime]);

  const stepBackward = useCallback(() => {
    const prevEvents = events.filter((e) => e.timestamp < currentTime);
    if (prevEvents.length > 0) {
      setCurrentTimeState(prevEvents[prevEvents.length - 1].timestamp);
      setIsLiveMode(false);
    }
  }, [events, currentTime]);

  // ==========================================================================
  // Playback
  // ==========================================================================

  const startPlayback = useCallback(() => {
    if (events.length > 0) {
      setCurrentTimeState(events[0].timestamp);
      setIsPlaying(true);
      setIsLiveMode(false);
    }
  }, [events]);

  const stopPlayback = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const setPlaybackSpeed = useCallback((speed: number) => {
    setPlaybackSpeedState(speed);
    playbackSpeedRef.current = speed;
  }, []);

  // Keep timeRange ref in sync
  const timeRangeRef = useRef(timeRange);
  timeRangeRef.current = timeRange;

  // Playback effect
  useEffect(() => {
    if (!isPlaying || events.length === 0) return;

    const timer = setInterval(() => {
      setCurrentTimeState((prev) => {
        const increment =
          playbackIntervalRef.current * playbackSpeedRef.current;
        const newTime = prev + increment;
        const endTime = timeRangeRef.current.end;

        if (newTime >= endTime) {
          setIsPlaying(false);
          return endTime;
        }

        return newTime;
      });
    }, playbackIntervalRef.current);

    return () => clearInterval(timer);
  }, [isPlaying, events.length]);

  // ==========================================================================
  // Event Filtering
  // ==========================================================================

  const getEventsAtCurrentTime = useCallback((): TimelineEvent[] => {
    return events.filter((e) => e.timestamp <= currentTime);
  }, [events, currentTime]);

  const getEventsByType = useCallback(
    (type: TimelineEventType): TimelineEvent[] => {
      return events.filter((e) => e.type === type);
    },
    [events],
  );

  const getEventsInRange = useCallback(
    (start: number, end: number): TimelineEvent[] => {
      return events.filter((e) => e.timestamp >= start && e.timestamp <= end);
    },
    [events],
  );

  const getVisibleEvents = useCallback((): TimelineEvent[] => {
    let filtered = events.filter((e) => e.timestamp <= currentTime);
    if (typeFilter && typeFilter.length > 0) {
      filtered = filtered.filter((e) => typeFilter.includes(e.type));
    }
    return filtered;
  }, [events, currentTime, typeFilter]);

  // ==========================================================================
  // Time Window and Span Selection
  // ==========================================================================

  const setTimeWindow = useCallback((start: number, end: number) => {
    setTimeWindowState({ start, end });
  }, []);

  const clearTimeWindow = useCallback(() => {
    setTimeWindowState(null);
  }, []);

  const getEventsInWindow = useCallback((): TimelineEvent[] => {
    if (!timeWindow) return events;
    return events.filter(
      (e) => e.timestamp >= timeWindow.start && e.timestamp <= timeWindow.end,
    );
  }, [events, timeWindow]);

  const selectSpan = useCallback((spanId: string) => {
    setSelectedSpanId(spanId);
  }, []);

  const clearSpanSelection = useCallback(() => {
    setSelectedSpanId(null);
  }, []);

  const getEventsInSelectedSpan = useCallback((): TimelineEvent[] => {
    if (!selectedSpanId) return [];

    // Find the selected span
    const spanEvent = events.find(
      (e) => e.type === "otel_span" && e.data.spanId === selectedSpanId,
    );

    if (!spanEvent) return [];

    const spanStart = spanEvent.timestamp;
    const spanDuration = (spanEvent.data.duration as number) || 0;
    const spanEnd = spanStart + spanDuration;

    // Return all non-span events that occurred during this span
    return events.filter(
      (e) =>
        e.type !== "otel_span" &&
        e.timestamp >= spanStart &&
        e.timestamp <= spanEnd,
    );
  }, [events, selectedSpanId]);

  const getActiveFilters = useCallback((): ActiveFilters => {
    return {
      hasTimeWindow: timeWindow !== null,
      hasSpanSelection: selectedSpanId !== null,
      hasTypeFilter: typeFilter !== null && typeFilter.length > 0,
      typeFilter,
    };
  }, [timeWindow, selectedSpanId, typeFilter]);

  const getFilteredEvents = useCallback((): TimelineEvent[] => {
    let filtered = events;

    // Apply time window filter
    if (timeWindow) {
      filtered = filtered.filter(
        (e) => e.timestamp >= timeWindow.start && e.timestamp <= timeWindow.end,
      );
    }

    // Apply span selection filter (events within span duration)
    if (selectedSpanId) {
      const spanEvent = events.find(
        (e) => e.type === "otel_span" && e.data.spanId === selectedSpanId,
      );

      if (spanEvent) {
        const spanStart = spanEvent.timestamp;
        const spanDuration = (spanEvent.data.duration as number) || 0;
        const spanEnd = spanStart + spanDuration;

        filtered = filtered.filter(
          (e) => e.timestamp >= spanStart && e.timestamp <= spanEnd,
        );
      }
    }

    // Apply type filter
    if (typeFilter && typeFilter.length > 0) {
      filtered = filtered.filter((e) => typeFilter.includes(e.type));
    }

    return filtered;
  }, [events, timeWindow, selectedSpanId, typeFilter]);

  // ==========================================================================
  // Event Correlation
  // ==========================================================================

  const getEventsNear = useCallback(
    (timestamp: number, windowMs: number): TimelineEvent[] => {
      return events.filter(
        (e) => Math.abs(e.timestamp - timestamp) <= windowMs,
      );
    },
    [events],
  );

  const getCorrelatedEvents = useCallback(
    (correlationId: string): TimelineEvent[] => {
      return events.filter((e) => e.data.correlationId === correlationId);
    },
    [events],
  );

  const getPreviousEventOfType = useCallback(
    (eventId: string, type: TimelineEventType): TimelineEvent | null => {
      const eventIndex = events.findIndex((e) => e.id === eventId);
      if (eventIndex === -1) return null;

      for (let i = eventIndex - 1; i >= 0; i--) {
        if (events[i].type === type) {
          return events[i];
        }
      }
      return null;
    },
    [events],
  );

  const getEventsByTraceId = useCallback(
    (traceId: string): TimelineEvent[] => {
      return events.filter((e) => e.data.traceId === traceId);
    },
    [events],
  );

  // ==========================================================================
  // OTEL Spans
  // ==========================================================================

  const getSpansByTraceId = useCallback(
    (traceId: string): TimelineEvent[] => {
      return events.filter(
        (e) => e.type === "otel_span" && e.data.traceId === traceId,
      );
    },
    [events],
  );

  const getSpanHierarchy = useCallback(
    (traceId: string): SpanHierarchy => {
      const spans = getSpansByTraceId(traceId);

      // Find root (no parent)
      const root = spans.find((s) => !s.data.parentSpanId) || null;

      // Find direct children of root
      const children = root
        ? spans.filter((s) => s.data.parentSpanId === root.data.spanId)
        : [];

      // Calculate depth
      const calculateDepth = (
        spanId: string | undefined,
        currentDepth: number,
      ): number => {
        if (!spanId) return currentDepth;
        const childSpans = spans.filter((s) => s.data.parentSpanId === spanId);
        if (childSpans.length === 0) return currentDepth;
        return Math.max(
          ...childSpans.map((c) =>
            calculateDepth(c.data.spanId as string, currentDepth + 1),
          ),
        );
      };

      const depth = root ? calculateDepth(root.data.spanId as string, 1) : 0;

      return { root, children, depth };
    },
    [getSpansByTraceId],
  );

  const getSpanStats = useCallback(
    (traceId: string): SpanStats => {
      const spans = getSpansByTraceId(traceId);
      const durations = spans
        .map((s) => (s.data.duration as number) || 0)
        .filter((d) => d > 0);

      const totalDuration = durations.reduce((sum, d) => sum + d, 0);

      return {
        totalSpans: spans.length,
        totalDuration,
        averageDuration: spans.length > 0 ? totalDuration / spans.length : 0,
      };
    },
    [getSpansByTraceId],
  );

  const getSlowSpans = useCallback(
    (thresholdMs: number): TimelineEvent[] => {
      return events.filter(
        (e) =>
          e.type === "otel_span" &&
          typeof e.data.duration === "number" &&
          e.data.duration > thresholdMs,
      );
    },
    [events],
  );

  const getErrorSpans = useCallback((): TimelineEvent[] => {
    return events.filter(
      (e) => e.type === "otel_span" && e.data.status === "ERROR",
    );
  }, [events]);

  // ==========================================================================
  // LangGraph
  // ==========================================================================

  const getLangGraphNodeEvents = useCallback(
    (nodeId: string): TimelineEvent[] => {
      return events.filter(
        (e) => e.type === "langgraph_node" && e.data.nodeId === nodeId,
      );
    },
    [events],
  );

  const getLangGraphStateAtCurrentTime = useCallback((): Record<
    string,
    string
  > => {
    const nodeStates: Record<string, string> = {};
    const relevantEvents = events.filter(
      (e) => e.type === "langgraph_node" && e.timestamp <= currentTime,
    );

    // Group by nodeId and take the latest status for each
    for (const event of relevantEvents) {
      const nodeId = event.data.nodeId as string;
      const status = event.data.status as string;
      if (nodeId && status) {
        nodeStates[nodeId] = status;
      }
    }

    return nodeStates;
  }, [events, currentTime]);

  // ==========================================================================
  // Bookmarks
  // ==========================================================================

  const addBookmark = useCallback((label: string) => {
    const bookmark: TimelineBookmark = {
      id: generateId(),
      timestamp: currentTimeRef.current,
      label,
    };
    setBookmarks((prev) => [...prev, bookmark]);
  }, []);

  const removeBookmark = useCallback((id: string) => {
    setBookmarks((prev) => prev.filter((b) => b.id !== id));
  }, []);

  const jumpToBookmark = useCallback(
    (id: string) => {
      const bookmark = bookmarks.find((b) => b.id === id);
      if (bookmark) {
        setCurrentTimeState(bookmark.timestamp);
        setIsLiveMode(false);
      }
    },
    [bookmarks],
  );

  // ==========================================================================
  // Clear/Reset
  // ==========================================================================

  const clearEvents = useCallback(() => {
    setEvents([]);
    setCurrentTimeState(0);
  }, []);

  const clearEventsByType = useCallback((type: TimelineEventType) => {
    setEvents((prev) => prev.filter((e) => e.type !== type));
  }, []);

  const reset = useCallback(() => {
    setEvents([]);
    setCurrentTimeState(0);
    setIsPlaying(false);
    setIsLiveMode(true);
    setBookmarks([]);
    setTypeFilter(null);
    setTimeWindowState(null);
    setSelectedSpanId(null);
  }, []);

  return {
    // State
    events,
    currentTime,
    timeRange,
    isPlaying,
    isAtEnd,
    isLiveMode,
    playbackSpeed,
    bookmarks,
    sessionStartTime,
    timeWindow,
    selectedSpanId,

    // Event registration
    registerEvent,

    // Time navigation
    setCurrentTime,
    jumpToStart,
    jumpToEnd,
    stepForward,
    stepBackward,

    // Playback
    startPlayback,
    stopPlayback,
    setPlaybackSpeed,

    // Filtering
    getEventsAtCurrentTime,
    getEventsByType,
    getEventsInRange,
    getVisibleEvents,
    setTypeFilter,

    // Time window and span selection
    setTimeWindow,
    clearTimeWindow,
    getEventsInWindow,
    selectSpan,
    clearSpanSelection,
    getEventsInSelectedSpan,
    getActiveFilters,
    getFilteredEvents,

    // Correlation
    getEventsNear,
    getCorrelatedEvents,
    getPreviousEventOfType,
    getEventsByTraceId,

    // OTEL Spans
    getSpansByTraceId,
    getSpanHierarchy,
    getSpanStats,
    getSlowSpans,
    getErrorSpans,

    // LangGraph
    getLangGraphNodeEvents,
    getLangGraphStateAtCurrentTime,

    // Bookmarks
    addBookmark,
    removeBookmark,
    jumpToBookmark,

    // Clear/Reset
    clearEvents,
    clearEventsByType,
    reset,
  };
}

export default useDevToolsTimeline;
