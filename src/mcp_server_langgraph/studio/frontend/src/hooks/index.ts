/**
 * Hooks Index
 *
 * Central export for all custom React hooks in the application.
 * Organized by category for easy discovery and import.
 */

// =============================================================================
// WebSocket Hooks (Real-time Communication)
// =============================================================================

export {
  useRealtimeSync,
  type UseRealtimeSyncOptions,
  type UseRealtimeSyncReturn,
  type WebSocketConnectionStatus,
} from "./useRealtimeSync";

export { useMCPWebSocket } from "./useMCPWebSocket";

export {
  useMCPAggregatedUpdates,
  type UseMCPAggregatedUpdatesOptions,
  type UseMCPAggregatedUpdatesReturn,
} from "./useMCPAggregatedUpdates";

export {
  useMCPTaskWebSocket,
  type MCPTask,
  type MCPTaskStatus,
  type UseMCPTaskWebSocketOptions,
  type UseMCPTaskWebSocketReturn,
} from "./useMCPTaskWebSocket";

export {
  useAuditWebSocket,
  type AuditEvent,
  type AuditFilter,
  type UseAuditWebSocketOptions,
  type UseAuditWebSocketReturn,
} from "./useAuditWebSocket";

export {
  useConnectionHealthWebSocket,
  type ConnectionHealth,
  type ConnectionStatus,
  type ConnectionSummary,
  type UseConnectionHealthWebSocketOptions,
  type UseConnectionHealthWebSocketReturn,
} from "./useConnectionHealthWebSocket";

export { useNotificationWebSocket } from "./useNotificationWebSocket";

export { useTraceWebSocket } from "./useTraceWebSocket";

export {
  useAlertWebSocket,
  type UseAlertWebSocketOptions,
  type UseAlertWebSocketReturn,
} from "./useAlertWebSocket";

// ADR-0068 New WebSocket Hooks (Phase 4 Standardization)
export {
  useConnectionsRealtimeWebSocket,
  type UseConnectionsRealtimeWebSocketOptions,
  type UseConnectionsRealtimeWebSocketReturn,
  type Connection,
  type HealthCheckResult,
} from "./useConnectionsRealtimeWebSocket";

export {
  useHeartMetricsWebSocket,
  type UseHeartMetricsWebSocketOptions,
  type UseHeartMetricsWebSocketReturn,
  type HeartMetricsSnapshot,
  type DimensionMetrics,
  type ThresholdAlert,
} from "./useHeartMetricsWebSocket";

export {
  useCostTrackingWebSocket,
  type UseCostTrackingWebSocketOptions,
  type UseCostTrackingWebSocketReturn,
  type CostEvent,
  type SessionCost,
  type UserBudget,
  type BudgetWarning,
} from "./useCostTrackingWebSocket";

// =============================================================================
// Alert Hooks (ADR-0026 - Comprehensive Client Resilience Patterns)
// =============================================================================

export { useAlertSound, type UseAlertSoundReturn } from "./useAlertSound";

export {
  useAlertSoundSettings,
  useAlertSoundOptionsFromSettings,
  type AlertSoundSettings,
  type UseAlertSoundSettingsReturn,
  DEFAULT_ALERT_SOUND_SETTINGS,
} from "./useAlertSoundSettings";

export { useAlertSoundIntegration } from "./useAlertSoundIntegration";

// =============================================================================
// Connection Hooks
// =============================================================================

export { useMCPConnection } from "./useMCPConnection";

// useConnectionHealth is DEPRECATED - use useConnectionHealthWebSocket instead
// (exported in WebSocket Hooks section above)

export {
  useMCPKeyboardShortcuts,
  MCP_SHORTCUTS,
} from "./useMCPKeyboardShortcuts";

// =============================================================================
// Chat Hooks
// =============================================================================

export { useStreamingChat } from "./useStreamingChat";

export { useAutoSessionTitle } from "./useAutoSessionTitle";

export { useSessionAutoName } from "./useSessionAutoName";

export { useWorkflowAutoName } from "./useWorkflowAutoName";
export type {
  UseWorkflowAutoNameOptions,
  UseWorkflowAutoNameResult,
} from "./useWorkflowAutoName";

export { useNewChat } from "./useNewChat";

export { useSessionSync } from "./useSessionSync";

export { useMessageRevalidation } from "./useMessageRevalidation";

