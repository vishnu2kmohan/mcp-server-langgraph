/**
 * TimelineBar Component
 *
 * Unified timeline scrubber for time-travel debugging across all DevTools tabs.
 * Provides playback controls, minimap visualization, and time navigation.
 *
 * Design System Compliance:
 * - Uses CVA for button variants
 * - Uses Motion.dev for playback button animation
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import React, { useState, useCallback, useMemo, useRef } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ChevronLeft,
  ChevronRight,
  Radio,
  Bookmark,
  Download,
  X,
} from "lucide-react";

import { cn } from "../../utils/cn";
import { useTimelineContext } from "./context/DevToolsTimelineProvider";
import { buttonVariants as motionButtonVariants } from "@/design-system/micro-interactions";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface TimelineBarProps {
  /** Show minimap visualization */
  showMinimap?: boolean;
  /** Show bookmark button */
  showBookmarkButton?: boolean;
  /** Show time range selector */
  showTimeRangeSelector?: boolean;
  /** Show export button */
  showExport?: boolean;
  /** Compact display mode */
  compact?: boolean;
  /** Export callback */
  onExport?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// Speed options for playback
const SPEED_OPTIONS = [
  { value: 0.5, label: "0.5x" },
  { value: 1, label: "1x" },
  { value: 2, label: "2x" },
  { value: 4, label: "4x" },
];

// Time range options
const TIME_RANGE_OPTIONS = [
  { value: "15m", label: "15 minutes" },
  { value: "1h", label: "1 hour" },
  { value: "24h", label: "24 hours" },
  { value: "7d", label: "7 days" },
];

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format milliseconds to human-readable time string.
 */
