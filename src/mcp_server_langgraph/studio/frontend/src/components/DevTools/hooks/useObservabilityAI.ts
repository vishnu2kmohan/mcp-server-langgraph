/**
 * useObservabilityAI Hook
 *
 * AI-powered observability insights for DevTools.
 * Provides trace anomaly detection, alert correlation, cost prediction,
 * and root cause analysis.
 */
import { useState, useEffect, useMemo, useCallback } from "react";

// =============================================================================
// Types
// =============================================================================

export interface SpanData {
  span_id: string;
  duration_ms: number;
  name: string;
  status?: string;
  service_name?: string;
}

export interface AlertData {
  id: string;
  started_at: string;
  service: string;
  message?: string;
}

export interface MetricData {
  name: string;
  value: number;
  timestamp: number;
}

export interface TraceAnomalies {
  slowSpans: SpanData[];
  errorPatterns: { name: string; count: number }[];
  percentiles: { p50: number; p95: number; p99: number };
}

export interface AlertCorrelation {
  alerts: string[];
  services: string[];
  timeWindow: { start: number; end: number };
}

export interface CostPrediction {
  trend: "increasing" | "decreasing" | "stable";
  projectedDaily: number;
  anomalies: { timestamp: number; value: number }[];
}

export interface RootCauseAnalysis {
  hypothesis: string;
  confidence: number;
  rootCauses: { description: string; likelihood: number }[];
  suggestedActions: string[];
}

export interface ObservabilityInsights {
  traceAnomalies: TraceAnomalies | null;
  alertCorrelations: AlertCorrelation[];
  costPrediction: CostPrediction | null;
  rootCauseAnalysis: RootCauseAnalysis | null;
}

export interface SuggestedAction {
  id: string;
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  category: "performance" | "reliability" | "cost";
}

export interface UseObservabilityAIOptions {
  enabled: boolean;
  spans?: SpanData[];
  alerts?: AlertData[];
  metrics?: MetricData[];
}

export interface UseObservabilityAIReturn {
  insights: ObservabilityInsights;
  suggestedActions: SuggestedAction[];
  isAnalyzing: boolean;
  refresh: () => void;
}

// =============================================================================
// Analysis Functions
// =============================================================================

const SLOW_THRESHOLD_MS = 1000; // 1 second
const CORRELATION_WINDOW_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Analyze trace spans for anomalies
 */
export function analyzeTraceAnomalies(spans: SpanData[]): TraceAnomalies {
  // Find slow spans (above threshold)
  const slowSpans = spans.filter((s) => s.duration_ms > SLOW_THRESHOLD_MS);

  // Find error patterns
  const errorSpans = spans.filter((s) => s.status === "error");
  const errorCounts = new Map<string, number>();
  for (const span of errorSpans) {
    const name = span.name;
    errorCounts.set(name, (errorCounts.get(name) || 0) + 1);
  }
  const errorPatterns = Array.from(errorCounts.entries()).map(
    ([name, count]) => ({ name, count }),
  );

  // Calculate percentiles
  const durations = spans.map((s) => s.duration_ms).sort((a, b) => a - b);
  const getPercentile = (p: number) => {
    const index = Math.floor((p / 100) * durations.length);
    return durations[index] || 0;
  };

  return {
    slowSpans,
    errorPatterns,
    percentiles: {
      p50: getPercentile(50),
      p95: getPercentile(95),
      p99: getPercentile(99),
    },
  };
}

/**
 * Correlate alerts by time proximity
 */
