/**
 * UI Components
 *
 * Reusable UI components for the frontend application.
 * Barrel file for clean imports: import { Component } from '../components/UI';
 */

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
