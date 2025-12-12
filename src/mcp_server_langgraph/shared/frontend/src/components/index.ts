/**
 * Shared Components
 *
 * Reusable UI components for Builder and Playground.
 */

export { PrivacySettings, type PrivacySettingsProps, type PrivacyState } from './Privacy';

export {
  Tooltip,
  TooltipProvider,
  TooltipTrigger,
  TooltipContent,
  type TooltipProps,
  type TooltipProviderProps,
  type TooltipTriggerProps,
  type TooltipContentProps,
} from './Tooltip';

export {
  ErrorRecovery,
  classifyError,
  getRecoverySuggestions,
  type ErrorRecoveryProps,
  type ErrorType,
} from './ErrorRecovery';

export {
  FeatureHint,
  useFeatureDiscovery,
  type FeatureHintProps,
  type HintConfig,
  type UseFeatureDiscoveryResult,
} from './FeatureHint';

export {
  OnboardingProgress,
  useOnboarding,
  type OnboardingProgressProps,
  type OnboardingStep,
  type UseOnboardingResult,
} from './OnboardingProgress';

export {
  GuidedTour,
  type GuidedTourProps,
  type TourStep,
} from './GuidedTour';

export {
  HelpPanel,
  type HelpPanelProps,
  type HelpSection,
  type HelpArticle,
  type KeyboardShortcut,
} from './HelpPanel';