export function correlateAlerts(alerts: AlertData[]): AlertCorrelation[] {
  if (alerts.length === 0) return [];

  // Sort by time
  const sorted = [...alerts].sort(
    (a, b) =>
      new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
  );

  const correlations: AlertCorrelation[] = [];
  let currentGroup: AlertData[] = [sorted[0]];

  for (let i = 1; i < sorted.length; i++) {
    const prevTime = new Date(sorted[i - 1].started_at).getTime();
    const currTime = new Date(sorted[i].started_at).getTime();

    if (currTime - prevTime <= CORRELATION_WINDOW_MS) {
      currentGroup.push(sorted[i]);
    } else {
      if (currentGroup.length > 0) {
        correlations.push({
          alerts: currentGroup.map((a) => a.id),
          services: [...new Set(currentGroup.map((a) => a.service))],
          timeWindow: {
            start: new Date(currentGroup[0].started_at).getTime(),
            end: new Date(
              currentGroup[currentGroup.length - 1].started_at,
            ).getTime(),
          },
        });
      }
      currentGroup = [sorted[i]];
    }
  }

  // Add last group
  if (currentGroup.length > 0) {
    correlations.push({
      alerts: currentGroup.map((a) => a.id),
      services: [...new Set(currentGroup.map((a) => a.service))],
      timeWindow: {
        start: new Date(currentGroup[0].started_at).getTime(),
        end: new Date(
          currentGroup[currentGroup.length - 1].started_at,
        ).getTime(),
      },
    });
  }

  return correlations;
}

/**
 * Predict cost trends from metrics
 */
export function predictCostTrends(metrics: MetricData[]): CostPrediction {
  const tokenMetrics = metrics.filter((m) => m.name === "tokens_used");

  if (tokenMetrics.length < 2) {
    return {
      trend: "stable",
      projectedDaily: 0,
      anomalies: [],
    };
  }

  // Calculate trend
  const values = tokenMetrics.map((m) => m.value);
  const avgChange =
    values.slice(1).reduce((sum, v, i) => sum + (v - values[i]), 0) /
    (values.length - 1);

  let trend: "increasing" | "decreasing" | "stable" = "stable";
  if (avgChange > values[0] * 0.1) trend = "increasing";
  else if (avgChange < -values[0] * 0.1) trend = "decreasing";

  // Calculate projected daily
  const avgValue = values.reduce((a, b) => a + b, 0) / values.length;
  const projectedDaily = avgValue * 24; // Simple projection

  // Find anomalies (values > 2x average)
  const anomalies = tokenMetrics
    .filter((m) => m.value > avgValue * 2)
    .map((m) => ({ timestamp: m.timestamp, value: m.value }));

  return {
    trend,
    projectedDaily,
    anomalies,
  };
}

/**
 * Generate root cause analysis from context
 */
export function generateRootCauseAnalysis(context: {
  alerts: Partial<AlertData>[];
  spans: Partial<SpanData>[];
}): RootCauseAnalysis {
  const rootCauses: { description: string; likelihood: number }[] = [];

  // Analyze alerts for patterns
  const dbAlerts = context.alerts.filter(
    (a) =>
      a.service?.includes("db") ||
      a.message?.toLowerCase().includes("database"),
  );
  const apiAlerts = context.alerts.filter(
    (a) =>
      a.service?.includes("api") ||
      a.message?.toLowerCase().includes("request"),
  );

  // Database issues often cascade to API issues
  if (dbAlerts.length > 0 && apiAlerts.length > 0) {
    rootCauses.push({
      description: "Database connectivity issues causing API failures",
      likelihood: 0.85,
    });
  }

  // Check for timeout patterns
  const timeoutMessages = context.alerts.filter(
    (a) =>
      a.message?.toLowerCase().includes("timeout") ||
      a.message?.toLowerCase().includes("exhausted"),
  );
  if (timeoutMessages.length > 0) {
    rootCauses.push({
      description: "Resource exhaustion leading to timeouts",
      likelihood: 0.75,
    });
  }

  // Analyze slow spans
  const slowDbSpans = context.spans.filter(
    (s) => s.name?.includes("db") && (s.duration_ms || 0) > 5000,
  );
  if (slowDbSpans.length > 0) {
    rootCauses.push({
      description: "Slow database queries impacting overall latency",
      likelihood: 0.9,
    });
  }

  // Sort by likelihood
  rootCauses.sort((a, b) => b.likelihood - a.likelihood);

  // Generate hypothesis
  const hypothesis =
    rootCauses.length > 0
      ? rootCauses[0].description
      : "No clear root cause identified";

  // Generate suggested actions
  const suggestedActions: string[] = [];
  if (dbAlerts.length > 0) {
    suggestedActions.push("Check database connection pool settings");
  }
  if (timeoutMessages.length > 0) {
    suggestedActions.push("Review resource limits and scaling policies");
  }
  if (suggestedActions.length === 0) {
    suggestedActions.push("Review recent deployments for potential issues");
  }

  return {
    hypothesis,
    confidence: rootCauses.length > 0 ? rootCauses[0].likelihood : 0.3,
    rootCauses,
    suggestedActions,
  };
}

