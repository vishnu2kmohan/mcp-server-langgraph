/**
 * UI Components
 *
 * Reusable UI components for the frontend application.
 * Barrel file for clean imports: import { Component } from '../components/UI';
 */

// =============================================================================
// Primitive Components (Design System Foundation)
// =============================================================================

// Button - Primary interactive element
export { Button } from "./Button";
export type { ButtonProps, ButtonVariant, ButtonSize } from "./Button";

// Badge - Status indicators and labels
export { Badge } from "./Badge";
export type { BadgeProps, BadgeVariant, BadgeSize } from "./Badge";

// StatusBadge - Semantic status badges with design system colors
export { StatusBadge } from "./StatusBadge";
export type { StatusBadgeProps, StatusBadgeSize } from "./StatusBadge";

// ConfidenceIndicator - AI confidence score display
export { ConfidenceIndicator } from "./ConfidenceIndicator";
export type {
  ConfidenceIndicatorProps,
  ConfidenceIndicatorSize,
} from "./ConfidenceIndicator";

// RiskBadge - Risk level display with semantic colors
export { RiskBadge } from "./RiskBadge";
export type { RiskBadgeProps, RiskBadgeSize } from "./RiskBadge";

// Card - Content container with variants
export { Card, CardHeader, CardTitle, CardContent, CardFooter } from "./Card";
export type {
  CardProps,
  CardVariant,
  CardPadding,
  CardHeaderProps,
  CardTitleProps,
  CardContentProps,
  CardFooterProps,
} from "./Card";

// =============================================================================
// Composite Components
// =============================================================================

// Pagination - Page-based and cursor-based navigation
export { PagePagination } from "./Pagination";
export type { PagePaginationProps } from "./Pagination";
export { CursorPagination } from "./CursorPagination";
export type { CursorPaginationProps } from "./CursorPagination";

// Search - Debounced search input
export { SearchInput } from "./SearchInput";
export type { SearchInputProps } from "./SearchInput";

// Sort - Sort field and order dropdown
export { SortDropdown } from "./SortDropdown";
export type { SortDropdownProps, SortOption, SortOrder } from "./SortDropdown";

// Status Filter - Status dropdown filter
export { StatusFilter } from "./StatusFilter";
export type { StatusFilterProps, StatusOption } from "./StatusFilter";

// Filter Chips - Clickable filter chips (replaces dropdown for enum filtering)
export { FilterChips } from "./FilterChips";
export type { FilterChipsProps, FilterOption } from "./FilterChips";

// Skeleton - Loading placeholders
export { Skeleton, SkeletonCard, SkeletonText, SkeletonList } from "./Skeleton";

// Error State - Standardized error display
export { ErrorState } from "./ErrorState";
export type { ErrorStateProps, ErrorStateVariant } from "./ErrorState";

// Dialog - Reusable modal dialog
export { Dialog } from "./Dialog";
export type { DialogProps, DialogSize } from "./Dialog";

// Confirm Dialog - Styled confirmation dialog (replaces native confirm())
export { ConfirmDialog } from "./ConfirmDialog";
export type { ConfirmDialogProps } from "./ConfirmDialog";

// Offline Banner - PWA offline indicator
export { OfflineBanner } from "./OfflineBanner";

// Tier Usage Bar - Tier-based usage indicator
export { TierUsageBar } from "./TierUsageBar";
export type { TierUsageBarProps } from "./TierUsageBar";

// Upgrade Prompt - Tier upgrade CTA
export { UpgradePrompt } from "./UpgradePrompt";
export type { UpgradePromptProps } from "./UpgradePrompt";
