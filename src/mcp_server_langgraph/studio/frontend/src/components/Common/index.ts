/**
 * Common Components
 *
 * Shared UI components for the Studio frontend.
 */

export { ConfirmationDialog } from "./ConfirmationDialog";
export type {
  ConfirmationDialogProps,
  DialogSeverity,
} from "./ConfirmationDialog";

export { ProgressIndicator } from "./ProgressIndicator";
export type {
  ProgressIndicatorProps,
  ProgressSize,
  ProgressColor,
} from "./ProgressIndicator";

export { ShortcutsPanel } from "./ShortcutsPanel";
export type { ShortcutsPanelProps, ShortcutDefinition } from "./ShortcutsPanel";

export { StepProgress } from "./StepProgress";
export type {
  StepProgressProps,
  Step,
  StepStatus,
  StepSize,
  StepOrientation,
} from "./StepProgress";

export { ThemeToggle } from "./ThemeToggle";
export type { ThemeToggleProps, Theme } from "./ThemeToggle";