// =============================================================================
// Hook Implementation
// =============================================================================

const EMPTY_INSIGHTS: ObservabilityInsights = {
  traceAnomalies: null,
  alertCorrelations: [],
  costPrediction: null,
  rootCauseAnalysis: null,
};

export function useObservabilityAI(
  options: UseObservabilityAIOptions,
): UseObservabilityAIReturn {
  const { enabled, spans = [], alerts = [], metrics = [] } = options;

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [insights, setInsights] =
    useState<ObservabilityInsights>(EMPTY_INSIGHTS);

  // Analyze data when inputs change
  const analyze = useCallback(() => {
    if (!enabled) {
      setInsights(EMPTY_INSIGHTS);
      return;
    }

    setIsAnalyzing(true);

    // Perform analysis (synchronous for now, could be async with worker)
    const traceAnomalies =
      spans.length > 0 ? analyzeTraceAnomalies(spans) : null;
    const alertCorrelations = correlateAlerts(alerts);
    const costPrediction =
      metrics.length > 0 ? predictCostTrends(metrics) : null;
    const rootCauseAnalysis =
      alerts.length > 0 || spans.length > 0
        ? generateRootCauseAnalysis({ alerts, spans })
        : null;

    setInsights({
      traceAnomalies,
      alertCorrelations,
      costPrediction,
      rootCauseAnalysis,
    });

    setIsAnalyzing(false);
  }, [enabled, spans, alerts, metrics]);

  // Run analysis on mount and when data changes
  useEffect(() => {
    analyze();
  }, [analyze]);

  // Generate suggested actions from insights
  const suggestedActions = useMemo<SuggestedAction[]>(() => {
    const actions: SuggestedAction[] = [];

    if (insights.traceAnomalies?.slowSpans.length) {
      actions.push({
        id: "optimize-slow-spans",
        title: "Optimize Slow Operations",
        description: `${insights.traceAnomalies.slowSpans.length} slow operations detected`,
        priority: "high",
        category: "performance",
      });
    }

    if (insights.traceAnomalies?.errorPatterns.length) {
      actions.push({
        id: "investigate-errors",
        title: "Investigate Error Patterns",
        description: `${insights.traceAnomalies.errorPatterns.length} recurring error patterns`,
        priority: "high",
        category: "reliability",
      });
    }

    if (insights.costPrediction?.trend === "increasing") {
      actions.push({
        id: "review-costs",
        title: "Review Token Usage",
        description: "Token usage is trending upward",
        priority: "medium",
        category: "cost",
      });
    }

    if (insights.rootCauseAnalysis?.suggestedActions) {
      for (const action of insights.rootCauseAnalysis.suggestedActions) {
        actions.push({
          id: `rca-${actions.length}`,
          title: action,
          description: "Suggested by root cause analysis",
          priority: "high",
          category: "reliability",
        });
      }
    }

    return actions;
  }, [insights]);

  return {
    insights,
    suggestedActions,
    isAnalyzing,
    refresh: analyze,
  };
}

export default useObservabilityAI;