export {
  useChatAutoScroll,
  type UseChatAutoScrollReturn,
} from "./useChatAutoScroll";

// =============================================================================
// UI/UX Hooks
// =============================================================================

export { useDebounce } from "./useDebounce";

export {
  useCanvasKeyboardNav,
  type CanvasKeyboardNavRefs,
} from "./useCanvasKeyboardNav";

export { useKeyboardShortcuts } from "./useKeyboardShortcuts";

export { useTheme } from "./useTheme";

export { useOnboarding } from "./useOnboarding";

export { useProgressiveDisclosure } from "./useProgressiveDisclosure";
export type {
  DisclosureConfig,
  ProgressiveDisclosureResult,
} from "./useProgressiveDisclosure";

export { useFileUpload } from "./useFileUpload";

export { useVoiceInput } from "./useVoiceInput";

// =============================================================================
// PWA Hooks (Progressive Web App)
// =============================================================================

export { useOffline } from "./useOffline";

export { usePWAUpdate } from "./usePWAUpdate";

export { usePushNotifications } from "./usePushNotifications";

export { useBackgroundSync } from "./useBackgroundSync";

// =============================================================================
// Feature Hooks
// =============================================================================

export { useHeartMetricsTracker } from "./useHeartMetricsTracker";

export { useHeartDashboard } from "./useHeartDashboard";
export type {
  TimeRange,
  UseHeartDashboardOptions,
  UseHeartDashboardResult,
} from "./useHeartDashboard";

export { useTraceToReactFlow } from "./useTraceToReactFlow";

export { useWorkflowExecution } from "./useWorkflowExecution";

// API Hook Wrappers (for test isolation - prevents OOM during test module loading)
export {
  useGetWorkflowSuggestionsMutation,
  useListWorkflowExecutionsQuery,
} from "./useWorkflowAPI";

// =============================================================================
// Router Hooks (React Router Integration)
// =============================================================================

export { useSafeRouteLoaderData } from "./useSafeRouteLoaderData";

export { usePersonaRouting } from "./usePersonaRouting";

export { useBreadcrumb, type BreadcrumbItem } from "./useBreadcrumb";

// =============================================================================
// Permission Hooks
// =============================================================================

export { usePermissionCache } from "./usePermissionCache";

// =============================================================================
// AI-Powered Hooks
// =============================================================================

export { useAIEmptyState } from "./useAIEmptyState";
export type {
  AISuggestion,
  UseAIEmptyStateOptions,
  UseAIEmptyStateResult,
} from "./useAIEmptyState";

// Sprint 3 AI-Powered Hooks (Stubs - Implementation Planned)
export { useAIErrorRecovery } from "./useAIErrorRecovery";
export type {
  AIErrorAnalysis,
  AIRecoverySuggestion,
  UseAIErrorRecoveryOptions,
  UseAIErrorRecoveryResult,
} from "./useAIErrorRecovery";

export { useNudges } from "./useNudges";
export type {
  Nudge,
  NudgeType,
  NudgePriority,
  NudgeHistory,
  UseNudgesOptions,
  UseNudgesResult,
} from "./useNudges";

export { useOfflineQueue } from "./useOfflineQueue";
export type {
  QueuedAction,
  QueuedActionType,
  SyncConflict,
  SyncResult,
  ConflictResolution,
  UseOfflineQueueOptions,
  UseOfflineQueueResult,
} from "./useOfflineQueue";

export { useAISuggestionsCache } from "./useAISuggestionsCache";
export type {
  CachedSuggestion,
  AIContextRef,
  UseAISuggestionsCacheOptions,
  UseAISuggestionsCacheResult,
} from "./useAISuggestionsCache";

export { useAISuggestionsFetch } from "./useAISuggestionsFetch";
export type {
  UseAISuggestionsFetchOptions,
  UseAISuggestionsFetchResult,
} from "./useAISuggestionsFetch";

// Phase 6.5-6.7: AI-Powered Personalization Hooks
export { useAIOnboarding } from "./useAIOnboarding";
export type {
  OnboardingStep,
  SignupContext,
  UseAIOnboardingOptions,
  UseAIOnboardingResult,
} from "./useAIOnboarding";

export { useAIMetricsInsights } from "./useAIMetricsInsights";
export type {
  BaseInsight,
  AnomalyInsight,
  TrendInsight,
  PatternInsight,
  Insight,
  Prediction,
  UseAIMetricsInsightsOptions,
  UseAIMetricsInsightsResult,
} from "./useAIMetricsInsights";

