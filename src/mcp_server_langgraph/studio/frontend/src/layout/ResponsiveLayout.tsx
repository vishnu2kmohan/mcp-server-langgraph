/**
 * ResponsiveLayout Component
 *
 * Wrapper component that detects screen breakpoints and provides
 * responsive layout classes for the StudioShell.
 *
 * Breakpoints:
 * - xl (>= 1440px): Full 4-column layout
 * - lg (1024-1439px): SessionNav collapsible
 * - md (768-1023px): Toggle Conversation/Canvas
 * - sm (< 768px): Mobile drawer navigation
 *
 * Features:
 * - Breakpoint detection via matchMedia
 * - Layout class application
 * - Breakpoint change callback
 * - Custom hook for breakpoint access
 */
/* eslint-disable react-refresh/only-export-components -- Exports useBreakpoint hook alongside component */
import { useState, useEffect, type ReactNode } from "react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type Breakpoint = "sm" | "md" | "lg" | "xl";

export interface ResponsiveLayoutProps {
  /** Child components to render */
  children: ReactNode;
  /** Callback when breakpoint changes */
  onBreakpointChange?: (breakpoint: Breakpoint) => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const BREAKPOINTS = {
  xl: 1440, // Full 4-column layout
  lg: 1024, // SessionNav collapsible
  md: 768, // Toggle Conversation/Canvas
  sm: 0, // Mobile drawer navigation
} as const;

const LAYOUT_CLASSES: Record<Breakpoint, string> = {
  xl: "layout-full",
  lg: "layout-collapsible",
  md: "layout-toggle",
  sm: "layout-mobile",
};

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to detect current breakpoint
 */
export function useBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>(() =>
    getBreakpoint(typeof window !== "undefined" ? window.innerWidth : 1440),
  );

  useEffect(() => {
    // Media query listeners
    const xlQuery = window.matchMedia(`(min-width: ${BREAKPOINTS.xl}px)`);
    const lgQuery = window.matchMedia(`(min-width: ${BREAKPOINTS.lg}px)`);
    const mdQuery = window.matchMedia(`(min-width: ${BREAKPOINTS.md}px)`);

    const updateBreakpoint = () => {
      const width = window.innerWidth;
      setBreakpoint(getBreakpoint(width));
    };

    // Add listeners
    xlQuery.addEventListener?.("change", updateBreakpoint);
    lgQuery.addEventListener?.("change", updateBreakpoint);
    mdQuery.addEventListener?.("change", updateBreakpoint);

    // Initial check
    updateBreakpoint();

    // Cleanup
    return () => {
      xlQuery.removeEventListener?.("change", updateBreakpoint);
      lgQuery.removeEventListener?.("change", updateBreakpoint);
      mdQuery.removeEventListener?.("change", updateBreakpoint);
    };
  }, []);

  return breakpoint;
}

/**
 * Get breakpoint from width
 */
function getBreakpoint(width: number): Breakpoint {
  if (width >= BREAKPOINTS.xl) return "xl";
  if (width >= BREAKPOINTS.lg) return "lg";
  if (width >= BREAKPOINTS.md) return "md";
  return "sm";
}

// =============================================================================
// Component
// =============================================================================

export function ResponsiveLayout({
  children,
  onBreakpointChange,
  className,
}: ResponsiveLayoutProps) {
  const breakpoint = useBreakpoint();

  // Notify parent of breakpoint changes
  useEffect(() => {
    onBreakpointChange?.(breakpoint);
  }, [breakpoint, onBreakpointChange]);

  return (
    <div
      data-testid="responsive-layout"
      data-breakpoint={breakpoint}
      className={cn(LAYOUT_CLASSES[breakpoint], className)}
    >
      {children}
    </div>
  );
}
