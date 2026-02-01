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

import { Button } from "@/components/UI";

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
  if (confidence >= 0.9) return "text-success-10 dark:text-success-7";
  if (confidence >= 0.7) return "text-warning-9 dark:text-warning-9";
  return "text-neutral-10";
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
        "bg-primary-3 bg-primary-4",
        "text-primary-11 dark:text-primary-5",
        "hover:bg-primary-4 dark:hover:bg-primary-a6",
      );
    case "outline":
      return cn(
        "bg-transparent",
        "border border-neutral-5",
        "text-neutral-11",
        "hover:border-primary-7 dark:hover:border-primary-9",
        "hover:bg-primary-1 dark:hover:bg-primary-a3",
      );
    case "subtle":
      return cn("bg-neutral-2", "text-neutral-11", "hover:bg-neutral-3");
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
    <Button
      variant="primary"
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
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-7 focus-visible:ring-offset-2",
        "cursor-pointer",
        // Size styles
        sizeStyles.container,
        // Variant styles
        variant === "default" && "bg-primary",
        variant === "outline" && "border bg-transparent",
        variant === "subtle" && "bg-neutral-2",
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
    </Button>
  );
}

export default SuggestionChip;