export { useAIPersonaAnalysis } from "./useAIPersonaAnalysis";
export type {
  UIAdaptation,
  FeatureUsage,
  UseAIPersonaAnalysisOptions,
  UseAIPersonaAnalysisResult,
} from "./useAIPersonaAnalysis";

// Real-time AI Suggestions (WebSocket)
export { useAIRealTimeSuggestions } from "./useAIRealTimeSuggestions";
export type {
  Suggestion,
  UseAIRealTimeSuggestionsOptions,
  UseAIRealTimeSuggestionsReturn,
  SuggestionRequestContext,
} from "./useAIRealTimeSuggestions";

// Batch Composite Analysis (runs persona, disclosure, error analyses in parallel)
export { useBatchCompositeAnalysis } from "./useBatchCompositeAnalysis";
export type {
  DisclosureLevel,
  PersonaAnalysisResult,
  DisclosureAnalysisResult,
  ErrorAnalysisSuggestion,
  ErrorAnalysisResult,
  UseBatchCompositeAnalysisOptions,
  UseBatchCompositeAnalysisResult,
} from "./useBatchCompositeAnalysis";

// Studio AI (unified StudioShell AI analysis via StudioOrchestrator)
export { useStudioAI } from "./useStudioAI";
export type {
  TaskCategory,
  StudioTask,
  StudioAnalysisResult,
  UseStudioAIOptions,
  UseStudioAIResult,
} from "./useStudioAI";

// CrossInsightsPanel state management (extracted from StudioShellLayout)
export { useCrossInsightsPanel } from "./useCrossInsightsPanel";
export type { UseCrossInsightsPanelReturn } from "./useCrossInsightsPanel";

// Session Intelligence (Sprint 2)
export {
  useSessionSummary,
  useSessionGroups,
  useSessionSimilarity,
} from "./useSessionIntelligence";
export type {
  SessionGroup,
  SimilarSession,
  UseSessionSummaryOptions,
  UseSessionSummaryResult,
  UseSessionGroupsOptions,
  UseSessionGroupsResult,
  UseSessionSimilarityOptions,
  UseSessionSimilarityResult,
} from "./useSessionIntelligence";

// Conversation Intelligence (Sprint 3)
export {
  useIntentDetection,
  useContextOptimization,
  useGoalTracking,
} from "./useConversationIntelligence";
export type {
  IntentDetectionOptions,
  IntentDetectionResult,
  ContextOptimizationOptions,
  ContextSuggestion,
  ContextOptimizationResult,
  GoalTrackingOptions,
  GoalTrackingResult,
} from "./useConversationIntelligence";

// Canvas + Diagram Intelligence (Sprint 4)
export {
  useArtifactTypeSuggestion,
  useCodeAnalysis,
  useDiffExplanation,
  useDiagramAnalysis,
  useDiagramToCode,
} from "./useCanvasIntelligence";
export type {
  ArtifactTypeSuggestionOptions,
  ArtifactTypeAlternative,
  ArtifactTypeSuggestionResult,
  CodeAnalysisOptions,
  CodeIssue,
  CodeSuggestion,
  CodeAnalysisResult,
  DiffExplanationOptions,
  DiffChange,
  DiffExplanationResult,
  DiagramAnalysisOptions,
  DiagramSuggestion,
  DiagramIssue,
  DiagramAnalysisResult,
  DiagramToCodeOptions,
  DiagramToCodeResult,
} from "./useCanvasIntelligence";

// Trace + Cost Intelligence (Sprint 5)
export {
  useTraceSummary,
  useTraceAnomaly,
  useCostProjection,
  useTokenPrediction,
} from "./useTraceIntelligence";
export type {
  TraceSummaryOptions,
  TraceSummaryResult,
  TraceAnomalyOptions,
  TraceAnomaly,
  TraceBottleneck,
  TraceAnomalyResult,
  CostProjectionOptions,
  TraceTokenBreakdown,
  CostProjectionResult,
  TokenPredictionOptions,
  TokenPredictionResult,
} from "./useTraceIntelligence";

