/**
 * Numeric Utilities for NaN/Infinity Safety
 *
 * Provides safe numeric operations that handle edge cases like:
 * - NaN (Not a Number)
 * - Infinity/-Infinity
 * - Division by zero
 *
 * These utilities mirror the Python `mcp_server_langgraph.core.numeric` module
 * for consistent defense-in-depth handling across the full stack.
 *
 * @example
 * safeFloat(NaN) // Returns 0.0
 * safeAverage([1, 2, NaN, 4]) // Returns 2.333... (skips NaN)
 * safeDivide(10, 0) // Returns 0.0 (avoids Infinity)
 */

/**
 * Convert a potentially unsafe numeric value to a safe float.
 *
 * Handles NaN, Infinity, and -Infinity by replacing them with a default value.
 *
 * @param value - The value to convert
 * @param defaultValue - Value to return if input is NaN/Infinity (default: 0.0)
 * @returns A safe finite number
 */
export function safeFloat(
  value: number | null | undefined,
  defaultValue: number = 0.0,
): number {
  if (value === null || value === undefined) {
    return defaultValue;
  }
  if (!Number.isFinite(value)) {
    return defaultValue;
  }
  return value;
}

/**
 * Calculate the average of an array of numbers safely.
 *
 * - Returns 0.0 for empty arrays (avoids division by zero)
 * - Filters out NaN/Infinity values before averaging
 * - Never returns NaN or Infinity
 *
 * @param values - Array of numbers to average
 * @returns The safe average, or 0.0 if no valid values
 */
export function safeAverage(values: number[]): number {
  if (!values || values.length === 0) {
    return 0.0;
  }

  // Filter to only finite values
  const finiteValues = values.filter(Number.isFinite);
  if (finiteValues.length === 0) {
    return 0.0;
  }

  const sum = finiteValues.reduce((acc, val) => acc + val, 0);
  return sum / finiteValues.length;
}

/**
 * Safely divide two numbers.
 *
 * Returns 0.0 when:
 * - Divisor is zero (avoids Infinity)
 * - Either operand is NaN or Infinity
 *
 * @param numerator - The dividend
 * @param denominator - The divisor
 * @param defaultValue - Value to return on error (default: 0.0)
 * @returns The quotient, or defaultValue if division would produce NaN/Infinity
 */
export function safeDivide(
  numerator: number,
  denominator: number,
  defaultValue: number = 0.0,
): number {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator)) {
    return defaultValue;
  }
  if (denominator === 0) {
    return defaultValue;
  }
  const result = numerator / denominator;
  return Number.isFinite(result) ? result : defaultValue;
}

/**
 * Safely round a number to specified decimal places.
 *
 * Handles NaN/Infinity by returning the default value.
 *
 * @param value - The value to round
 * @param decimals - Number of decimal places (default: 2)
 * @param defaultValue - Value to return if input is invalid (default: 0.0)
 * @returns The rounded value, or defaultValue if input is NaN/Infinity
 */
export function safeRound(
  value: number,
  decimals: number = 2,
  defaultValue: number = 0.0,
): number {
  if (!Number.isFinite(value)) {
    return defaultValue;
  }
  const factor = Math.pow(10, decimals);
  return Math.round(value * factor) / factor;
}

/**
 * Safely sum an array of numbers.
 *
 * Filters out NaN/Infinity values before summing.
 *
 * @param values - Array of numbers to sum
 * @returns The safe sum (0.0 if no valid values)
 */
export function safeSum(values: number[]): number {
  if (!values || values.length === 0) {
    return 0.0;
  }

  const finiteValues = values.filter(Number.isFinite);
  return finiteValues.reduce((acc, val) => acc + val, 0);
}

/**
 * Options for safePercentage function.
 */
export interface SafePercentageOptions {
  /** Value to return if calculation fails (default: 0.0) */
  defaultValue?: number;
  /** Whether to clamp to min/max bounds (default: true) */
  clamp?: boolean;
  /** Minimum value when clamping (default: 0.0) */
  minVal?: number;
  /** Maximum value when clamping (default: 100.0) */
  maxVal?: number;
  /** Number of decimal places to round to (default: no rounding) */
  decimals?: number;
}

/**
 * Safely calculate a percentage with NaN/Infinity/zero protection.
 *
 * Computes (numerator / denominator) * 100, with protection against:
 * - Division by zero
 * - NaN/Infinity inputs
 * - Out-of-bounds results (optionally clamped to 0-100 or custom range)
 *
 * This is the TypeScript equivalent of Python's safe_percentage from
 * mcp_server_langgraph.core.numeric for full-stack consistency.
 *
 * @param numerator - The numerator
 * @param denominator - The denominator
 * @param options - Configuration options
 * @returns Percentage value, optionally clamped and rounded
 *
 * @example
 * safePercentage(50, 100) // 50.0
 * safePercentage(150, 100) // 100.0 (clamped)
 * safePercentage(150, 100, { clamp: false }) // 150.0
 * safePercentage(1, 3, { decimals: 2 }) // 33.33
 */
export function safePercentage(
  numerator: number,
  denominator: number,
  options: SafePercentageOptions = {},
): number {
  const {
    defaultValue = 0.0,
    clamp = true,
    minVal = 0.0,
    maxVal = 100.0,
    decimals,
  } = options;

  // Use safeDivide for the core calculation
  const ratio = safeDivide(numerator, denominator, NaN);

  // Check if division failed
  if (!Number.isFinite(ratio)) {
    return defaultValue;
  }

  // Calculate percentage
  let percentage = ratio * 100.0;

  // Apply clamping if enabled
  if (clamp) {
    percentage = Math.max(minVal, Math.min(maxVal, percentage));
  }

  // Apply rounding if specified
  if (decimals !== undefined) {
    const factor = Math.pow(10, decimals);
    percentage = Math.round(percentage * factor) / factor;
  }

  return percentage;
}

/**
 * Format a potentially unsafe number for display.
 *
 * Returns a dash or custom placeholder for NaN/Infinity values.
 *
 * @param value - The value to format
 * @param placeholder - String to show for invalid values (default: "-")
 * @param decimals - Decimal places for valid numbers (default: 2)
 * @returns Formatted string representation
 */
export function formatSafeNumber(
  value: number | null | undefined,
  placeholder: string = "-",
  decimals: number = 2,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return placeholder;
  }
  return value.toFixed(decimals);
}