function formatTime(ms: number): string {
  if (ms < 0) return "0:00";

  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/**
 * Calculate event density for minimap.
 */
function calculateDensity(
  events: Array<{ timestamp: number }>,
  start: number,
  end: number,
  buckets: number = 50,
): number[] {
  if (events.length === 0 || end <= start) {
    return new Array(buckets).fill(0);
  }

  const density = new Array(buckets).fill(0);
  const bucketWidth = (end - start) / buckets;

  for (const event of events) {
    const bucketIndex = Math.min(
      Math.floor((event.timestamp - start) / bucketWidth),
      buckets - 1,
    );
    if (bucketIndex >= 0 && bucketIndex < buckets) {
      density[bucketIndex]++;
    }
  }

  // Normalize to 0-1 range
  const maxDensity = Math.max(...density, 1);
  return density.map((d) => d / maxDensity);
}

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Timeline button variants - matches ghost variant from Button component per STYLE.md
 */
// eslint-disable-next-line react-refresh/only-export-components
export const timelineButtonVariants = cva(
  [
    "inline-flex items-center justify-center rounded-md text-sm font-medium",
    "bg-transparent text-neutral-11",
    "transition-colors hover:text-neutral-12 hover:bg-neutral-2 active:bg-neutral-3",
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-6 focus-visible:ring-offset-2",
    "disabled:opacity-50 disabled:pointer-events-none",
  ],
  {
    variants: {
      size: {
        icon: "h-7 w-7",
        sm: "h-7 px-2 text-xs",
      },
    },
    defaultVariants: {
      size: "icon",
    },
  },
);

// =============================================================================
// Sub-Components
// =============================================================================

interface MinimapProps {
  events: Array<{ timestamp: number }>;
  bookmarks: Array<{ id: string; timestamp: number; label: string }>;
  timeRange: { start: number; end: number };
  currentTime: number;
  timeWindow: { start: number; end: number } | null;
  onTimeClick: (time: number) => void;
  onClearTimeWindow: () => void;
}

function TimelineMinimap({
  events,
  bookmarks,
  timeRange,
  currentTime,
  timeWindow,
  onTimeClick,
  onClearTimeWindow,
}: MinimapProps) {
  const minimapRef = useRef<HTMLDivElement>(null);
  const density = useMemo(
    () => calculateDensity(events, timeRange.start, timeRange.end),
    [events, timeRange.start, timeRange.end],
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!minimapRef.current) return;

      const rect = minimapRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = x / rect.width;
      const time =
        timeRange.start + percentage * (timeRange.end - timeRange.start);
      onTimeClick(time);
    },
    [timeRange, onTimeClick],
  );

  // Calculate cursor position
  const cursorPosition = useMemo(() => {
    if (timeRange.end === timeRange.start) return 0;
    return (
      ((currentTime - timeRange.start) / (timeRange.end - timeRange.start)) *
      100
    );
  }, [currentTime, timeRange]);

  // Calculate time window overlay position
  const windowOverlay = useMemo(() => {
    if (!timeWindow || timeRange.end === timeRange.start) return null;

    const left =
      ((timeWindow.start - timeRange.start) /
        (timeRange.end - timeRange.start)) *
      100;
    const right =
      ((timeWindow.end - timeRange.start) / (timeRange.end - timeRange.start)) *
      100;
    return { left: Math.max(0, left), width: Math.min(100, right) - left };
  }, [timeWindow, timeRange]);

  return (
    <div
      ref={minimapRef}
      data-testid="timeline-minimap"
      className="relative h-8 bg-neutral-2 rounded cursor-pointer"
      onClick={handleClick}
    >
      {/* Density bars */}
      <div className="absolute inset-0 flex items-end gap-px p-1">
        {density.map((d, i) => (
          <div
            key={i}
            data-density-bar
            className="flex-1 bg-primary-a7 rounded-t dynamic-height"
            style={
              { "--height": `${Math.max(d * 100, 2)}%` } as React.CSSProperties
            }
          />
        ))}
      </div>
      {/* Time window overlay */}
      {windowOverlay && (
        <div
          data-testid="time-window-overlay"
          className="absolute inset-y-0 bg-primary-a3 border-x border-primary-9"
          style={{
            left: `${windowOverlay.left}%`,
            width: `${windowOverlay.width}%`,
          }}
        >
          <Button
            variant="ghost"
            className="absolute -right-3 -top-2 h-4 w-4 rounded bg-neutral-1 border flex"
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onClearTimeWindow();
            }}
            aria-label="Clear time window"
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}
      {/* Bookmark indicators */}
      {bookmarks.map((bookmark) => {
        const position =
          ((bookmark.timestamp - timeRange.start) /
            (timeRange.end - timeRange.start)) *
          100;
        if (position < 0 || position > 100) return null;

        return (
          <div
            key={bookmark.id}
            data-testid="bookmark-indicator"
            className="absolute top-0 bottom-0 w-0.5 bg-warning-9"
            style={{ left: `${position}%` }}
            title={bookmark.label}
          />
        );
      })}
      {/* Current time cursor */}
      <div
        data-testid="minimap-cursor"
        className="absolute top-0 bottom-0 w-0.5 bg-neutral-2"
        style={{ left: `${cursorPosition}%` }}
      />
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function TimelineBar({
  showMinimap = false,
  showBookmarkButton = false,
  showTimeRangeSelector = false,
  showExport = false,
  compact = false,
  onExport,
  className,
}: TimelineBarProps): React.ReactElement {
  const timeline = useTimelineContext();
  const prefersReducedMotion = useReducedMotion();
  const [speedMenuOpen, setSpeedMenuOpen] = useState(false);
  const [timeRangeMenuOpen, setTimeRangeMenuOpen] = useState(false);
  const [selectedTimeRange, setSelectedTimeRange] = useState("15m");

  const hasEvents = timeline.events.length > 0;
  const isDisabled = !hasEvents;

  // Handlers
  const handlePlayPause = useCallback(() => {
    if (timeline.isPlaying) {
      timeline.stopPlayback();
    } else {
      timeline.startPlayback();
    }
  }, [timeline]);

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      timeline.setCurrentTime(Number(e.target.value));
    },
    [timeline],
  );

  const handleLiveToggle = useCallback(() => {
    if (!timeline.isLiveMode) {
      timeline.jumpToEnd();
    }
  }, [timeline]);

  const handleSpeedSelect = useCallback(
    (speed: number) => {
      timeline.setPlaybackSpeed(speed);
      setSpeedMenuOpen(false);
    },
    [timeline],
  );

  const handleTimeRangeSelect = useCallback(
    (range: string) => {
      setSelectedTimeRange(range);
      setTimeRangeMenuOpen(false);

      const now = Date.now();
      let windowStart: number;

      switch (range) {
        case "15m":
          windowStart = now - 15 * 60 * 1000;
          break;
        case "1h":
          windowStart = now - 60 * 60 * 1000;
          break;
        case "24h":
          windowStart = now - 24 * 60 * 60 * 1000;
          break;
        case "7d":
          windowStart = now - 7 * 24 * 60 * 60 * 1000;
          break;
        default:
          windowStart = now - 15 * 60 * 1000;
      }

      timeline.setTimeWindow(windowStart, now);
    },
    [timeline],
  );

  const handleAddBookmark = useCallback(() => {
    timeline.addBookmark(`Bookmark ${timeline.bookmarks.length + 1}`);
  }, [timeline]);

  const handleMinimapClick = useCallback(
    (time: number) => {
      timeline.setCurrentTime(time);
    },
    [timeline],
  );

  // Computed values
  const currentTimeFormatted = formatTime(
    timeline.currentTime - timeline.timeRange.start,
  );
  const totalTimeFormatted = formatTime(
    timeline.timeRange.end - timeline.timeRange.start,
  );
  const speedLabel = `${timeline.playbackSpeed}x`;

  return (
    <div
      data-testid="timeline-bar"
      className={cn(
        "flex flex-col gap-2 p-2 bg-neutral-1 border-b border-neutral-5",
        compact && "compact py-1",
        className,
      )}
    >
      {/* Main controls row */}
      <div className="flex items-center gap-2">
        {/* Playback controls - use ghost variant for minimal visual weight per STYLE.md */}
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={timeline.jumpToStart}
            disabled={isDisabled}
            aria-label="Jump to start"
          >
            <SkipBack className="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={timeline.stepBackward}
            disabled={isDisabled}
            aria-label="Step backward"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <motion.button
            type="button"
            className={timelineButtonVariants({ size: "icon" })}
            onClick={handlePlayPause}
            disabled={isDisabled}
            aria-label={timeline.isPlaying ? "Pause" : "Play"}
            variants={prefersReducedMotion ? undefined : motionButtonVariants}
            initial="rest"
            whileHover={isDisabled ? undefined : "hover"}
            whileTap={isDisabled ? undefined : "pressed"}
          >
            {timeline.isPlaying ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </motion.button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={timeline.stepForward}
            disabled={isDisabled}
            aria-label="Step forward"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={timeline.jumpToEnd}
            disabled={isDisabled}
            aria-label="Jump to end"
          >
            <SkipForward className="h-4 w-4" />
          </Button>
        </div>

        {/* Speed selector */}
        <div className="relative">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setSpeedMenuOpen(!speedMenuOpen)}
            aria-label={speedLabel}
          >
            {speedLabel}
          </Button>
          {speedMenuOpen && (
            <div className="absolute top-full left-0 mt-1 bg-neutral-1 border border-neutral-6 rounded shadow-lg z-dropdown">
              {SPEED_OPTIONS.map((option) => (
                <Button
                  variant="ghost"
                  size="sm"
                  className="block w-full px-3 py-1 text-left text-sm hover:bg-neutral-3"
                  key={option.value}
                  type="button"
                  role="option"
                  aria-label={option.label}
                  onClick={() => handleSpeedSelect(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          )}
        </div>

        {/* Scrubber/Slider */}
        <div className="flex-1">
          <input
            type="range"
            role="slider"
            value={timeline.currentTime}
            min={timeline.timeRange.start}
            max={timeline.timeRange.end}
            step={10}
            onChange={handleSliderChange}
            disabled={isDisabled}
            aria-label="Timeline position"
            className="w-full h-2 bg-neutral-3 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
          />
        </div>

        {/* Time display */}
        <div className="flex items-center gap-1 text-xs text-neutral-10">
          <span data-testid="current-time-display">{currentTimeFormatted}</span>
          <span>/</span>
          <span data-testid="total-time-display">{totalTimeFormatted}</span>
        </div>

        {/* Live mode toggle */}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={cn("gap-1", timeline.isLiveMode && "text-error-9")}
          onClick={handleLiveToggle}
          data-active={timeline.isLiveMode}
          aria-label="Live"
        >
          <Radio className="h-3 w-3" />
          Live
        </Button>

        {/* Time range selector */}
        {showTimeRangeSelector && (
          <div className="relative">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setTimeRangeMenuOpen(!timeRangeMenuOpen)}
              aria-label={selectedTimeRange}
            >
              {selectedTimeRange}
            </Button>
            {timeRangeMenuOpen && (
              <div className="absolute top-full right-0 mt-1 bg-neutral-1 border border-neutral-6 rounded shadow-lg z-dropdown">
                {TIME_RANGE_OPTIONS.map((option) => (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="block w-full px-3 py-1 text-left text-sm hover:bg-neutral-3 whitespace-nowrap"
                    key={option.value}
                    type="button"
                    role="option"
                    aria-label={option.label}
                    onClick={() => handleTimeRangeSelect(option.value)}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Bookmark button */}
        {showBookmarkButton && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleAddBookmark}
            disabled={isDisabled}
            aria-label="Add bookmark"
          >
            <Bookmark className="h-4 w-4" />
          </Button>
        )}

        {/* Export button */}
        {showExport && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onExport}
            aria-label="Export"
          >
            <Download className="h-4 w-4" />
          </Button>
        )}
      </div>
      {/* Minimap row */}
      {showMinimap && !compact && hasEvents && (
        <TimelineMinimap
          events={timeline.events}
          bookmarks={timeline.bookmarks}
          timeRange={timeline.timeRange}
          currentTime={timeline.currentTime}
          timeWindow={timeline.timeWindow}
          onTimeClick={handleMinimapClick}
          onClearTimeWindow={timeline.clearTimeWindow}
        />
      )}
    </div>
  );
}

export default TimelineBar;