// HITL Intelligence (Sprint 6)
export { useRiskAssessment, useDecisionHistory } from "./useHITLIntelligence";
export type {
  RiskFactor,
  RiskLevel,
  RiskRecommendation,
  RiskAssessmentOptions,
  RiskAssessmentResult,
  SimilarDecision,
  DecisionHistoryOptions,
  DecisionHistoryResult,
} from "./useHITLIntelligence";

// UX Intelligence (Sprint 6)
export {
  useNavPrediction,
  useContextualHelp,
  useLearningPath,
} from "./useUXIntelligence";
export type {
  PredictedNavItem,
  NavPredictionOptions,
  NavPredictionResult,
  HelpTopic,
  QuickAction,
  ContextualHelpOptions,
  ContextualHelpResult,
  LearningStep,
  SkillLevel,
  LearningPathOptions,
  LearningPathResult,
} from "./useUXIntelligence";

// HITL dialogs state management (extracted from StudioShellLayout)
export { useHITLDialogs } from "./useHITLDialogs";
export type {
  ClarificationResponse,
  UseHITLDialogsReturn,
} from "./useHITLDialogs";

// Rotating threshold settings
export { useThresholdSettings } from "./useThresholdSettings";
export type {
  ThresholdRecommendation,
  UserThresholdSettings,
  UpdateThresholdSettingsRequest,
  UseThresholdSettingsReturn,
} from "./useThresholdSettings";

// =============================================================================
// Error Reporting Hooks (Phase 2.4)
// =============================================================================

export { useErrorReporting } from "./useErrorReporting";
export type {
  UseErrorReportingOptions,
  UseErrorReportingResult,
} from "./useErrorReporting";

// =============================================================================
// AI Cache Hook (Architecture: Caching Layer)
// =============================================================================

export {
  useAICache,
  createCacheKey,
  clearAllAICache,
  clearAICacheByPrefix,
  getAICacheStats,
} from "./useAICache";
export type {
  CacheEntry,
  UseAICacheOptions,
  UseAICacheResult,
} from "./useAICache";

// =============================================================================
// AI Real-Time UX Suggestions (WebSocket + Context Integration)
// =============================================================================

export { useAIRealTimeUXSuggestions } from "./useAIRealTimeUXSuggestions";
export type {
  UseAIRealTimeUXSuggestionsOptions,
  UseAIRealTimeUXSuggestionsResult,
} from "./useAIRealTimeUXSuggestions";

// =============================================================================
// AI Metrics Hook (Architecture: Observability)
// =============================================================================

export { useAIMetrics, createAIMetricsTracker } from "./useAIMetrics";
export type {
  AIMetricsEventType,
  AIMetricsEvent,
  AIMetricsSnapshot,
  FeatureMetrics,
  UseAIMetricsOptions,
  UseAIMetricsResult,
  AIMetricsTracker,
  CreateAIMetricsTrackerOptions,
} from "./useAIMetrics";

// =============================================================================
// AI Intelligence Configuration (ADR-0068: WebSocket Standardization)
// =============================================================================

export { useAIIntelligenceConfig } from "./useAIIntelligenceConfig";
export type { UseAIIntelligenceConfigReturn } from "./useAIIntelligenceConfig";

// =============================================================================
// Persona Cache Invalidation (ADR-0068: WebSocket Standardization)
// =============================================================================

export { usePersonaCacheInvalidation } from "./usePersonaCacheInvalidation";
export type {
  UsePersonaCacheInvalidationOptions,
  UsePersonaCacheInvalidationResult,
} from "./usePersonaCacheInvalidation";

// =============================================================================
// Accessibility Hooks (Sprint 5.2: WCAG 2.1 AA Compliance)
// =============================================================================

export { useFocusTrap } from "./useFocusTrap";

// =============================================================================
// Metrics & Observability Hooks
// =============================================================================

export {
  useMetricsHistory,
  type TrendDirection,
  type MetricsSnapshot,
  type MetricWithTrend,
  type UseMetricsHistoryOptions,
  type UseMetricsHistoryResult,
} from "./useMetricsHistory";

// =============================================================================
// Tools Hooks (Manual Tool Selection)
// =============================================================================

export {
  useAvailableTools,
  type UseAvailableToolsOptions,
  type UseAvailableToolsResult,
} from "./useAvailableTools";

export {
  useNativeCapabilities,
  type UseNativeCapabilitiesOptions,
  type UseNativeCapabilitiesResult,
} from "./useNativeCapabilities";
