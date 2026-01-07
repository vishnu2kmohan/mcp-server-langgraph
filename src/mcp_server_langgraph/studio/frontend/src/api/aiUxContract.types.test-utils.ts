/**
 * Type Aliases for AI UX Contract Tests
 *
 * Generated type aliases for readability in test files.
 */

import type { components } from "../types/generated-api";

// =============================================================================
// Core AI UX Type Aliases
// =============================================================================

export type NudgeRecommendRequest =
  components["schemas"]["NudgeRecommendRequest"];
export type NudgeRecommendResponse =
  components["schemas"]["NudgeRecommendResponse"];
export type NudgeContext = components["schemas"]["NudgeContext"];
export type NudgeHistoryItem = components["schemas"]["NudgeHistoryItem"];

export type OnboardingPersonalizeRequest =
  components["schemas"]["OnboardingPersonalizeRequest"];
export type OnboardingPersonalizeResponse =
  components["schemas"]["OnboardingPersonalizeResponse"];
export type SignupContext = components["schemas"]["SignupContext"];

export type PersonaAnalyzeRequest =
  components["schemas"]["PersonaAnalyzeRequest"];
export type PersonaAnalyzeResponse =
  components["schemas"]["PersonaAnalyzeResponse"];

// =============================================================================
// ADR-0091 Phase 9: Aligned Schema Type Aliases
// =============================================================================

export type DisclosureAnalyzeRequest =
  components["schemas"]["DisclosureAnalyzeRequest"];
export type DisclosureAnalyzeResponse =
  components["schemas"]["DisclosureAnalyzeResponse"];
export type EmptyStateSuggestionsRequest =
  components["schemas"]["EmptyStateSuggestionsRequest"];
export type EmptyStateSuggestionsResponse =
  components["schemas"]["EmptyStateSuggestionsResponse"];
export type ErrorAnalyzeRequest = components["schemas"]["ErrorAnalyzeRequest"];
export type ErrorAnalyzeResponse =
  components["schemas"]["ErrorAnalyzeResponse"];
export type MetricsInsightsResponse =
  components["schemas"]["MetricsInsightsResponse"];
