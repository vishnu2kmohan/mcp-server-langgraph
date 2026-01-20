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
export { Button, buttonVariants } from "./Button";
export type { ButtonProps, ButtonVariant, ButtonSize } from "./Button";

// Badge - Status indicators and labels
export { Badge, badgeVariants } from "./Badge";
export type { BadgeProps, BadgeVariant, BadgeSize } from "./Badge";

// Input - Text input field
export { Input, inputVariants } from "./Input";
export type { InputProps, InputVariant, InputSize } from "./Input";

// Select - Dropdown select field
export { Select, selectVariants } from "./Select";
export type {
  SelectProps,
  SelectOption,
  SelectVariant,
  SelectSize,
} from "./Select";

// Textarea - Multi-line text input
export { Textarea, textareaVariants } from "./Textarea";
export type {
  TextareaProps,
  TextareaVariant,
  TextareaSize,
  TextareaResize,
} from "./Textarea";

// Toggle - Switch/toggle control
export { Toggle, toggleVariants } from "./Toggle";
export type { ToggleProps, ToggleSize } from "./Toggle";

// Checkbox - Checkbox input with label
export { Checkbox, checkboxVariants } from "./Checkbox";
export type { CheckboxProps, CheckboxSize } from "./Checkbox";

// RadioGroup - Radio button group (variants: default, card, rating)
export { RadioGroup, Radio, radioVariants } from "./RadioGroup";
export type {
  RadioGroupProps,
  RadioProps,
  RadioSize,
  RadioGroupVariant,
} from "./RadioGroup";

// Slider - Range input control
export { Slider, sliderVariants } from "./Slider";
export type { SliderProps, SliderSize, SliderMark } from "./Slider";

// FileInput - File upload control
export { FileInput, fileInputVariants } from "./FileInput";
export type {
  FileInputProps,
  FileInputSize,
  FileInputVariant,
} from "./FileInput";

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
export {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
  cardVariants,
} from "./Card";
export type {
  CardProps,
  CardVariant,
  CardPadding,
  CardHeaderProps,
  CardTitleProps,
  CardContentProps,
  CardFooterProps,
} from "./Card";

// SelectionCard - Consistent selection card for wizards and option lists
export { SelectionCard } from "./SelectionCard";
export type { SelectionCardProps } from "./SelectionCard";

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
export {
  Skeleton,
  SkeletonCard,
  SkeletonText,
  SkeletonList,
  skeletonVariants,
} from "./Skeleton";
export type {
  SkeletonProps,
  SkeletonCardProps,
  SkeletonTextProps,
  SkeletonListProps,
} from "./Skeleton";

// Error State - Standardized error display
export { ErrorState } from "./ErrorState";
export type { ErrorStateProps, ErrorStateVariant } from "./ErrorState";

// Dialog - Reusable modal dialog
export { Dialog, dialogVariants } from "./Dialog";
export type { DialogProps, DialogSize } from "./Dialog";

// Confirm Dialog - Styled confirmation dialog (replaces native confirm())
export { ConfirmDialog } from "./ConfirmDialog";
export type { ConfirmDialogProps } from "./ConfirmDialog";

// NOTE: OfflineBanner moved to components/OfflineBanner for feature-rich version
// Legacy simple banner in UI/OfflineBanner.tsx is deprecated

// Tier Usage Bar - Tier-based usage indicator
export { TierUsageBar } from "./TierUsageBar";
export type { TierUsageBarProps } from "./TierUsageBar";

// Upgrade Prompt - Tier upgrade CTA
export { UpgradePrompt } from "./UpgradePrompt";
export type { UpgradePromptProps } from "./UpgradePrompt";

// ContextMenu - Right-click context menu
export { ContextMenu } from "./ContextMenu";
export type { ContextMenuProps, ContextMenuItem } from "./ContextMenu";

// Tooltip - Hover tooltip
export { Tooltip } from "./Tooltip";
export type { TooltipProps } from "./Tooltip";

// InlineEdit - Inline text editing
export { InlineEdit } from "./InlineEdit";
export type { InlineEditProps } from "./InlineEdit";

// =============================================================================
// Data Display Components
// =============================================================================

// Table - Data table with compound component pattern
export {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableHeaderCell,
  TableCell,
} from "./Table";
export type {
  TableProps,
  TableHeadProps,
  TableBodyProps,
  TableRowProps,
  TableHeaderCellProps,
  TableCellProps,
} from "./Table";

// SegmentedControl - Toggle group for view modes and mutually exclusive options
export { SegmentedControl, SegmentedControlItem } from "./SegmentedControl";
export type {
  SegmentedControlProps,
  SegmentedControlItemProps,
  SegmentedControlSize,
} from "./SegmentedControl";
