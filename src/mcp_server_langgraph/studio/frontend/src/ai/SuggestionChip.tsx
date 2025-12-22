/**
 * SuggestionChip Component
 *
 * Phase 4: AI-Native Features
 * An atomic component for displaying individual AI suggestions
 * as interactive chip elements.
 *
 * Features:
 * - Display suggestion text with optional icon
 * - Click handler for selection
 * - Keyboard accessibility (Enter/Space to select)
 * - Visual states (default, hover, active, disabled)
 * - Confidence indicator
 * - Multiple variants (default, outline, subtle)
 * - Multiple sizes (sm, md, lg)
 */

import { Sparkles, Lightbulb, Zap, MessageCircle, Loader2 } from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type ChipIcon = "sparkles" | "lightbulb" | "zap" | "message-circle";
export type ChipVariant = "default" | "outline" | "subtle";
export type ChipSize = "sm" | "md" | "lg";

export interface SuggestionChipData {
  id?: string;
  text: string;
}

export interface SuggestionChipProps {
  /** The suggestion text to display */
  text: string;
  /** Optional unique identifier */
  id?: string;
  /** Click handler */
  onClick: (data: SuggestionChipData) => void;
  /** Optional icon to display */
  icon?: ChipIcon;
  /** Visual variant */
  variant?: ChipVariant;
  /** Size of the chip */
  size?: ChipSize;
  /** Confidence score (0-1) to display */
  confidence?: number;
  /** Whether the chip is disabled */
  disabled?: boolean;
  /** Whether the chip is in loading state */
  isLoading?: boolean;
  /** Maximum text length before truncation */
  maxLength?: number;
  /** Additional CSS classes */
  className?: string;
  /** Accessible label override */
  ariaLabel?: string;
}

// =============================================================================
// Icon Mapping
// =============================================================================

function getIcon(icon: ChipIcon, size: number) {
  switch (icon) {
    case "sparkles":
      return <Sparkles size={size} />;
    case "lightbulb":
      return <Lightbulb size={size} />;
    case "zap":
      return <Zap size={size} />;
    case "message-circle":
      return <MessageCircle size={size} />;
    default:
      return <Sparkles size={size} />;
  }
}

// =============================================================================
// Confidence Color Mapping
// =============================================================================

function getConfidenceClass(confidence: number): string {
  if (confidence >= 0.9) return "text-green-600 dark:text-green-400";
  if (confidence >= 0.7) return "text-yellow-600 dark:text-yellow-400";
  return "text-gray-500 dark:text-gray-400";
}

function getConfidenceTestClass(confidence: number): string {
  if (confidence >= 0.9) return "text-green";
  if (confidence >= 0.7) return "text-yellow";
  return "text-gray";
}

// =============================================================================
// Variant Styles
// =============================================================================

function getVariantClasses(variant: ChipVariant): string {
  switch (variant) {
    case "default":
      return cn(
        "bg-primary-100 dark:bg-primary-900/30",
        "text-primary-700 dark:text-primary-300",
        "hover:bg-primary-200 dark:hover:bg-primary-800/50",
      );
    case "outline":
      return cn(
        "bg-transparent",
        "border border-gray-300 dark:border-gray-600",
        "text-gray-700 dark:text-gray-300",
        "hover:border-primary-400 dark:hover:border-primary-500",
        "hover:bg-primary-50 dark:hover:bg-primary-900/20",
      );
    case "subtle":
      return cn(
        "bg-gray-100 dark:bg-gray-800",
        "text-gray-700 dark:text-gray-300",
        "hover:bg-gray-200 dark:hover:bg-gray-700",
      );
    default:
      return "";
  }
}

// =============================================================================
// Size Styles
// =============================================================================

function getSizeClasses(size: ChipSize): { container: string; icon: number } {
  switch (size) {
    case "sm":
      return {
        container: "px-2 py-1 text-xs gap-1.5",
        icon: 12,
      };
    case "lg":
      return {
        container: "px-4 py-2 text-base gap-2.5",
        icon: 18,
      };
    case "md":
    default:
      return {
        container: "px-3 py-1.5 text-sm gap-2",
        icon: 14,
      };
  }
}

// =============================================================================
// Component
// =============================================================================

export function SuggestionChip({
  text,
  id,
  onClick,
  icon,
  variant = "default",
  size = "md",
  confidence,
  disabled = false,
  isLoading = false,
  maxLength,
  className,
  ariaLabel,
}: SuggestionChipProps) {
  const sizeStyles = getSizeClasses(size);
  const isDisabled = disabled || isLoading;

  // Truncate text if maxLength is specified
  const displayText =
    maxLength && text.length > maxLength
      ? `${text.slice(0, maxLength)}...`
      : text;

  const handleClick = () => {
    if (!isDisabled) {
      onClick({ id, text });
    }
  };

  return (
    <button
      type="button"
      id={id}
      data-testid="suggestion-chip"
      onClick={handleClick}
      disabled={isDisabled}
      tabIndex={isDisabled ? -1 : 0}
      aria-label={ariaLabel || text}
      className={cn(
        // Base styles
        "inline-flex items-center justify-center",
        "rounded-full",
        "font-medium",
        "transition-all duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
        "cursor-pointer",
        // Size styles
        sizeStyles.container,
        // Variant styles
        variant === "default" && "bg-primary",
        variant === "outline" && "border bg-transparent",
        variant === "subtle" && "bg-gray-100",
        getVariantClasses(variant),
        // Disabled styles
        isDisabled && "opacity-50 cursor-not-allowed",
        // Custom classes
        className,
      )}
    >
      {/* Loading spinner */}
      {isLoading && (
        <Loader2
          data-testid="loading-spinner"
          size={sizeStyles.icon}
          className="animate-spin"
        />
      )}

      {/* Icon */}
      {icon && !isLoading && (
        <span data-testid="chip-icon">{getIcon(icon, sizeStyles.icon)}</span>
      )}

      {/* Text */}
      <span className="truncate">{displayText}</span>

      {/* Confidence badge */}
      {confidence !== undefined && (
        <span
          data-testid="confidence-badge"
          className={cn(
            "text-xs font-medium",
            getConfidenceClass(confidence),
            getConfidenceTestClass(confidence),
          )}
        >
          {Math.round(confidence * 100)}%
        </span>
      )}
    </button>
  );
}

export default SuggestionChip;
